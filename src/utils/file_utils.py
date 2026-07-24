from pathlib import Path
from .paths import ROOT_DIR

DEFAULT_EXT = "text"


def resolve_filepath(path: str) -> Path:
    path = path.strip()
    if not path:
        raise ValueError("File path cannot be empty.")

    return Path(path).expanduser().resolve()


def get_path_relative_to_project_root(path: str | Path) -> Path | None:

    try:
        filepath = path if isinstance(path, Path) else resolve_filepath(path)
        return filepath.relative_to(ROOT_DIR)
    except ValueError:
        return None
    except Exception:
        return filepath


def get_file_ext(path: str) -> str:
    suffix = Path(path).suffix
    return suffix if suffix else DEFAULT_EXT
