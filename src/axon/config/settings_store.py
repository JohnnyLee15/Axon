import json
from pathlib import Path
from typing import Any



CHAT_MODEL_KEY = "chat_model"
CHAT_LIMIT_KEY = "chat_limit"


class SettingsStore:
    def __init__(self, settings_path: Path) -> None:
        self._settings_path = settings_path
        self._settings = self._load()


    def _load(self) -> dict[str, Any]:
        if not self._settings_path.exists():
            return {}

        content = self._settings_path.read_text(encoding="utf-8").strip()
        if not content:
            return {}

        settings = json.loads(content)
        return settings if isinstance(settings, dict) else {}


    def get(self, key: str) -> Any | None:
        return self._settings.get(key)


    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        content = json.dumps(self._settings, indent=2)
        self._settings_path.write_text(
            f"{content}\n",
            encoding="utf-8",
        )
