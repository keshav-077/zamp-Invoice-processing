from abc import ABC, abstractmethod
from typing import Any

from app.domain.invoice import InvoiceExtracted


class ExtractionProvider(ABC):
    name: str
    supports_verification: bool = False

    @abstractmethod
    async def extract_invoice(self, image_paths: list[str], file_name: str) -> tuple[InvoiceExtracted, dict[str, Any]]:
        pass

    @abstractmethod
    async def verify_invoice(
        self, extracted: InvoiceExtracted, image_paths: list[str]
    ) -> tuple[InvoiceExtracted, dict[str, Any]]:
        pass
