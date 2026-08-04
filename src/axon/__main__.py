import sys

from .session.manager import SessionManager
from .config.paths import initialize_axon_home, ENV_PATH
from .llm.gemini_setup import setup_gemini
from .ui.axon_ui import AxonUI
from .config.credential_store import CredentialStore


def main() -> None:
    initialize_axon_home()
    credentials = CredentialStore(env_path=ENV_PATH)
    ui = AxonUI()

    try:
        llm_adapter = setup_gemini(ui=ui, credentials=credentials)
    except (KeyboardInterrupt, EOFError):
        ui.info("Gemini setup canceled. Axon was not started.")
        sys.exit(130)

    if llm_adapter is None:
        sys.exit(1)

    manager = SessionManager(ui=ui, llm_adapter=llm_adapter)
    manager.run()


if __name__ == "__main__":
    main()
