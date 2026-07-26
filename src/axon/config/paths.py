import os
from pathlib import Path


DEFAULT_AXON_HOME = Path.home() / "Axon"
AXON_HOME = Path(os.getenv("AXON_HOME", str(DEFAULT_AXON_HOME))).expanduser().resolve()
DATA_DIR = AXON_HOME / "data"
MODEL_CACHE_DIR = AXON_HOME / "models"
ENV_PATH = AXON_HOME / ".env"


def initialize_axon_home() -> None:
    AXON_HOME.mkdir(parents=True, exist_ok=True, mode=0o700)
    DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    ENV_PATH.touch(exist_ok=True, mode=0o600)
