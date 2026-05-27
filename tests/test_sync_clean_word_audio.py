from __future__ import annotations

import json
from pathlib import Path

from word_base.sync_clean_word_audio import sync_clean_word_audio


def build_bundle(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "core:1",
                        "source_namespace": "core",
                        "source_legacy_id": 1,
                        "entry_key": "abandon__verb__entry",
                        "word": "abandon",
                        "normalized_word": "abandon",
                        "entry_type": "word",
                        "level_code": "B2",
                        "parts_of_speech": ["verb"],
                        "category_tags": ["general"],
                        "translation_uk": "покидати",
                        "translation_ru": "покидать",
                        "translation_pl": "porzucać",
                        "transcription": "/əˈbændən/",
                        "examples": ["Abandon ship."],
                        "synonym_source_refs": [],
                    },
                    {
                        "source_ref": "core:2",
                        "source_namespace": "core",
                        "source_legacy_id": 2,
                        "entry_key": "new-word__noun__entry",
                        "word": "new word",
                        "normalized_word": "new word",
                        "entry_type": "word",
                        "level_code": "A1",
                        "parts_of_speech": ["noun"],
                        "category_tags": ["general"],
                        "translation_uk": "нове слово",
                        "translation_ru": "новое слово",
                        "translation_pl": "nowe słowo",
                        "transcription": "/njuː wɜːd/",
                        "examples": ["A new word."],
                        "synonym_source_refs": [],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_sync_clean_word_audio_reuses_existing_and_generates_missing(tmp_path: Path, monkeypatch) -> None:
    bundle_path = tmp_path / "clean_words.json"
    csv_path = tmp_path / "clean_words.csv"
    audio_dir = tmp_path / "word_audio"
    report_path = tmp_path / "audio_sync_report.json"
    status_path = tmp_path / "audio_sync_status.json"
    audio_dir.mkdir()
    (audio_dir / "0001_abandon.mp3").write_bytes(b"existing")
    build_bundle(bundle_path)

    monkeypatch.setattr(
        "word_base.sync_clean_word_audio.synthesize_google_tts",
        lambda **kwargs: b"generated-mp3",
    )
    monkeypatch.setattr(
        "word_base.sync_clean_word_audio.resolve_google_tts_api_key",
        lambda: "configured",
    )

    report = sync_clean_word_audio(
        bundle_path=bundle_path,
        csv_path=csv_path,
        audio_dir=audio_dir,
        report_path=report_path,
        status_path=status_path,
        google_tts_language_code="en-US",
        google_tts_voice_name="en-US-Neural2-F",
        checkpoint_every=1,
        limit=0,
        skip_google_tts_if_unconfigured=False,
    )

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    entries = {entry["source_ref"]: entry for entry in bundle["entries"]}

    assert entries["core:1"]["audio_path"].endswith("0001_abandon.mp3")
    assert entries["core:2"]["audio_path"].endswith("new-word.mp3")
    assert (audio_dir / "new-word.mp3").read_bytes() == b"generated-mp3"
    assert report["stats"]["reused_existing_audio"] == 1
    assert report["stats"]["generated_audio"] == 1


def test_sync_clean_word_audio_can_skip_google_tts_when_key_is_missing(tmp_path: Path, monkeypatch) -> None:
    bundle_path = tmp_path / "clean_words.json"
    csv_path = tmp_path / "clean_words.csv"
    audio_dir = tmp_path / "word_audio"
    report_path = tmp_path / "audio_sync_report.json"
    status_path = tmp_path / "audio_sync_status.json"
    audio_dir.mkdir()
    build_bundle(bundle_path)

    monkeypatch.setattr(
        "word_base.sync_clean_word_audio.resolve_google_tts_api_key",
        lambda: (_ for _ in ()).throw(RuntimeError("GOOGLE_TTS__API_KEY is not configured.")),
    )

    report = sync_clean_word_audio(
        bundle_path=bundle_path,
        csv_path=csv_path,
        audio_dir=audio_dir,
        report_path=report_path,
        status_path=status_path,
        google_tts_language_code="en-US",
        google_tts_voice_name="en-US-Neural2-F",
        checkpoint_every=1,
        limit=0,
        skip_google_tts_if_unconfigured=True,
    )

    assert report["google_tts_enabled"] is False
    assert report["stats"]["missing_audio"] == 2


def test_sync_clean_word_audio_can_force_regenerate_only_verbs_without_csv(tmp_path: Path, monkeypatch) -> None:
    bundle_path = tmp_path / "normolized_clean_words.json"
    csv_path = tmp_path / "normolized_clean_words.csv"
    audio_dir = tmp_path / "word_audio"
    report_path = tmp_path / "audio_sync_report.json"
    status_path = tmp_path / "audio_sync_status.json"
    audio_dir.mkdir()
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "core:1",
                        "source_namespace": "core",
                        "source_legacy_id": 1,
                        "entry_key": "love__verb__entry",
                        "word": "to love",
                        "normalized_word": "to love",
                        "entry_type": "word",
                        "level_code": "A1",
                        "parts_of_speech": ["verb"],
                        "category_tags": ["general"],
                        "translation_uk": "любити",
                        "translation_ru": "любить",
                        "translation_pl": "kochać",
                        "transcription": "/lʌv/",
                        "audio_path": str((audio_dir / "love.mp3").as_posix()),
                        "examples": ["I love music."],
                        "synonym_source_refs": [],
                    },
                    {
                        "source_ref": "core:2",
                        "source_namespace": "core",
                        "source_legacy_id": 2,
                        "entry_key": "look-after__phrasal-verb__entry",
                        "word": "to look after",
                        "normalized_word": "to look after",
                        "entry_type": "phrasal_verb",
                        "level_code": "A2",
                        "parts_of_speech": ["phrasal verb"],
                        "category_tags": ["general"],
                        "translation_uk": "доглядати",
                        "translation_ru": "заботиться",
                        "translation_pl": "opiekować się",
                        "transcription": "/lʊk ˈæf.tɚ/",
                        "audio_path": "",
                        "examples": ["They look after the child."],
                        "synonym_source_refs": [],
                    },
                    {
                        "source_ref": "core:3",
                        "source_namespace": "core",
                        "source_legacy_id": 3,
                        "entry_key": "care__noun__entry",
                        "word": "care",
                        "normalized_word": "care",
                        "entry_type": "word",
                        "level_code": "A2",
                        "parts_of_speech": ["noun"],
                        "category_tags": ["general"],
                        "translation_uk": "турбота",
                        "translation_ru": "забота",
                        "translation_pl": "opieka",
                        "transcription": "/ker/",
                        "audio_path": str((audio_dir / "care.mp3").as_posix()),
                        "examples": ["Care matters."],
                        "synonym_source_refs": [],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (audio_dir / "love.mp3").write_bytes(b"old-love")
    (audio_dir / "care.mp3").write_bytes(b"old-care")

    generated_payloads: list[str] = []

    def fake_synthesize_google_tts(**kwargs):
        generated_payloads.append(kwargs["text"])
        return f"audio:{kwargs['text']}".encode()

    monkeypatch.setattr(
        "word_base.sync_clean_word_audio.synthesize_google_tts",
        fake_synthesize_google_tts,
    )
    monkeypatch.setattr(
        "word_base.sync_clean_word_audio.resolve_google_tts_api_key",
        lambda: "configured",
    )

    report = sync_clean_word_audio(
        bundle_path=bundle_path,
        csv_path=csv_path,
        audio_dir=audio_dir,
        report_path=report_path,
        status_path=status_path,
        google_tts_language_code="en-US",
        google_tts_voice_name="en-US-Neural2-F",
        checkpoint_every=1,
        limit=0,
        skip_google_tts_if_unconfigured=False,
        skip_csv=True,
        only_verbs=True,
        force_regenerate_existing=True,
    )

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    entries = {entry["source_ref"]: entry for entry in bundle["entries"]}

    assert generated_payloads == ["to love", "to look after"]
    assert entries["core:1"]["audio_path"].endswith("love.mp3")
    assert entries["core:2"]["audio_path"].endswith("to-look-after.mp3")
    assert entries["core:3"]["audio_path"].endswith("care.mp3")
    assert (audio_dir / "love.mp3").read_bytes() == b"audio:to love"
    assert (audio_dir / "to-look-after.mp3").read_bytes() == b"audio:to look after"
    assert (audio_dir / "care.mp3").read_bytes() == b"old-care"
    assert not csv_path.exists()
    assert report["stats"]["total_entries"] == 2
    assert report["stats"]["generated_audio"] == 2
    assert report["only_verbs"] is True
    assert report["force_regenerate_existing"] is True
    assert report["skip_csv"] is True


def test_sync_clean_word_audio_can_regenerate_only_placeholder_patterns(tmp_path: Path, monkeypatch) -> None:
    bundle_path = tmp_path / "normolized_phrase_entries.json"
    csv_path = tmp_path / "normolized_phrase_entries.csv"
    audio_dir = tmp_path / "phrase_pattern"
    report_path = tmp_path / "phrase_audio_sync_report.json"
    status_path = tmp_path / "phrase_audio_sync_status.json"
    audio_dir.mkdir()
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "phrase:1",
                        "source_namespace": "generated_phrase_entries",
                        "source_legacy_id": "",
                        "entry_key": "talk-about-smth__phrase-pattern__entry",
                        "word": "talk about smth",
                        "normalized_word": "talk about smth",
                        "entry_type": "phrase_pattern",
                        "level_code": "A1",
                        "parts_of_speech": ["phrase pattern"],
                        "category_tags": ["general"],
                        "translation_uk": "говорити про щось",
                        "translation_ru": "говорить о чём-то",
                        "translation_pl": "mowić o czymś",
                        "transcription": "/tɔk əˈbaʊt sʌmθɪŋ/",
                        "audio_path": str((audio_dir / "talk-about-smth.mp3").as_posix()),
                        "examples": ["We talk about music."],
                        "synonym_source_refs": [],
                    },
                    {
                        "source_ref": "phrase:2",
                        "source_namespace": "generated_phrase_entries",
                        "source_legacy_id": "",
                        "entry_key": "break-the-ice__idiom__entry",
                        "word": "break the ice",
                        "normalized_word": "break the ice",
                        "entry_type": "idiom",
                        "level_code": "A2",
                        "parts_of_speech": ["idiom"],
                        "category_tags": ["general"],
                        "translation_uk": "розрядити обстановку",
                        "translation_ru": "растопить лед",
                        "translation_pl": "przełamać lody",
                        "transcription": "/breɪk ði aɪs/",
                        "audio_path": str((audio_dir / "break-the-ice.mp3").as_posix()),
                        "examples": ["He told a joke to break the ice."],
                        "synonym_source_refs": [],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (audio_dir / "talk-about-smth.mp3").write_bytes(b"old-pattern")
    (audio_dir / "break-the-ice.mp3").write_bytes(b"old-idiom")

    generated_payloads: list[str] = []

    def fake_synthesize_google_tts(**kwargs):
        generated_payloads.append(kwargs["text"])
        return f"audio:{kwargs['text']}".encode()

    monkeypatch.setattr(
        "word_base.sync_clean_word_audio.synthesize_google_tts",
        fake_synthesize_google_tts,
    )
    monkeypatch.setattr(
        "word_base.sync_clean_word_audio.resolve_google_tts_api_key",
        lambda: "configured",
    )

    report = sync_clean_word_audio(
        bundle_path=bundle_path,
        csv_path=csv_path,
        audio_dir=audio_dir,
        report_path=report_path,
        status_path=status_path,
        google_tts_language_code="en-US",
        google_tts_voice_name="en-US-Neural2-F",
        checkpoint_every=1,
        limit=0,
        skip_google_tts_if_unconfigured=False,
        skip_csv=True,
        only_placeholder_patterns=True,
        force_regenerate_existing=True,
    )

    assert generated_payloads == ["talk about smth"]
    assert (audio_dir / "talk-about-smth.mp3").read_bytes() == b"audio:talk about smth"
    assert (audio_dir / "break-the-ice.mp3").read_bytes() == b"old-idiom"
    assert report["stats"]["total_entries"] == 1
    assert report["stats"]["generated_audio"] == 1
    assert report["only_placeholder_patterns"] is True
