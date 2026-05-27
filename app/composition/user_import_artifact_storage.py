from __future__ import annotations

from typing import Any

from app.storage.user_import_artifacts import (
    FileSystemUserImportArtifactStorageProvider,
    UserImportArtifactStorageProvider,
)


def build_user_import_artifact_storage_provider(
    settings: Any,
) -> UserImportArtifactStorageProvider:
    return FileSystemUserImportArtifactStorageProvider(
        settings.app_user_import_storage_dir,
    )
