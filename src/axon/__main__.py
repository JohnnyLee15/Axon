import sys

from axon.commands.completion import build_command_options
from axon.commands.registry import COMMANDS

from .session.manager import SessionManager
from .config.paths import (
    ENV_PATH,
    SETTINGS_JSON_PATH,
    initialize_axon_home,
)
from .llm.gemini_setup import setup_gemini
from .ui.axon_ui import AxonUI
from .config.credential_store import CredentialStore
from .config.settings_store import SettingsStore


def main() -> None:
    initialize_axon_home()
    credentials = CredentialStore(env_path=ENV_PATH)
    settings = SettingsStore(settings_path=SETTINGS_JSON_PATH)
    ui = AxonUI(build_command_options(COMMANDS))

    try:
        llm_adapter = setup_gemini(ui=ui, credentials=credentials)
    except (KeyboardInterrupt, EOFError):
        ui.info("Gemini setup canceled. Axon was not started.")
        sys.exit(130)

    if llm_adapter is None:
        sys.exit(1)

    manager = SessionManager(
        ui=ui,
        llm_adapter=llm_adapter,
        settings=settings,
    )

    try:
        manager.run()
    except KeyboardInterrupt:
        ui.display_goodbye()
        sys.exit(130)
    except EOFError:
        ui.display_goodbye()


if __name__ == "__main__":
    main()
