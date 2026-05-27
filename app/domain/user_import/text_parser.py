from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

LINE_SEPARATOR_RE = re.compile(r"\r\n?")
MULTISPACE_RE = re.compile(r"\s+")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
LEADING_NUMBER_RE = re.compile(r"^\s*(?:\d+\.\s*)+")
PAIR_SEPARATOR_RE = re.compile(r"\s[-–—]\s")
TRANSLATES_AS_RE = re.compile(r"\b(?:переводится|перекладається|translates?)\s+(?:как|як|as)\s*:?\s*", re.IGNORECASE)
ENGLISH_WORD_SEQUENCE_RE = re.compile(r"[A-Za-z][A-Za-z'‘’/-]*(?:\s+[A-Za-z][A-Za-z'‘’/-]*)*")
REPEATED_TO_VARIANT_RE = re.compile(r"\bto\s+(?=[A-Za-z])", re.IGNORECASE)
HTML_LIKE_RE = re.compile(r"[<>]|&lt;|&gt;|<script|</script", re.IGNORECASE)
SQL_LIKE_RE = re.compile(
    r"(?:--|/\*|\*/|;\s*(?:drop|delete|update|insert|alter)\b|"
    r"\b(?:drop|delete|update|insert|alter|truncate)\s+(?:table|from|into|database|schema)\b)",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'/-]*$")
IPA_FRAGMENT_RE = re.compile(r"/[^/\n]+/")
PHONETIC_BRACKET_FRAGMENT_RE = re.compile(r"\[[^\]\n]*[\u0250-\u02AF\u0300-\u036Fˈˌ][^\]\n]*\]")
PAREN_FRAGMENT_RE = re.compile(r"\([^)]*\)")
PHONETIC_PREFIX_RECOVERY_WORDS = frozenset({"despite"})
PROMPT_LIKE_RE = re.compile(
    r"\b("
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
    r"system\s+prompt|developer\s+message|"
    r"you\s+are\s+(?:now|chatgpt|an?\s+ai)|"
    r"act\s+as|pretend\s+to\s+be|"
    r"execute|run\s+(?:this\s+)?(?:command|script|code)|"
    r"shell|powershell|bash|python|javascript|"
    r"prompt\s+injection|"
    r"выполни|виконай|запусти|запусти\s+скрипт|"
    r"игнорируй\s+(?:все\s+)?(?:предыдущие|попередні)|"
    r"проігноруй\s+(?:усі\s+)?попередні"
    r")\b",
    re.IGNORECASE,
)
TEMPLATE_LIKE_RE = re.compile(r"(\{\{|\}\}|<%|%>|\$\{|\{%|%\})")
MAX_IMPORT_ITEM_CHARS = 120
MAX_IMPORT_ITEM_WORDS = 14
MAX_PARSED_IMPORT_WORDS = 200
MAX_INVALID_IMPORT_FEEDBACK_ITEMS = 50


@dataclass(frozen=True)
class ParsedImportWord:
    raw_value: str
    lookup_word: str
    translation_hint: str | None = None
    validated_lookup_word: str | None = None
    validated_part_of_speech: str | None = None
    validated_translation_uk: str | None = None
    validated_translation_ru: str | None = None
    validated_translation_pl: str | None = None


@dataclass(frozen=True)
class ParsedImportTextResult:
    parsed_words: list[ParsedImportWord]
    invalid_fragments: list[str]


def normalize_import_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\ufeff", "")
    normalized = LINE_SEPARATOR_RE.sub("\n", normalized)
    normalized = CONTROL_CHAR_RE.sub(" ", normalized)
    return normalized.strip()


def normalize_lookup_word(value: str) -> str:
    normalized = value.strip()
    normalized = IPA_FRAGMENT_RE.sub(" ", normalized)
    normalized = PAREN_FRAGMENT_RE.sub(" ", normalized)
    normalized = normalized.replace("’", "'")
    normalized = re.sub(r"\s*/\s*", " / ", normalized)
    normalized = re.sub(r"[^A-Za-z' /-]+", " ", normalized)
    normalized = MULTISPACE_RE.sub(" ", normalized).strip()
    if " / " in normalized:
        normalized = normalized.split(" / ", 1)[0].strip()
    return normalized.lower()


def is_allowed_lookup_word(value: str) -> bool:
    candidate = value.strip().lower()
    if not candidate or "/" in candidate:
        return False
    if len(candidate) > MAX_IMPORT_ITEM_CHARS:
        return False
    tokens = candidate.split()
    if len(tokens) > MAX_IMPORT_ITEM_WORDS:
        return False
    if len(tokens) == 1:
        if len(tokens[0].replace("'", "")) < 2:
            return False
        return bool(TOKEN_RE.fullmatch(tokens[0]))
    return all(TOKEN_RE.fullmatch(token) for token in tokens)


def _normalize_fragment(value: str) -> str:
    candidate = normalize_import_text(value)
    candidate = LEADING_NUMBER_RE.sub("", candidate).strip()
    if not candidate:
        return ""
    if PAIR_SEPARATOR_RE.search(candidate):
        candidate = PAIR_SEPARATOR_RE.split(candidate, maxsplit=1)[0].strip()
    candidate = candidate.strip(" \"'`“”‘’")
    candidate = MULTISPACE_RE.sub(" ", candidate)
    return candidate


def _normalize_translation_hint(value: str | None) -> str | None:
    candidate = normalize_import_text(value or "")
    candidate = LEADING_NUMBER_RE.sub("", candidate).strip()
    candidate = TRANSLATES_AS_RE.sub("", candidate).strip()
    candidate = candidate.strip(" :\"'`“”‘’➡️-–—")
    candidate = re.sub(r"\s*;\s*", ", ", candidate)
    candidate = MULTISPACE_RE.sub(" ", candidate)
    if not candidate:
        return None
    if len(candidate) > 160:
        candidate = candidate[:157].rstrip() + "..."
    return candidate


def _strip_parenthetical_context(value: str) -> str:
    return PAREN_FRAGMENT_RE.sub(" ", value).split(":", 1)[0]


def _strip_phonetic_context(value: str) -> str:
    without_ipa = IPA_FRAGMENT_RE.sub(" ", value)
    return PHONETIC_BRACKET_FRAGMENT_RE.sub(" ", without_ipa)


def _repair_phonetic_prefix_artifact(value: str) -> str:
    tokens = value.split()
    if not tokens:
        return value
    first_token = tokens[0]
    if len(first_token) < 3 or not first_token.isalpha():
        return value
    recovered_first_token = first_token[1:]
    if recovered_first_token.lower() not in PHONETIC_PREFIX_RECOVERY_WORDS:
        return value
    return " ".join([recovered_first_token, *tokens[1:]])


def _extract_english_lookup_candidate(value: str) -> str:
    candidates = _extract_english_lookup_candidates(value)
    if not candidates:
        return ""
    return candidates[0]


def _extract_english_lookup_candidates(value: str) -> list[str]:
    candidate = normalize_import_text(value)
    candidate = TRANSLATES_AS_RE.sub("", candidate)
    candidate = _strip_phonetic_context(candidate)
    candidate = _repair_phonetic_prefix_artifact(candidate)
    candidate = re.sub(r"^\s*(?:як|как|as)\s+", "", candidate, flags=re.IGNORECASE)
    candidate = _strip_parenthetical_context(candidate)
    matches = ENGLISH_WORD_SEQUENCE_RE.findall(candidate)
    if not matches:
        return []
    result: list[str] = []
    for match in matches:
        result.extend(_split_english_lookup_variants(match))
    return _dedupe_lookup_candidates(result)


def _split_english_lookup_variants(value: str) -> list[str]:
    candidate = MULTISPACE_RE.sub(" ", str(value or "")).strip(" ,;")
    if not candidate:
        return []
    to_matches = list(REPEATED_TO_VARIANT_RE.finditer(candidate))
    if len(to_matches) < 2:
        return [candidate]
    variants: list[str] = []
    for index, match in enumerate(to_matches):
        start = match.start()
        end = to_matches[index + 1].start() if index + 1 < len(to_matches) else len(candidate)
        variant = candidate[start:end].strip(" ,;")
        if variant:
            variants.append(variant)
    return variants or [candidate]


def _dedupe_lookup_candidates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        raw_value = _normalize_fragment(value)
        lookup_word = normalize_lookup_word(raw_value)
        if not lookup_word or lookup_word in seen:
            continue
        seen.add(lookup_word)
        result.append(raw_value)
    return result


def _parse_import_fragment(fragment: str) -> tuple[str, str | None]:
    candidates = _parse_import_fragment_candidates(fragment)
    if not candidates:
        return "", None
    return candidates[0]


def _parse_import_fragment_candidates(fragment: str) -> list[tuple[str, str | None]]:
    candidate = normalize_import_text(fragment)
    if not candidate:
        return []

    translation_hint: str | None = None
    raw_values = [_normalize_fragment(candidate)]
    if PAIR_SEPARATOR_RE.search(candidate):
        left, right = PAIR_SEPARATOR_RE.split(candidate, maxsplit=1)
        normalized_left = _repair_phonetic_prefix_artifact(_normalize_fragment(_strip_phonetic_context(left)))
        left_variants = _extract_english_lookup_candidates(normalized_left)
        left_lookup = normalize_lookup_word(normalized_left)
        if len(left_variants) > 1:
            raw_values = left_variants
            translation_hint = _normalize_translation_hint(right)
        elif left_lookup and is_allowed_lookup_word(left_lookup):
            raw_values = _dedupe_lookup_candidates([normalized_left])
            translation_hint = _normalize_translation_hint(right)
        else:
            extracted = _extract_english_lookup_candidates(right)
            if extracted:
                raw_values = extracted
                translation_hint = _normalize_translation_hint(left)
    else:
        match = TRANSLATES_AS_RE.search(candidate)
        if match is not None:
            left = candidate[: match.start()].strip()
            right = candidate[match.end() :].strip()
            left_lookup = normalize_lookup_word(_normalize_fragment(left))
            if left_lookup and is_allowed_lookup_word(left_lookup):
                raw_values = _dedupe_lookup_candidates([_normalize_fragment(left)])
                translation_hint = _normalize_translation_hint(right)

    return [(raw_value, translation_hint) for raw_value in raw_values if raw_value]


def _is_suspicious_fragment(value: str) -> bool:
    if not value:
        return True
    lowered = value.lower()
    return bool(
        HTML_LIKE_RE.search(lowered)
        or SQL_LIKE_RE.search(lowered)
        or PROMPT_LIKE_RE.search(lowered)
        or TEMPLATE_LIKE_RE.search(lowered)
        or "http://" in lowered
        or "https://" in lowered
    )


def _sanitize_invalid_fragment_for_feedback(value: str) -> str:
    candidate = normalize_import_text(value)
    candidate = LEADING_NUMBER_RE.sub("", candidate).strip()
    candidate = MULTISPACE_RE.sub(" ", candidate)
    candidate = candidate.strip(" \"'`“”‘’")
    if not candidate:
        return "[порожній фрагмент]"
    if _is_suspicious_fragment(candidate):
        return "[небезпечний фрагмент приховано]"
    candidate = re.sub(r"[^0-9A-Za-zА-Яа-яІіЇїЄєҐґ' /,-]+", " ", candidate)
    candidate = MULTISPACE_RE.sub(" ", candidate).strip(" ,")
    if not candidate:
        return "[невалідний фрагмент]"
    if len(candidate) > 80:
        candidate = candidate[:77].rstrip() + "..."
    return candidate


def parse_user_vocabulary_text_result(text: str, *, max_words: int = MAX_PARSED_IMPORT_WORDS) -> ParsedImportTextResult:
    normalized_text = normalize_import_text(text)
    max_words = max(int(max_words), 1)
    seen: set[str] = set()
    seen_invalid: set[str] = set()
    result: list[ParsedImportWord] = []
    invalid_fragments: list[str] = []
    lines = normalized_text.split("\n")
    line_index = 0
    while line_index < len(lines):
        raw_line = lines[line_index]
        line_index += 1
        line = raw_line.strip()
        if not line:
            continue
        translate_match = TRANSLATES_AS_RE.search(line)
        if translate_match is not None and not line[translate_match.end() :].strip():
            lookahead_index = line_index
            while lookahead_index < len(lines) and not lines[lookahead_index].strip():
                lookahead_index += 1
            if lookahead_index < len(lines):
                line = f"{line} {lines[lookahead_index].strip()}"
                line_index = lookahead_index + 1
        fragments = [line]
        if not PAIR_SEPARATOR_RE.search(line):
            fragments = [fragment for fragment in line.split(",") if fragment.strip()]
        for fragment in fragments:
            parsed_candidates = _parse_import_fragment_candidates(fragment)
            if not parsed_candidates:
                continue
            for raw_value, translation_hint in parsed_candidates:
                if not raw_value:
                    continue
                if _is_suspicious_fragment(raw_value):
                    feedback = _sanitize_invalid_fragment_for_feedback(fragment)
                    if feedback not in seen_invalid and len(invalid_fragments) < MAX_INVALID_IMPORT_FEEDBACK_ITEMS:
                        seen_invalid.add(feedback)
                        invalid_fragments.append(feedback)
                    continue
                lookup_word = normalize_lookup_word(raw_value)
                if not lookup_word or not is_allowed_lookup_word(lookup_word):
                    feedback = _sanitize_invalid_fragment_for_feedback(fragment)
                    if feedback not in seen_invalid and len(invalid_fragments) < MAX_INVALID_IMPORT_FEEDBACK_ITEMS:
                        seen_invalid.add(feedback)
                        invalid_fragments.append(feedback)
                    continue
                if lookup_word in seen:
                    continue
                seen.add(lookup_word)
                result.append(ParsedImportWord(raw_value=raw_value, lookup_word=lookup_word, translation_hint=translation_hint))
                if len(result) >= max_words:
                    return ParsedImportTextResult(parsed_words=result, invalid_fragments=invalid_fragments)
    return ParsedImportTextResult(parsed_words=result, invalid_fragments=invalid_fragments)


def parse_user_vocabulary_text(text: str) -> list[ParsedImportWord]:
    return parse_user_vocabulary_text_result(text).parsed_words
