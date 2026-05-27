from __future__ import annotations

DICTIONARY_ENTRY_TYPE_WORD = "word"
DICTIONARY_ENTRY_TYPE_PHRASAL_VERB = "phrasal_verb"
DICTIONARY_ENTRY_TYPE_IDIOM = "idiom"
DICTIONARY_ENTRY_TYPE_PHRASE_PATTERN = "phrase_pattern"

DICTIONARY_ENTRY_TYPES = (
    DICTIONARY_ENTRY_TYPE_WORD,
    DICTIONARY_ENTRY_TYPE_PHRASAL_VERB,
    DICTIONARY_ENTRY_TYPE_IDIOM,
    DICTIONARY_ENTRY_TYPE_PHRASE_PATTERN,
)

DICTIONARY_ENTRY_TYPE_LABELS = {
    DICTIONARY_ENTRY_TYPE_WORD: "Word",
    DICTIONARY_ENTRY_TYPE_PHRASAL_VERB: "Phrasal verb",
    DICTIONARY_ENTRY_TYPE_IDIOM: "Idiom",
    DICTIONARY_ENTRY_TYPE_PHRASE_PATTERN: "Phrase pattern",
}

DICTIONARY_PART_OF_SPEECH_TYPES = (
    "noun",
    "verb",
    "adjective",
    "adverb",
    "pronoun",
    "preposition",
    "conjunction",
    "determiner",
    "interjection",
    "phrasal verb",
    "idiom",
    "phrase pattern",
)

_PART_OF_SPEECH_ALIASES = {
    "phrasalverb": "phrasal verb",
    "phrasal verb": "phrasal verb",
    "idiom": "idiom",
    "idiomatic expression": "idiom",
    "phrase pattern": "phrase pattern",
    "phrase": "phrase pattern",
    "useful phrase": "phrase pattern",
    "useful construction": "phrase pattern",
    "construction": "phrase pattern",
    "verb pattern": "phrase pattern",
    "imperative phrase": "phrase pattern",
    "sentence pattern": "phrase pattern",
    "grammar pattern": "phrase pattern",
}


def normalize_dictionary_entry_type(value: str | None) -> str:
    candidate = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if candidate == "phrasalverb":
        candidate = DICTIONARY_ENTRY_TYPE_PHRASAL_VERB
    if candidate not in DICTIONARY_ENTRY_TYPES:
        raise ValueError(f"entry_type must be one of: {', '.join(DICTIONARY_ENTRY_TYPES)}")
    return candidate


def normalize_dictionary_part_of_speech(value: str | None) -> str:
    candidate = " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())
    if not candidate:
        raise ValueError("part_of_speech is required")
    candidate = _PART_OF_SPEECH_ALIASES.get(candidate, candidate)
    if candidate not in DICTIONARY_PART_OF_SPEECH_TYPES:
        raise ValueError(f"part_of_speech must be one of: {', '.join(DICTIONARY_PART_OF_SPEECH_TYPES)}")
    return candidate


def dictionary_entry_type_from_part_of_speech(part_of_speech: str | None) -> str:
    candidate = " ".join(str(part_of_speech or "").strip().lower().replace("_", " ").replace("-", " ").split())
    candidate = _PART_OF_SPEECH_ALIASES.get(candidate, candidate)
    if candidate == "phrasal verb":
        return DICTIONARY_ENTRY_TYPE_PHRASAL_VERB
    if candidate == "idiom":
        return DICTIONARY_ENTRY_TYPE_IDIOM
    if candidate == "phrase pattern":
        return DICTIONARY_ENTRY_TYPE_PHRASE_PATTERN
    return DICTIONARY_ENTRY_TYPE_WORD
