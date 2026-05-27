from __future__ import annotations

import re

IRREGULAR_SINGLE_TOKEN_FORMS: dict[str, set[str]] = {
    "calf": {"calves"},
    "child": {"children"},
    "criterion": {"criteria"},
    "foot": {"feet"},
    "fisherman": {"fishermen"},
    "gentleman": {"gentlemen"},
    "goose": {"geese"},
    "leaf": {"leaves"},
    "man": {"men"},
    "marksman": {"marksmen"},
    "midshipman": {"midshipmen"},
    "mouse": {"mice"},
    "person": {"people"},
    "policeman": {"policemen"},
    "shelf": {"shelves"},
    "tooth": {"teeth"},
    "woman": {"women"},
}
OBJECT_PLACEHOLDER_TOKENS = {
    "sb",
    "smb",
    "someone",
    "somebody",
    "sth",
    "smth",
    "something",
}
OBJECT_PLACEHOLDER_PATTERN = r"[A-Za-z][A-Za-z'-]*"
ACTION_PLACEHOLDER_PATTERN = (
    r"[A-Za-z][A-Za-z'-]*"
    r"(?:\s+(?!(?:after|before|during|at|in|on|for|from|with|without|because)\b)[A-Za-z][A-Za-z'-]*){0,2}"
)


def normalize_usage_form(usage_form: str) -> str:
    candidate = " ".join(usage_form.strip().split()).lower()
    if candidate.startswith("to "):
        tail = candidate[3:].strip()
        if tail:
            return tail
    return candidate


def _normalize_usage_tokens(usage_form: str) -> list[str]:
    return [token for token in re.sub(r"[^a-z\s-]", " ", normalize_usage_form(usage_form)).split() if token]


def _is_object_placeholder_token(token: str) -> bool:
    return token.lower() in OBJECT_PLACEHOLDER_TOKENS


def _is_thing_placeholder_token(token: str) -> bool:
    return token.lower() in {"sth", "smth", "something"}


def _looks_like_cvc(token: str) -> bool:
    if len(token) < 3:
        return False
    vowels = "aeiou"
    return (
        token[-1] not in vowels + "wxy"
        and token[-2] in vowels
        and token[-3] not in vowels
    )


def _inflected_single_token_forms(token: str) -> set[str]:
    forms = {token}
    forms.update(IRREGULAR_SINGLE_TOKEN_FORMS.get(token, set()))

    if token.endswith(("s", "x", "z", "sh", "ch", "o")):
        forms.add(f"{token}es")
    elif token.endswith("y") and len(token) > 1 and token[-2] not in "aeiou":
        forms.add(f"{token[:-1]}ies")
    else:
        forms.add(f"{token}s")

    if token.endswith("fe") and len(token) > 2:
        forms.add(f"{token[:-2]}ves")
    elif token.endswith("f") and len(token) > 1:
        forms.add(f"{token[:-1]}ves")

    if token.endswith("man") and len(token) > 3:
        forms.add(f"{token[:-3]}men")

    forms.add(f"{token}ed")
    forms.add(f"{token}ing")

    if token.endswith("e") and len(token) > 1:
        forms.add(f"{token}d")
        forms.add(f"{token[:-1]}ing")

    if token.endswith("y") and len(token) > 1 and token[-2] not in "aeiou":
        stem = token[:-1]
        forms.add(f"{stem}ied")
        forms.add(f"{token}ing")

    if token.endswith("c"):
        forms.add(f"{token}ked")
        forms.add(f"{token}king")

    if _looks_like_cvc(token):
        doubled = f"{token}{token[-1]}"
        forms.add(f"{doubled}ed")
        forms.add(f"{doubled}ing")

    return forms


def _usage_form_pattern(usage_form: str) -> re.Pattern[str] | None:
    normalized_form = normalize_usage_form(usage_form)
    if normalized_form == "o'clock":
        return re.compile(r"\bo['’]?clock\b", re.IGNORECASE)
    if normalized_form in {"p.m.", "p.m", "pm"}:
        return re.compile(r"\bp\.?m\.?\b", re.IGNORECASE)
    if normalized_form in {"a.m.", "a.m", "am"}:
        return re.compile(r"\ba\.?m\.?\b", re.IGNORECASE)

    usage_tokens = _normalize_usage_tokens(usage_form)
    if not usage_tokens:
        return None
    if len(usage_tokens) == 1:
        if _is_object_placeholder_token(usage_tokens[0]):
            return re.compile(rf"\b{OBJECT_PLACEHOLDER_PATTERN}\b", re.IGNORECASE)
        variants = sorted(_inflected_single_token_forms(usage_tokens[0]), key=len, reverse=True)
        body = "|".join(re.escape(variant) for variant in variants)
        return re.compile(rf"\b(?:{body})\b", re.IGNORECASE)

    first_token_variants = sorted(_inflected_single_token_forms(usage_tokens[0]), key=len, reverse=True)
    first_token = "(?:" + "|".join(re.escape(variant) for variant in first_token_variants) + ")"
    rest_tokens = []
    index = 1
    while index < len(usage_tokens):
        token = usage_tokens[index]
        next_token = usage_tokens[index + 1] if index + 1 < len(usage_tokens) else ""
        if token == "do" and _is_thing_placeholder_token(next_token):
            rest_tokens.append(ACTION_PLACEHOLDER_PATTERN)
            index += 2
            continue
        rest_tokens.append(OBJECT_PLACEHOLDER_PATTERN if _is_object_placeholder_token(token) else re.escape(token))
        index += 1
    rest = r"\s+".join(rest_tokens)
    optional_insert = r"(?:\s+[A-Za-z']+){0,2}"
    return re.compile(rf"\b{first_token}{optional_insert}\s+{rest}\b", re.IGNORECASE)


def find_usage_form_span(text: str, usage_form: str) -> tuple[int, int] | None:
    pattern = _usage_form_pattern(usage_form)
    if pattern is None:
        return None
    match = pattern.search(text)
    if match is None:
        return None
    return match.span()


def contains_usage_form(text: str, usage_form: str) -> bool:
    return find_usage_form_span(text, usage_form) is not None
