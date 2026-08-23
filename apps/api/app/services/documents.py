import hashlib
import io
from pathlib import Path

import fitz  # PyMuPDF

from app.config import get_settings
from app.storage.local import LocalStorage


class DocumentProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = LocalStorage()

    def validate_pdf(self, content: bytes, filename: str) -> tuple[bool, str, int]:
        if not filename.lower().endswith(".pdf"):
            return False, "Only PDF files are accepted.", 0
        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            return False, f"File exceeds {self.settings.max_upload_size_mb}MB limit.", 0
        if not content.startswith(b"%PDF"):
            return False, "Invalid PDF file signature.", 0
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = doc.page_count
            doc.close()
        except Exception:
            return False, "Corrupted or unreadable PDF.", 0
        if page_count == 0:
            return False, "PDF contains no pages.", 0
        if page_count > self.settings.max_pdf_pages:
            return False, f"PDF exceeds {self.settings.max_pdf_pages} page limit.", 0
        return True, "OK", page_count

    def compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def render_pages(self, run_id: str, pdf_path: str) -> list[str]:
        doc = fitz.open(pdf_path)
        image_paths: list[str] = []
        max_pages = min(doc.page_count, self.settings.max_pdf_pages)
        for i in range(max_pages):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_paths.append(self.storage.save_image(run_id, i + 1, pix.tobytes("png")))
        doc.close()
        return image_paths

    def save_upload(self, run_id: str, filename: str, content: bytes) -> tuple[str, str, int]:
        valid, message, page_count = self.validate_pdf(content, filename)
        if not valid:
            raise ValueError(message)
        file_hash = self.compute_hash(content)
        file_path = self.storage.save(run_id, filename, content)
        return file_path, file_hash, page_count
