from __future__ import annotations

from collections.abc import Callable

from app.contracts import ScreenModel, TelegramUserContext
from app.domain.user_import.text_parser import parse_user_vocabulary_text
from app.i18n import translate

ImportScreenBuilder = Callable[[int, str, str | None], ScreenModel]
ImportSubmitter = Callable[[TelegramUserContext, str, str], ScreenModel]


class ClientImportTextInputService:
    def __init__(
        self,
        *,
        build_user_import_screen: ImportScreenBuilder,
        submit_user_vocabulary_import: ImportSubmitter,
    ) -> None:
        self.build_user_import_screen = build_user_import_screen
        self.submit_user_vocabulary_import = submit_user_vocabulary_import

    def handle_text_input(
        self,
        *,
        user: TelegramUserContext,
        locale: str,
        normalized_text: str,
    ) -> ScreenModel | None:
        if normalized_text.startswith("https://docs.google.com/"):
            return self.submit_user_vocabulary_import(user, locale, normalized_text)
        if normalized_text.startswith("http://") or normalized_text.startswith("https://"):
            return self.build_user_import_screen(
                user.telegram_user_id,
                locale,
                translate(locale, "import_words_invalid_url"),
            )
        parsed_words = parse_user_vocabulary_text(normalized_text)
        if parsed_words and self._looks_like_word_list(normalized_text):
            notice = (
                "Імпорт списків слів через текст тимчасово вимкнений. "
                "Скористайся Google Doc або дочекайся оновленого import flow."
            )
            return self.build_user_import_screen(user.telegram_user_id, locale, notice)
        return None

    def _looks_like_word_list(self, value: str) -> bool:
        return "\n" in value or "," in value
