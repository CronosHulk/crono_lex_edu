from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BillingReceiptArtifactRef:
    path: str
    filename: str


class BillingReceiptStorageProvider(Protocol):
    def write_receipt_file(self, *, receipt_id: int, payload: bytes) -> BillingReceiptArtifactRef: ...
