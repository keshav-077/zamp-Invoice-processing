from pathlib import Path

from app.config import get_settings


class LocalStorage:
    def __init__(self) -> None:
        self.base = get_settings().storage_dir

    def save(self, run_id: str, filename: str, content: bytes) -> str:
        run_dir = self.base / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(filename).name
        path = run_dir / safe_name
        path.write_bytes(content)
        return str(path)

    def save_image(self, run_id: str, page_num: int, content: bytes) -> str:
        run_dir = self.base / run_id / "pages"
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"page_{page_num:03d}.png"
        path.write_bytes(content)
        return str(path)

    def read(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def exists(self, path: str) -> bool:
        return Path(path).exists()
