from __future__ import annotations

READY_STAGE_TO_QUIZ_STAGE = {
    "ready_en_uk": "quiz_en_uk",
    "ready_uk_en": "quiz_uk_en",
    "ready_gap": "quiz_gap",
}
QUIZ_STAGE_TO_EXERCISE = {
    "quiz_en_uk": "en_uk",
    "quiz_uk_en": "uk_en",
    "quiz_gap": "gap",
}
NEXT_READY_STAGE = {
    "quiz_en_uk": "ready_uk_en",
    "quiz_uk_en": "ready_gap",
}
READY_STAGES = tuple(READY_STAGE_TO_QUIZ_STAGE)
QUIZ_STAGES = tuple(QUIZ_STAGE_TO_EXERCISE)
READY_STAGE_INTRO_I18N_KEYS = {
    "ready_en_uk": "practice_intro",
    "ready_uk_en": "quiz_uk_en_title",
    "ready_gap": "quiz_gap_title",
}
QUIZ_STAGE_META_I18N_KEYS = {
    "quiz_en_uk": "quiz_en_uk_meta",
    "quiz_uk_en": "quiz_uk_en_meta",
    "quiz_gap": "quiz_gap_meta",
}
QUIZ_PROMPT_PROGRESS_STAGES = ("quiz_en_uk", "quiz_uk_en")
FINAL_QUIZ_STAGE = "quiz_gap"
