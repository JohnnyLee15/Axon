from axon.config.credential_store import CredentialStore
from axon.ui.axon_ui import AxonUI
from axon.llm.errors import InvalidCredentialsError

from .llm_adapter import LLMAdapter
from .factory import create_llm_adapter
from .providers import (
    PROVIDER_TO_API_KEY_ENV_VAR,
    GEMINI_PROVIDER,
)


def setup_gemini(
    ui: AxonUI,
    credentials: CredentialStore,
) -> LLMAdapter | None:
    api_key_env_var = PROVIDER_TO_API_KEY_ENV_VAR[GEMINI_PROVIDER]
    api_key = credentials.get(api_key_env_var)

    should_save = False
    while True:
        if api_key is None:
            api_key = ui.request_secret("Enter your Gemini API Key").strip()
            should_save = True

        adapter = create_llm_adapter(
            provider=GEMINI_PROVIDER,
            ui=ui,
            api_key=api_key,
        )

        try:
            adapter.validate_credentials()
        except InvalidCredentialsError:
            ui.error("The API key is invalid.")
            api_key = None
            continue
        except Exception as e:
            ui.error(f"Could not validate Gemini credentials: {e}.")
            return None

        if should_save:
            credentials.set(key=api_key_env_var, value=api_key)
        return adapter
