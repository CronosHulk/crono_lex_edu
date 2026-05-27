from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.billing.services.receipt_storage_port import (
    BillingReceiptArtifactRef,
    BillingReceiptStorageProvider,
)
from app.helpers.user_import_storage import write_bytes_atomic


class FileSystemBillingReceiptStorageProvider(BillingReceiptStorageProvider):
    def __init__(
        self,
        storage_dir: str | Path,
        *,
        write_bytes_atomic: Callable[[Path, bytes], None] = write_bytes_atomic,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.write_bytes_atomic = write_bytes_atomic

    def write_receipt_file(self, *, receipt_id: int, payload: bytes) -> BillingReceiptArtifactRef:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        path = self.storage_dir / f"billing_receipt_{int(receipt_id)}.pdf"
        self.write_bytes_atomic(path, payload)
        return BillingReceiptArtifactRef(path=str(path), filename=path.name)
