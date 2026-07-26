from axon.config.credential_store import CredentialStore
from axon.ui.axon_ui import AxonUI

from .llm_adapter import LLMAdapter
from .gemini_adapter import GeminiAdapter
from .models import MODEL_TO_PROVIDER, GEMINI_PROVIDER


PROVIDER_TO_API_KEY_ENV_VAR = {
    GEMINI_PROVIDER: "GEMINI_API_KEY",
}


def _get_provider_api_key(provider: str, credentials: CredentialStore) -> str:
    env_var = PROVIDER_TO_API_KEY_ENV_VAR.get(provider)
    if env_var is None:
        raise ValueError(
            f"No API-key environment variable registered for provider \"{provider}\"."
        )

    api_key = credentials.get(env_var)
    if api_key is None:
        raise ValueError(f"API key for provider \"{provider}\" is not configured.")

    return api_key


def create_llm_adapter(
    model: str,
    ui: AxonUI,
    credentials: CredentialStore,
) -> LLMAdapter:
    provider = MODEL_TO_PROVIDER.get(model)
    if provider is None:
        raise ValueError(f"No provider registered for model: {model}")

    api_key = _get_provider_api_key(provider, credentials)

    if provider == GEMINI_PROVIDER:
        return GeminiAdapter(ui=ui, api_key=api_key)

    raise ValueError(f"Unsupported LLM provider: {provider}")
