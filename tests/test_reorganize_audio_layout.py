from __future__ import annotations

import json
from pathlib import Path

import pytest

from word_base.reorganize_audio_layout import reorganize_audio_layout


def write_bundle(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_entries(path: Path) -> dict[str, dict[str, object]]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return {str(entry["source_ref"]): entry for entry in bundle["entries"]}


def test_reorganize_audio_layout_dry_run_reports_without_rewriting_normolized_json(tmp_path: Path) -> None:
    project_root = tmp_path
    word_audio_dir = project_root / "word_base" / "word_audio"
    phrase_audio_dir = project_root / "word_base" / "phrase_audio"
    word_audio_dir.mkdir(parents=True)
    phrase_audio_dir.mkdir(parents=True)
    (word_audio_dir / "inside.mp3").write_bytes(b"inside-audio")
    (phrase_audio_dir / "break-the-ice.mp3").write_bytes(b"phrase-audio")

    words_bundle_path = project_root / "word_base" / "json_sources" / "normolized_clean_words.json"
    phrases_bundle_path = project_root / "word_base" / "json_sources" / "normolized_phrase_entries.json"
    words_bundle_path.parent.mkdir(parents=True)
    write_bundle(
        words_bundle_path,
        [
            {
                "source_ref": "inside__adverb",
                "word": "inside",
                "parts_of_speech": ["adverb"],
                "audio_path": "word_base/word_audio/inside.mp3",
            }
        ],
    )
    write_bundle(
        phrases_bundle_path,
        [
            {
                "source_ref": "break_the_ice__phrase",
                "word": "break the ice",
                "entry_type": "phrase",
                "audio_path": "word_base/phrase_audio/break-the-ice.mp3",
            }
        ],
    )
    report_path = project_root / "word_base" / "json_sources" / "audio_layout_report.json"

    report = reorganize_audio_layout(
        bundle_paths=[words_bundle_path, phrases_bundle_path],
        project_root=project_root,
        namespace="base",
        report_path=report_path,
    )

    words = read_entries(words_bundle_path)
    phrases = read_entries(phrases_bundle_path)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert words["inside__adverb"]["audio_path"] == "word_base/word_audio/inside.mp3"
    assert phrases["break_the_ice__phrase"]["audio_path"] == "word_base/phrase_audio/break-the-ice.mp3"
    assert not (project_root / "word_base" / "base" / "adverb" / "inside.mp3").exists()
    assert not (project_root / "word_base" / "base" / "phrase" / "break-the-ice.mp3").exists()
    assert report["operation_count"] == 2
    assert report_payload["operation_count"] == 2
    assert report_payload["apply"] is False


def test_reorganize_audio_layout_apply_rewrites_normolized_json_and_preserves_legacy_files(tmp_path: Path) -> None:
    project_root = tmp_path
    word_audio_dir = project_root / "word_base" / "word_audio"
    phrase_audio_dir = project_root / "word_base" / "phrase_audio"
    word_audio_dir.mkdir(parents=True)
    phrase_audio_dir.mkdir(parents=True)
    word_audio = word_audio_dir / "inside.mp3"
    phrase_audio = phrase_audio_dir / "break-the-ice.mp3"
    word_audio.write_bytes(b"inside-audio")
    phrase_audio.write_bytes(b"phrase-audio")

    words_bundle_path = project_root / "word_base" / "json_sources" / "normolized_clean_words.json"
    phrases_bundle_path = project_root / "word_base" / "json_sources" / "normolized_phrase_entries.json"
    words_bundle_path.parent.mkdir(parents=True)
    write_bundle(
        words_bundle_path,
        [
            {
                "source_ref": "inside__adverb",
                "word": "inside",
                "parts_of_speech": ["adverb"],
                "audio_path": "word_base/word_audio/inside.mp3",
            }
        ],
    )
    write_bundle(
        phrases_bundle_path,
        [
            {
                "source_ref": "break_the_ice__phrase",
                "word": "break the ice",
                "entry_type": "phrase",
                "audio_path": "word_base/phrase_audio/break-the-ice.mp3",
            }
        ],
    )

    report = reorganize_audio_layout(
        bundle_paths=[words_bundle_path, phrases_bundle_path],
        project_root=project_root,
        namespace="base",
        report_path=project_root / "word_base" / "json_sources" / "audio_layout_report.json",
        apply=True,
        copy_only=True,
    )

    words = read_entries(words_bundle_path)
    phrases = read_entries(phrases_bundle_path)

    assert words["inside__adverb"]["audio_path"] == "word_base/base/adverb/inside.mp3"
    assert phrases["break_the_ice__phrase"]["audio_path"] == "word_base/base/phrase/break-the-ice.mp3"
    assert (project_root / "word_base" / "base" / "adverb" / "inside.mp3").read_bytes() == b"inside-audio"
    assert (project_root / "word_base" / "base" / "phrase" / "break-the-ice.mp3").read_bytes() == b"phrase-audio"
    assert word_audio.exists()
    assert phrase_audio.exists()
    assert report["stale_path_count"] == 0
    assert report["removed_legacy_count"] == 0


def test_reorganize_audio_layout_apply_syncs_nested_audio_report_paths(tmp_path: Path) -> None:
    project_root = tmp_path
    phrase_audio_dir = project_root / "word_base" / "phrase_audio"
    phrase_audio_dir.mkdir(parents=True)
    phrase_audio = phrase_audio_dir / "break-the-ice.mp3"
    phrase_audio.write_bytes(b"phrase-audio")
    bundle_path = project_root / "word_base" / "json_sources" / "normolized_phrase_entries.json"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "source_ref": "phrase:1",
                        "word": "break the ice",
                        "entry_type": "phrase",
                        "audio_path": "word_base/phrase_audio/break-the-ice.mp3",
                    }
                ],
                "audio_sync_report": {
                    "generated_entries": [
                        {"source_ref": "phrase:1", "audio_path": "word_base/phrase_audio/break-the-ice.mp3"}
                    ]
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    reorganize_audio_layout(
        bundle_paths=[bundle_path],
        project_root=project_root,
        namespace="base",
        report_path=project_root / "report.json",
        apply=True,
        copy_only=True,
    )

    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert payload["entries"][0]["audio_path"] == "word_base/base/phrase/break-the-ice.mp3"
    assert payload["audio_sync_report"]["generated_entries"][0]["audio_path"] == (
        "word_base/base/phrase/break-the-ice.mp3"
    )


def test_reorganize_audio_layout_remove_legacy_only_after_successful_apply(tmp_path: Path) -> None:
    project_root = tmp_path
    audio_dir = project_root / "word_base" / "word_audio"
    audio_dir.mkdir(parents=True)
    legacy_audio = audio_dir / "inside.mp3"
    legacy_audio.write_bytes(b"inside-audio")
    bundle_path = project_root / "word_base" / "json_sources" / "normolized_clean_words.json"
    bundle_path.parent.mkdir(parents=True)
    write_bundle(
        bundle_path,
        [
            {
                "source_ref": "inside__adverb",
                "word": "inside",
                "parts_of_speech": ["adverb"],
                "audio_path": "word_base/word_audio/inside.mp3",
            }
        ],
    )

    report = reorganize_audio_layout(
        bundle_paths=[bundle_path],
        project_root=project_root,
        namespace="base",
        report_path=project_root / "report.json",
        apply=True,
        remove_legacy=True,
        copy_only=True,
    )

    assert not legacy_audio.exists()
    assert (project_root / "word_base" / "base" / "adverb" / "inside.mp3").exists()
    assert report["removed_legacy_count"] == 1


def test_reorganize_audio_layout_uses_source_ref_suffix_on_target_collision(tmp_path: Path) -> None:
    project_root = tmp_path
    audio_dir = project_root / "word_base" / "word_audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "round-adjective.mp3").write_bytes(b"adjective")
    (audio_dir / "round-noun.mp3").write_bytes(b"noun")
    bundle_path = project_root / "word_base" / "json_sources" / "normolized_clean_words.json"
    bundle_path.parent.mkdir(parents=True)
    write_bundle(
        bundle_path,
        [
            {
                "source_ref": "round__adjective",
                "word": "round",
                "parts_of_speech": ["adjective"],
                "audio_path": "word_base/word_audio/round-adjective.mp3",
            },
            {
                "source_ref": "round__adjective_variant",
                "word": "round",
                "parts_of_speech": ["adjective"],
                "audio_path": "word_base/word_audio/round-noun.mp3",
            },
        ],
    )

    reorganize_audio_layout(
        bundle_paths=[bundle_path],
        project_root=project_root,
        namespace="base",
        report_path=project_root / "report.json",
        apply=True,
        copy_only=True,
    )

    entries = read_entries(bundle_path)
    assert entries["round__adjective"]["audio_path"] == "word_base/base/adjective/round.mp3"
    assert entries["round__adjective_variant"]["audio_path"] == (
        "word_base/base/adjective/round-round-adjective-variant.mp3"
    )


def test_reorganize_audio_layout_rejects_missing_or_unsafe_audio_without_rewriting_bundle(tmp_path: Path) -> None:
    project_root = tmp_path
    bundle_path = project_root / "word_base" / "json_sources" / "normolized_clean_words.json"
    bundle_path.parent.mkdir(parents=True)
    write_bundle(
        bundle_path,
        [
            {
                "source_ref": "missing__noun",
                "word": "missing",
                "parts_of_speech": ["noun"],
                "audio_path": "word_base/word_audio/missing.mp3",
            },
            {
                "source_ref": "escape__noun",
                "word": "escape",
                "parts_of_speech": ["noun"],
                "audio_path": "../escape.mp3",
            },
        ],
    )
    original_payload = bundle_path.read_text(encoding="utf-8")
    report_path = project_root / "report.json"

    with pytest.raises(ValueError, match="Missing or unsafe audio files"):
        reorganize_audio_layout(
            bundle_paths=[bundle_path],
            project_root=project_root,
            namespace="base",
            report_path=report_path,
            apply=True,
            copy_only=True,
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert bundle_path.read_text(encoding="utf-8") == original_payload
    assert report["missing_file_count"] == 2
    assert report["apply"] is True
