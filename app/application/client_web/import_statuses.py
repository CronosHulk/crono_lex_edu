from __future__ import annotations

from app.application.client_web.import_errors import ClientWebImportValidationError

IMPORT_RESULT_PAGE_SIZE = 20
IMPORT_RESULT_PAGE_SIZES = {20, 50, 100}
IMPORT_SUCCESS_STATUSES = {"found_existing", "imported", "ready_for_rotation"}
IMPORT_QUEUE_STATUSES = {
    "pending",
    "waiting_for_user_dictionary_entry",
    "queued_for_details",
    "queued_for_audio",
    "queued_for_embedding",
}
IMPORT_REJECTED_STATUSES = {"rejected", "failed", "details_failed", "audio_failed", "embedding_failed"}
IMPORT_STATUS_CATEGORY_FILTERS = {
    "added": IMPORT_SUCCESS_STATUSES,
    "queued": IMPORT_QUEUE_STATUSES,
    "rejected": IMPORT_REJECTED_STATUSES,
}
IMPORT_STATUS_LABELS = {
    "uk": {
        "processing": "Обробляється",
        "added": "Успішно додано",
        "queued": "В черзі на додавання",
        "rejected": "Відхилено",
    },
    "ru": {
        "processing": "Обрабатывается",
        "added": "Успешно добавлено",
        "queued": "В очереди на добавление",
        "rejected": "Отклонено",
    },
    "pl": {
        "processing": "Przetwarzanie",
        "added": "Dodano",
        "queued": "W kolejce do dodania",
        "rejected": "Odrzucono",
    },
}
IMPORT_STATUS_EXACT_LABELS = {
    "uk": {
        "found_existing": "Вже в навчанні",
    },
    "ru": {
        "found_existing": "Уже в обучении",
    },
    "pl": {
        "found_existing": "Już w nauce",
    },
}


def validate_import_result_page_size(page_size: int) -> None:
    if page_size not in IMPORT_RESULT_PAGE_SIZES:
        raise ClientWebImportValidationError("Import result page_size must be one of 20, 50 or 100")


def status_category(status: str) -> str:
    if status in IMPORT_SUCCESS_STATUSES:
        return "added"
    if status in IMPORT_REJECTED_STATUSES:
        return "rejected"
    if status in IMPORT_QUEUE_STATUSES:
        return "queued"
    return "processing"


def status_filter(status_category_value: str) -> set[str] | None:
    if status_category_value == "all":
        return None
    if status_category_value not in IMPORT_STATUS_CATEGORY_FILTERS:
        raise ClientWebImportValidationError(
            "Import result status_category must be all, added, queued or rejected"
        )
    return IMPORT_STATUS_CATEGORY_FILTERS[status_category_value]


def build_status_summary(status_counts: dict[str, int]) -> dict[str, int]:
    summary = {"added": 0, "queued": 0, "rejected": 0, "processing": 0}
    for status, count in status_counts.items():
        summary[status_category(status)] += int(count)
    return summary


def build_category_summary(category_counts: dict[str, int]) -> dict[str, int]:
    summary = {"added": 0, "queued": 0, "rejected": 0, "processing": 0}
    for category, count in category_counts.items():
        if category in summary:
            summary[category] += int(count)
    return summary
