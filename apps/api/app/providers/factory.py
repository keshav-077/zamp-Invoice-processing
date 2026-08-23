import logging

from app.config import get_settings
from app.providers.base import ExtractionProvider
from app.providers.mock import MockExtractionProvider
from app.providers.vlm import GeminiProvider, GroqProvider, OpenRouterProvider

logger = logging.getLogger(__name__)


class ExtractionProvidersError(RuntimeError):
    """Raised when live extraction is unavailable or every provider fails."""


def get_extraction_providers() -> list[ExtractionProvider]:
    settings = get_settings()
    if settings.use_mock_extraction:
        return [MockExtractionProvider()]
    providers: list[ExtractionProvider] = []
    if settings.gemini_api_key:
        providers.append(GeminiProvider())
    if settings.groq_api_key:
        providers.append(GroqProvider())
    if settings.openrouter_api_key:
        providers.append(OpenRouterProvider())
    if not providers:
        raise RuntimeError(
            "Live extraction is enabled, but no LLM API keys are configured. "
            "Set at least one provider key or explicitly set USE_MOCK_EXTRACTION=true."
        )
    return providers


async def extract_with_fallback(image_paths: list[str], file_name: str) -> tuple:
    try:
        providers = get_extraction_providers()
    except RuntimeError as exc:
        raise ExtractionProvidersError(str(exc)) from exc
    failures: list[str] = []
    for provider in providers:
        try:
            logger.info("Extracting invoice via provider=%s file=%s", provider.name, file_name)
            extracted, meta = await provider.extract_invoice(image_paths, file_name)
            logger.info("Extraction succeeded via provider=%s", meta.get("provider", provider.name))
            return extracted, meta
        except Exception as e:
            logger.warning("Provider %s failed: %s", provider.name, e)
            failures.append(f"{provider.name}: {e}")
    raise ExtractionProvidersError(
        "All extraction providers failed. " + " | ".join(failures)
    )
