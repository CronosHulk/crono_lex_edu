from __future__ import annotations

ACTIVE_IMPORT_ITEM_STATUSES = (
    "pending",
    "found_existing",
    "waiting_for_user_dictionary_entry",
    "queued_for_details",
    "queued_for_audio",
    "queued_for_embedding",
    "ready_for_rotation",
    "imported",
)

SUCCESSFUL_IMPORT_ITEM_STATUSES = (
    "found_existing",
    "waiting_for_user_dictionary_entry",
    "queued_for_details",
    "queued_for_audio",
    "queued_for_embedding",
    "ready_for_rotation",
    "imported",
)

FAILED_IMPORT_ITEM_STATUSES = ("rejected", "details_failed", "audio_failed", "embedding_failed", "failed")
