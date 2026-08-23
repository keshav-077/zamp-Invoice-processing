import hashlib
import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from app.config import get_settings
from app.storage.local import LocalStorage

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def is_allowed_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def is_pdf(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".pdf"


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


class DocumentProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = LocalStorage()

    def _check_size(self, content: bytes) -> tuple[bool, str]:
        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            return False, f"File exceeds {self.settings.max_upload_size_mb}MB limit."
        return True, "OK"

    def validate_pdf(self, content: bytes, filename: str) -> tuple[bool, str, int]:
        if not is_pdf(filename):
            return False, "Only PDF and image files are accepted.", 0
        ok, message = self._check_size(content)
        if not ok:
            return False, message, 0
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

    def validate_image(self, content: bytes, filename: str) -> tuple[bool, str, int]:
        if not is_image(filename):
            return False, "Only PDF and image files are accepted.", 0
        ok, message = self._check_size(content)
        if not ok:
            return False, message, 0
        ext = Path(filename).suffix.lower()
        if ext == ".png" and not content.startswith(b"\x89PNG"):
            return False, "Invalid PNG file signature.", 0
        if ext in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            return False, "Invalid JPEG file signature.", 0
        if ext == ".webp" and not (content.startswith(b"RIFF") and b"WEBP" in content[:16]):
            return False, "Invalid WebP file signature.", 0
        try:
            with Image.open(io.BytesIO(content)) as img:
                img.verify()
        except Exception:
            return False, "Corrupted or unreadable image.", 0
        return True, "OK", 1

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

    def _normalize_image_to_png(self, content: bytes) -> bytes:
        with Image.open(io.BytesIO(content)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

    def prepare_images(self, run_id: str, file_path: str) -> list[str]:
        filename = Path(file_path).name
        if is_pdf(filename):
            return self.render_pages(run_id, file_path)
        content = Path(file_path).read_bytes()
        png_bytes = self._normalize_image_to_png(content)
        return [self.storage.save_image(run_id, 1, png_bytes)]

    def save_upload(self, run_id: str, filename: str, content: bytes) -> tuple[str, str, int]:
        if not is_allowed_extension(filename):
            raise ValueError("Only PDF, PNG, JPG, and WebP files are accepted.")
        if is_pdf(filename):
            valid, message, page_count = self.validate_pdf(content, filename)
        else:
            valid, message, page_count = self.validate_image(content, filename)
        if not valid:
            raise ValueError(message)
        file_hash = self.compute_hash(content)
        file_path = self.storage.save(run_id, filename, content)
        return file_path, file_hash, page_count
