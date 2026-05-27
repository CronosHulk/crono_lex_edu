from __future__ import annotations

import json

from app.application.admin.exercise_texts.providers import ExerciseTextGenerationRequest

EXERCISE_TEXT_GENERATION_PROMPT_VERSION = "exercise-texts-schema-v1-stage-v1"


def build_exercise_text_generation_prompt(request: ExerciseTextGenerationRequest) -> str:
    return "PROMPT"

