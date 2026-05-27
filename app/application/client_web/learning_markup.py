from __future__ import annotations

import html
from html.parser import HTMLParser

WORD_JOINER = "\u2060"


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "br":
            self._chunks.append("\n")

    def text(self) -> str:
        return "".join(self._chunks).strip()


def telegram_html_to_text(value: str | None) -> str:
    if not value:
        return ""
    parser = _HtmlTextExtractor()
    parser.feed(str(value))
    parser.close()
    text = parser.text().replace(WORD_JOINER, "").strip()
    for _ in range(2):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    return text.strip()
