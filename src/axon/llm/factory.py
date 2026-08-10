from axon.ui.axon_ui import AxonUI

from .llm_adapter import LLMAdapter
from .gemini_adapter import GeminiAdapter
from .providers import GEMINI_PROVIDER


def create_llm_adapter(
    provider: str,
    ui: AxonUI,
    api_key: str,
) -> LLMAdapter:
    if provider == GEMINI_PROVIDER:
        return GeminiAdapter(ui=ui, api_key=api_key)

    raise ValueError(f"Unsupported LLM provider: {provider}")
