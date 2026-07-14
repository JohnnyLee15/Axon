from pathlib import Path
from src.utils.config import *

DEFAULT_EXT = "text"

def get_path_relative_to_project_root(path: str | Path) -> Path | None:
    filepath = path
    if not isinstance(path, Path):
        try:
            filepath = Path(path.strip()).expanduser().resolve()
        except Exception:
            return None

    try:
        display_path = filepath.relative_to(ROOT_DIR)
        return display_path
    except Exception:
        return filepath


def get_file_ext(path: str) -> str:
    suffix = Path(path).suffix
    return suffix if suffix else DEFAULT_EXT

