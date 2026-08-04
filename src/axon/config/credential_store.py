import os
from pathlib import Path

from dotenv import dotenv_values, set_key


class CredentialStore:
    def __init__(self, env_path: Path) -> None:
        self._env_path = env_path
        self._credentials = dotenv_values(env_path)


    def get(self, key: str) -> str | None:
        env_var = os.getenv(key)
        if env_var:
            return env_var

        stored_value = self._credentials.get(key)
        if not stored_value:
            return None

        return stored_value


    def set(self, key: str, value: str) -> None:
        set_key(
            dotenv_path=self._env_path,
            key_to_set=key,
            value_to_set=value,
            quote_mode="never",
        )
        self._credentials[key] = value
