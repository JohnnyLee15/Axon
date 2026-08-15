from axon.config.credential_store import CredentialStore
from axon.ui.axon_ui import AxonUI

from .errors import InvalidCredentialsError
from .factory import create_llm_adapter
from .providers import PROVIDER_TO_API_KEY_ENV_VAR


def setup_provider_api_key(
    provider: str,
    ui: AxonUI,
    credentials: CredentialStore,
) -> str | None:
    api_key_env_var = PROVIDER_TO_API_KEY_ENV_VAR.get(provider)
    if api_key_env_var is None:
        raise ValueError(f"Unsupported provider: {provider}")

    api_key = credentials.get(api_key_env_var)
    provider_name = provider.capitalize()
    should_save = False

    while True:
        if api_key is None:
            api_key = ui.request_secret(f"Enter your {provider_name} API Key").strip()
            should_save = True

        validation_adapter = create_llm_adapter(
            provider=provider,
            ui=ui,
            api_key=api_key,
        )

        try:
            validation_adapter.validate_credentials()
        except InvalidCredentialsError:
            ui.error(f"The {provider_name} API key is invalid.")
            api_key = None
            continue
        except Exception as e:
            ui.error(
                f"Could not validate {provider_name} credentials: {e}."
            )
            return None

        if should_save:
            credentials.set(
                key=api_key_env_var,
                value=api_key,
            )

        return api_key
