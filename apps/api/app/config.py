from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/app/config.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]


def _resolve_env_files() -> tuple[str, ...]:
    candidates = (REPO_ROOT / ".env", API_ROOT / ".env")
    return tuple(str(path) for path in candidates if path.is_file())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files() or None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./data/invoice.db"
    storage_path: str = "./data/uploads"
    cors_origins: str = "http://localhost:3000"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.6-27b"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-3.6-flash"
    use_mock_extraction: bool = True

    amount_tolerance_percent: float = 2.0
    amount_tolerance_absolute: float = 50.0
    rounding_tolerance: float = 0.05
    po_match_min_score: float = 0.85
    po_match_possible_score: float = 0.70
    po_match_min_margin: float = 0.10
    po_weight_reference: float = 0.40
    po_weight_vendor: float = 0.20
    po_weight_amount: float = 0.15
    po_weight_line_items: float = 0.10
    po_weight_quantity: float = 0.05
    po_weight_date: float = 0.05
    po_weight_semantic: float = 0.05
    vendor_match_min_score: float = 0.85
    extraction_confidence_threshold: float = 0.75
    duplicate_decision: str = "REVIEW"
    po_closed_decision: str = "REJECT"
    po_cancelled_decision: str = "REJECT"
    currency_mismatch_decision: str = "REJECT"
    amount_over_tolerance_decision: str = "REVIEW"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    max_upload_size_mb: int = 20
    max_pdf_pages: int = 10
    log_level: str = "INFO"

    @model_validator(mode="after")
    def resolve_local_paths(self) -> "Settings":
        sqlite_prefix = "sqlite+aiosqlite:///"
        if self.database_url.startswith(sqlite_prefix):
            database_path = self.database_url[len(sqlite_prefix):]
            path = Path(database_path)
            if database_path != ":memory:" and not path.is_absolute():
                path = (API_ROOT / path).resolve()
                self.database_url = sqlite_prefix + path.as_posix()

        storage_path = Path(self.storage_path)
        if not storage_path.is_absolute():
            self.storage_path = str((API_ROOT / storage_path).resolve())
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_dir(self) -> Path:
        path = Path(self.storage_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
