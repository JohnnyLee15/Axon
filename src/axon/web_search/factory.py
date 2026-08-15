from axon.llm.providers import GEMINI_PROVIDER

from .backend import WebSearchBackend
from .gemini_backend import GeminiWebSearchBackend


def create_web_search_backend(
    provider: str,
    api_key: str,
) -> WebSearchBackend:
    if provider == GEMINI_PROVIDER:
        return GeminiWebSearchBackend(api_key=api_key)

    raise ValueError(f"Unsupported web search provider: {provider}")
