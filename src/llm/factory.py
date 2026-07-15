from src.ui.axon_ui import AxonUI

from .llm_adapter import LLMAdapter
from .gemini_adapter import GeminiAdapter
from .models import MODEL_TO_PROVIDER, GEMINI_PROVIDER


def create_llm_adapter(model: str, ui: AxonUI) -> LLMAdapter:
    provider = MODEL_TO_PROVIDER.get(model)
    if provider is None:
        raise ValueError(f"No provider registered for model: {model}")

    if provider == GEMINI_PROVIDER:
        return GeminiAdapter(ui)

    raise ValueError(f"Unsupported LLM provider: {provider}")