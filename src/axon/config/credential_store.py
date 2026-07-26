import os
from pathlib import Path

from dotenv import dotenv_values


class CredentialStore:
    def __init__(self, env_path: Path) -> None:
        self._credentials = dotenv_values(env_path)


    def get(self, key: str) -> str | None:
        env_var = os.getenv(key)
        if env_var:
            return env_var

        stored_value = self._credentials.get(key)
        if not stored_value:
            return None

        return stored_value
