from pathlib import Path


DEFAULT_EXT = "text"


def resolve_filepath(path: str | Path) -> Path:
    if isinstance(path, str):
        path = path.strip()
        if not path:
            raise ValueError("File path cannot be empty.")

    return Path(path).expanduser().resolve()


def get_path_relative_to_current_dir(path: str | Path) -> Path | None:
    try:
        filepath = resolve_filepath(path)
    except (ValueError, TypeError):
        return None

    try:
        return filepath.relative_to(Path.cwd().resolve())
    except ValueError:
        return filepath


def get_file_ext(path: str) -> str:
    suffix = Path(path).suffix
    return suffix if suffix else DEFAULT_EXT
