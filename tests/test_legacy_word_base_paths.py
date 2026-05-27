from __future__ import annotations

import re
import subprocess
from pathlib import Path

DEPRECATED_WORD_BASE_PATHS = (
    "word_base/pending requests from users",
    "word_base/ready to upload",
    "word_base/snapshot",
)

LEGACY_CSV_ARTIFACT_NAMES = (
    "clean_words.csv",
    "normolized_clean_words.csv",
)

ACTIVE_RUNTIME_ROOTS = (
    Path("app"),
    Path("migrations"),
)

REQUIRED_WORD_BASE_PATHS = (
    Path("word_base/sync_clean_word_audio.py"),
    Path("word_base/prepare_google_sheet_words.py"),
    Path("word_base/regenerate_seed_migrations.py"),
    Path("word_base/base"),
    Path("word_base/json_sources"),
)

SCANNED_PATHS = (
    Path("app"),
    Path("migrations"),
    Path("word_base"),
    Path("README.md"),
)

ALLOWED_FILES = {
    Path("word_base/pending requests from users/pending_requests_from_users.csv"),
    Path("word_base/ready to upload/ready_to_upload.csv"),
    Path("word_base/snapshot/snapshot.csv"),
}


def _iter_scanned_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in SCANNED_PATHS:
        absolute = root / path
        if absolute.is_file():
            files.append(absolute)
            continue
        if not absolute.exists():
            continue
        files.extend(candidate for candidate in absolute.rglob("*") if candidate.is_file())
    return files


def _iter_active_runtime_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in ACTIVE_RUNTIME_ROOTS:
        absolute = root / path
        if absolute.is_file():
            files.append(absolute)
            continue
        if not absolute.exists():
            continue
        files.extend(candidate for candidate in absolute.rglob("*") if candidate.is_file())
    return files


def _legacy_csv_artifact_reference_offenders(root: Path) -> list[str]:
    offenders: list[str] = []
    for file_path in _iter_active_runtime_files(root):
        relative_path = file_path.relative_to(root)
        if "__pycache__" in relative_path.parts:
            continue
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, 1):
            for artifact_name in LEGACY_CSV_ARTIFACT_NAMES:
                if _line_references_artifact(line, artifact_name):
                    offenders.append(f"{relative_path}:{line_number}: {artifact_name}")
    return offenders


def _line_references_artifact(line: str, artifact_name: str) -> bool:
    return re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(artifact_name)}(?![A-Za-z0-9_])",
        line,
    ) is not None


def _tracked_word_base_base_mp3_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "word_base/base"],
        capture_output=True,
        check=True,
        text=True,
    )
    return [
        Path(line)
        for line in result.stdout.splitlines()
        if line.endswith(".mp3")
    ]


def test_deprecated_word_base_csv_paths_are_not_runtime_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for file_path in _iter_scanned_files(root):
        relative_path = file_path.relative_to(root)
        if relative_path in ALLOWED_FILES:
            continue
        if "__pycache__" in relative_path.parts:
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for deprecated_path in DEPRECATED_WORD_BASE_PATHS:
            if deprecated_path in content:
                offenders.append(f"{relative_path}: {deprecated_path}")

    assert offenders == []


def test_legacy_csv_artifacts_are_not_active_runtime_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]

    assert _legacy_csv_artifact_reference_offenders(root) == []


def test_legacy_csv_artifact_detection_scans_only_active_runtime_roots(
    tmp_path: Path,
) -> None:
    app_module = tmp_path / "app" / "service.py"
    migration = tmp_path / "migrations" / "001.sql"
    word_base_tool = tmp_path / "word_base" / "tool.py"
    test_module = tmp_path / "tests" / "test_tooling.py"
    app_module.parent.mkdir(parents=True)
    migration.parent.mkdir(parents=True)
    word_base_tool.parent.mkdir(parents=True)
    test_module.parent.mkdir(parents=True)
    app_module.write_text('SOURCE = "clean_words.csv"\n', encoding="utf-8")
    migration.write_text("-- normolized_clean_words.csv\n", encoding="utf-8")
    word_base_tool.write_text('TOOL_INPUT = "clean_words.csv"\n', encoding="utf-8")
    test_module.write_text('csv_name = "normolized_clean_words.csv"\n', encoding="utf-8")

    assert _legacy_csv_artifact_reference_offenders(tmp_path) == [
        "app/service.py:1: clean_words.csv",
        "migrations/001.sql:1: normolized_clean_words.csv",
    ]


def test_required_word_base_tooling_and_seed_audio_layout_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    missing_paths = [
        path.as_posix()
        for path in REQUIRED_WORD_BASE_PATHS
        if not (root / path).exists()
    ]

    assert missing_paths == []
    assert _tracked_word_base_base_mp3_paths(root) != []
