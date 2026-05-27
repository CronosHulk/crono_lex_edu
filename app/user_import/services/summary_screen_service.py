from __future__ import annotations

import html
from collections.abc import Callable, Sequence
from typing import Any

from app.contracts import ButtonModel, DocumentAttachmentModel, ScreenModel
from app.i18n import translate
from app.screen_delivery_policy import (
    with_delete_after_hours,
    with_documents_only_delivery,
)
from app.user_import.services.helpers import (
    format_failed_import_item,
    format_import_count_text,
    format_numbered_import_item_list,
    normalize_nonempty_strings,
)


class UserImportSummaryScreenService:
    def __init__(self, *, build_import_url: Callable[[int], str] | None = None) -> None:
        self.build_import_url = build_import_url

    def build_user_import_document_screen(
        self,
        *,
        job_id: int,
        slice_name: str,
        documents: Sequence[DocumentAttachmentModel | None],
    ) -> ScreenModel:
        screen = ScreenModel(
            screen_id=f"import_words:documents:{slice_name}:{job_id}",
            text="",
            documents=[document for document in documents if document is not None],
            keyboard_type="inline",
        )
        return with_documents_only_delivery(with_delete_after_hours(screen, 24))

    def build_user_import_intake_slice_screen(
        self,
        *,
        locale: str,
        job_id: int,
        slice_name: str,
        intake_snapshot: dict[str, Any],
    ) -> ScreenModel:
        if slice_name == "existing":
            title_key = "import_words_existing_list_title"
            values = intake_snapshot["existing_lookup_words"]
            screen_suffix = "existing"
        elif slice_name == "queued":
            title_key = "import_words_queued_list_title"
            values = intake_snapshot["queued_lookup_words"]
            screen_suffix = "queued"
        else:
            title_key = "import_words_invalid_list_title"
            values = intake_snapshot["invalid_fragments"]
            screen_suffix = "invalid"
        lines = [translate(locale, title_key)]
        formatted = format_numbered_import_item_list(locale, values)
        if formatted:
            lines.append(formatted)
        else:
            lines.append(translate(locale, "import_words_intake_list_empty"))
        screen = ScreenModel(
            screen_id=f"import_words:{screen_suffix}:{job_id}",
            text="\n\n".join(lines),
            buttons=[
                ButtonModel(action=f"m:i:summary:{job_id}", text=translate(locale, "menu_back")),
                ButtonModel(action=f"m:i:delete:{job_id}", text=translate(locale, "import_words_delete_button")),
                ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
            ],
            keyboard_type="inline",
            metadata={"buttons_per_row": 1, "sticky_import_report": True},
        )
        return with_delete_after_hours(screen, 24)

    def build_user_import_summary_screen(
        self,
        *,
        locale: str,
        job_id: int,
        items: list[dict[str, Any]],
        job_status: str,
        last_error: str | None = None,
        notice: str | None = None,
        technical_details: str | None = None,
        intake_snapshot: dict[str, Any] | None = None,
        documents: list[DocumentAttachmentModel] | None = None,
        telegram_user_id: int | None = None,
    ) -> ScreenModel:
        intake_snapshot = intake_snapshot or {}
        review_count = len(
            [
                item
                for item in items
                if item["status"]
                in {
                    "queued_for_attributes",
                    "ready_for_attribute_review",
                    "ready_for_review",
                    "approved",
                    "ready_for_embedding",
                    "ready_for_publish",
                    "awaiting_audio",
                }
            ]
        )
        added_count = (
            len(intake_snapshot.get("existing_lookup_words", []))
            if intake_snapshot.get("existing_lookup_words") is not None
            else len([item for item in items if item["status"] == "found_existing"])
        )
        added_count += len([item for item in items if item["status"] == "imported"])
        invalid_count = int(intake_snapshot.get("invalid_fragments_count") or 0)
        rejected_count = invalid_count + len([item for item in items if item["status"] in {"rejected", "build_failed", "failed"}])

        lines = [translate(locale, "import_words_report_title")]
        if notice:
            lines.append(notice)
        if job_status == "failed":
            lines.append(
                translate(
                    locale,
                    "import_words_summary_failed_job",
                    error=html.escape(last_error or "невідома помилка"),
                )
            )
        lines.append(
            translate(locale, "import_words_report_added_count", count_text=format_import_count_text(locale, added_count))
        )
        lines.append(
            translate(locale, "import_words_report_rejected_count", count_text=format_import_count_text(locale, rejected_count))
        )
        lines.append(
            translate(locale, "import_words_report_review_count", count_text=format_import_count_text(locale, review_count))
        )
        buttons = []
        import_url = self.build_import_url(telegram_user_id) if self.build_import_url is not None and telegram_user_id is not None else ""
        if import_url:
            buttons.append(
                ButtonModel(
                    action=f"web:import:{job_id}",
                    text=translate(locale, "import_words_report_open_import_button"),
                    url=import_url,
                )
            )
        buttons.append(ButtonModel(action=f"m:i:delete:{job_id}", text=translate(locale, "import_words_report_close_button")))
        screen = ScreenModel(
            screen_id=f"import_words:summary:{job_id}",
            text="\n\n".join(lines),
            buttons=buttons,
            keyboard_type="inline",
            metadata={"buttons_per_row": 1, "sticky_import_report": True},
        )
        return with_delete_after_hours(screen, 24)

    def build_user_import_failed_items_screen(
        self,
        *,
        locale: str,
        job_id: int,
        items: list[dict[str, Any]],
        intake_snapshot: dict[str, Any],
        technical_details: str | None = None,
    ) -> ScreenModel:
        rejected = normalize_nonempty_strings(intake_snapshot.get("invalid_fragments"))
        if not rejected:
            rejected = [
                format_failed_import_item(item)
                for item in items
                if item["status"] in {"rejected", "build_failed", "failed"}
            ]
        lines = [translate(locale, "import_words_failed_list_title")]
        if rejected:
            lines.append(format_numbered_import_item_list(locale, rejected[:100]) or "\n\n".join(rejected[:100]))
            if len(rejected) > 100:
                lines.append(
                    translate(
                        locale,
                        "import_words_summary_more_suffix",
                        count_text=format_import_count_text(locale, len(rejected) - 100),
                    )
                )
        else:
            lines.append(translate(locale, "import_words_failed_list_empty"))
        if technical_details:
            lines.append(technical_details)
        screen = ScreenModel(
            screen_id=f"import_words:failed:{job_id}",
            text="\n\n".join(lines),
            buttons=[
                ButtonModel(action=f"m:i:summary:{job_id}", text=translate(locale, "menu_back")),
                ButtonModel(action=f"m:i:delete:{job_id}", text=translate(locale, "import_words_delete_button")),
                ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
            ],
            keyboard_type="inline",
            metadata={"buttons_per_row": 1, "sticky_import_report": True},
        )
        return with_delete_after_hours(screen, 24)

    def build_user_import_publish_summary_screen(
        self,
        *,
        locale: str,
        job_id: int,
        items: list[dict[str, Any]],
        priority_count: int,
        documents: list[DocumentAttachmentModel],
    ) -> ScreenModel:
        imported_items = [item for item in items if item["status"] == "imported"]
        lines = [
            translate(locale, "import_words_publish_summary_title"),
            translate(
                locale,
                "import_words_publish_summary_count",
                count_text=format_import_count_text(locale, len(imported_items)),
            ),
        ]
        if priority_count > 0:
            lines.append(
                translate(
                    locale,
                    "import_words_publish_summary_priority_count",
                    count_text=format_import_count_text(locale, priority_count),
                )
            )
        screen = ScreenModel(
            screen_id=f"import_words:published:{job_id}",
            text="\n\n".join(lines),
            buttons=[
                ButtonModel(action=f"m:i:summary:{job_id}", text=translate(locale, "menu_back")),
                ButtonModel(action=f"m:i:delete:{job_id}", text=translate(locale, "import_words_delete_button")),
                ButtonModel(action="m:menu", text=translate(locale, "menu_back_to_menu")),
            ],
            documents=documents,
            keyboard_type="inline",
            metadata={"buttons_per_row": 1, "sticky_import_report": True},
        )
        return with_delete_after_hours(screen, 24)
