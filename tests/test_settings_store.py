import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from axon.config.settings_store import (
    CHAT_LIMIT_KEY,
    CHAT_MODEL_KEY,
    SettingsStore,
)


class SettingsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self._settings_path = Path(self._temporary_directory.name) / "settings.json"

    def test_missing_settings_file_starts_with_empty_settings(self) -> None:
        settings = SettingsStore(self._settings_path)

        self.assertIsNone(settings.get(CHAT_MODEL_KEY))
        self.assertFalse(self._settings_path.exists())

    def test_settings_are_persisted_and_loaded_with_original_types(self) -> None:
        settings = SettingsStore(self._settings_path)

        settings.set(CHAT_MODEL_KEY, "model-a")
        settings.set(CHAT_LIMIT_KEY, 100_000)
        reloaded_settings = SettingsStore(self._settings_path)

        self.assertEqual(reloaded_settings.get(CHAT_MODEL_KEY), "model-a")
        self.assertEqual(reloaded_settings.get(CHAT_LIMIT_KEY), 100_000)
        self.assertTrue(self._settings_path.read_text(encoding="utf-8").endswith("\n"))

    def test_non_object_json_is_ignored(self) -> None:
        self._settings_path.write_text(
            json.dumps(["not", "settings"]),
            encoding="utf-8",
        )

        settings = SettingsStore(self._settings_path)

        self.assertIsNone(settings.get(CHAT_MODEL_KEY))


if __name__ == "__main__":
    unittest.main()
