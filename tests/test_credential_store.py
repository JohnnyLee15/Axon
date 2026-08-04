import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from axon.config.credential_store import CredentialStore


TEST_API_KEY_ENV_VAR = "AXON_TEST_API_KEY"


class CredentialStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)

        self._env_path = Path(self._temp_dir.name) / ".env"
        self._env_path.touch()

    def test_get_returns_environment_value_before_stored_value(self) -> None:
        self._env_path.write_text(
            f"{TEST_API_KEY_ENV_VAR}=stored-key\n",
            encoding="utf-8",
        )
        store = CredentialStore(self._env_path)

        with patch.dict(
            os.environ,
            {TEST_API_KEY_ENV_VAR: "environment-key"},
        ):
            value = store.get(TEST_API_KEY_ENV_VAR)

        self.assertEqual(value, "environment-key")

    def test_get_returns_none_when_credential_is_missing(self) -> None:
        store = CredentialStore(self._env_path)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(TEST_API_KEY_ENV_VAR, None)
            value = store.get(TEST_API_KEY_ENV_VAR)

        self.assertIsNone(value)

    def test_set_persists_and_immediately_exposes_credential(self) -> None:
        store = CredentialStore(self._env_path)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(TEST_API_KEY_ENV_VAR, None)
            store.set(TEST_API_KEY_ENV_VAR, "new-key")
            value = store.get(TEST_API_KEY_ENV_VAR)

        self.assertEqual(value, "new-key")
        self.assertEqual(
            dotenv_values(self._env_path)[TEST_API_KEY_ENV_VAR],
            "new-key",
        )


if __name__ == "__main__":
    unittest.main()
