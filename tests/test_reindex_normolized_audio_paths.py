from __future__ import annotations

import json
from pathlib import Path

from word_base.reindex_normolized_audio_paths import reindex_normolized_audio_paths


def test_reindex_normolized_audio_paths_rewrites_bundle_and_moves_legacy_files(tmp_path: Path) -> None:
    audio_dir = tmp_path / "word_base" / "word_audio"
    audio_dir.mkdir(parents=True)
    bundle_path = tmp_path / "normolized_clean_words.json"
    report_path = tmp_path / "audio_reindex_report.json"

    legacy_inside = audio_dir / "inside.mp3"
    legacy_round = audio_dir / "round.mp3"
    legacy_august = audio_dir / "0391_august.mp3"
    legacy_inside.write_bytes(b"inside-audio")
    legacy_round.write_bytes(b"round-audio")
    legacy_august.write_bytes(b"august-audio")

    bundle = {
        "entries": [
            {
                "source_ref": "inside__adverb",
                "word": "inside",
                "audio_path": "word_base/word_audio/inside.mp3",
            },
            {
                "source_ref": "inside__preposition",
                "word": "inside",
                "audio_path": "word_base/word_audio/inside.mp3",
            },
            {
                "source_ref": "round__preposition",
                "word": "round",
                "audio_path": "word_base/word_audio/round.mp3",
            },
            {
                "source_ref": "august__adjective",
                "word": "august",
                "audio_path": "word_base/word_audio/0391_august.mp3",
            },
            {
                "source_ref": "august__noun",
                "word": "August",
                "audio_path": "word_base/word_audio/0391_august.mp3",
            },
            {
                "source_ref": "mute__noun",
                "word": "mute",
                "audio_path": "",
            },
        ]
    }
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = reindex_normolized_audio_paths(
        bundle_path=bundle_path,
        audio_dir=audio_dir,
        report_path=report_path,
    )

    updated_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    entries = {entry["source_ref"]: entry for entry in updated_bundle["entries"]}

    assert entries["inside__adverb"]["audio_path"] == "word_base/word_audio/00001_inside.mp3"
    assert entries["inside__preposition"]["audio_path"] == "word_base/word_audio/00001_inside.mp3"
    assert entries["round__preposition"]["audio_path"] == "word_base/word_audio/00002_round.mp3"
    assert entries["august__adjective"]["audio_path"] == "word_base/word_audio/00003_august.mp3"
    assert entries["august__noun"]["audio_path"] == "word_base/word_audio/00004_august-august-noun.mp3"
    assert entries["mute__noun"]["audio_path"] == ""

    assert (audio_dir / "00001_inside.mp3").read_bytes() == b"inside-audio"
    assert (audio_dir / "00002_round.mp3").read_bytes() == b"round-audio"
    assert (audio_dir / "00003_august.mp3").read_bytes() == b"august-audio"
    assert (audio_dir / "00004_august-august-noun.mp3").read_bytes() == b"august-audio"

    assert not legacy_inside.exists()
    assert not legacy_round.exists()
    assert not legacy_august.exists()

    assert report["reindexed_words"] == 4
    assert report["removed_legacy_count"] == 3
    assert report["linked_count"] == 4
