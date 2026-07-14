from rich.console import Console

from src.llm.llm_adapter import LLMAdapter
from src.llm.gemini_adapter import GeminiAdapter

from .models import MODEL_TO_PROVIDER, GEMINI_PROVIDER


def create_llm_adapter(model: str, console: Console) -> LLMAdapter:
    provider = MODEL_TO_PROVIDER.get(model)
    if provider is None:
        raise ValueError(f"No provider registered for model: {model}")

    if provider == GEMINI_PROVIDER:
        return GeminiAdapter(console)

    raise ValueError(f"Unsupported LLM provider: {provider}")