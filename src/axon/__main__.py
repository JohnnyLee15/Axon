from .session.manager import SessionManager
from .config.paths import initialize_axon_home


def main() -> None:
    initialize_axon_home()
    manager = SessionManager()
    manager.run()


if __name__ == "__main__":
    main()
