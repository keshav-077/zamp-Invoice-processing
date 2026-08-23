from types import SimpleNamespace

import pytest

from app.config import API_ROOT, Settings
from app.providers import factory
from app.providers.mock import MockExtractionProvider


class StubProvider:
    def __init__(self, name: str, result=None, error: Exception | None = None):
        self.name = name
        self.result = result
        self.error = error

    async def extract_invoice(self, image_paths, file_name):
        if self.error:
            raise self.error
        return self.result, {"provider": self.name}


def test_local_paths_are_independent_of_working_directory():
    settings = Settings(
        database_url="sqlite+aiosqlite:///./data/test.db",
        storage_path="./data/test-uploads",
    )

    assert settings.database_url == (
        "sqlite+aiosqlite:///" + (API_ROOT / "data/test.db").as_posix()
    )
    assert settings.storage_path == str((API_ROOT / "data/test-uploads").resolve())


def test_live_mode_without_keys_does_not_silently_use_mock(monkeypatch):
    settings = SimpleNamespace(
        use_mock_extraction=False,
        gemini_api_key="",
        groq_api_key="",
        openrouter_api_key="",
    )
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="no LLM API keys"):
        factory.get_extraction_providers()


@pytest.mark.asyncio
async def test_mock_provider_requires_injected_fixture():
    provider = MockExtractionProvider()

    with pytest.raises(RuntimeError, match="Tests must inject"):
        await provider.extract_invoice([], "unrecognized-invoice.pdf")


@pytest.mark.asyncio
async def test_fallback_returns_first_success(monkeypatch):
    providers = [
        StubProvider("gemini", error=RuntimeError("model unavailable")),
        StubProvider("groq", result={"invoice_number": "INV-1"}),
    ]
    monkeypatch.setattr(factory, "get_extraction_providers", lambda: providers)

    extracted, metadata = await factory.extract_with_fallback([], "invoice.pdf")

    assert extracted == {"invoice_number": "INV-1"}
    assert metadata["provider"] == "groq"


@pytest.mark.asyncio
async def test_fallback_error_reports_every_provider(monkeypatch):
    providers = [
        StubProvider("gemini", error=RuntimeError("HTTP 404 model unavailable")),
        StubProvider("groq", error=RuntimeError("HTTP 429 rate limited")),
        StubProvider("openrouter", error=RuntimeError("HTTP 402 payment required")),
    ]
    monkeypatch.setattr(factory, "get_extraction_providers", lambda: providers)

    with pytest.raises(RuntimeError) as exc_info:
        await factory.extract_with_fallback([], "invoice.pdf")

    message = str(exc_info.value)
    assert "gemini: HTTP 404 model unavailable" in message
    assert "groq: HTTP 429 rate limited" in message
    assert "openrouter: HTTP 402 payment required" in message
