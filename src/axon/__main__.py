from .session.manager import SessionManager


def main() -> None:
    manager = SessionManager()
    manager.run()


if __name__ == "__main__":
    main()
