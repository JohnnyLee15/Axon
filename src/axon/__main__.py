import sys
import asyncio

from .commands.completion import build_command_options
from .commands.registry import COMMANDS
from .session.manager import SessionManager
from .config.paths import (
    ENV_PATH,
    SETTINGS_JSON_PATH,
    initialize_axon_home,
)
from .llm.factory import create_llm_adapter
from .llm.provider_setup import setup_provider_api_key
from .llm.providers import GEMINI_PROVIDER
from .web_search.factory import create_web_search_backend
from .ui.axon_ui import AxonUI
from .config.credential_store import CredentialStore
from .config.settings_store import SettingsStore


def main() -> None:
    initialize_axon_home()
    credentials = CredentialStore(env_path=ENV_PATH)
    settings = SettingsStore(settings_path=SETTINGS_JSON_PATH)
    ui = AxonUI(build_command_options(COMMANDS))

    try:
        api_key = setup_provider_api_key(
            provider=GEMINI_PROVIDER,
            ui=ui,
            credentials=credentials,
        )
    except (KeyboardInterrupt, EOFError):
        ui.info("Gemini setup canceled. Axon was not started.")
        sys.exit(130)

    if api_key is None:
        sys.exit(1)

    llm_adapter = create_llm_adapter(
        provider=GEMINI_PROVIDER,
        ui=ui,
        api_key=api_key,
    )
    web_search_backend = create_web_search_backend(
        provider=GEMINI_PROVIDER,
        api_key=api_key,
    )

    manager = SessionManager(
        ui=ui,
        llm_adapter=llm_adapter,
        web_search_backend=web_search_backend,
        settings=settings,
    )

    try:
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        ui.display_goodbye()
        sys.exit(130)
    except EOFError:
        ui.display_goodbye()


if __name__ == "__main__":
    main()
