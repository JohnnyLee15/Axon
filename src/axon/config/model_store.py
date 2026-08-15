from pathlib import Path

from huggingface_hub import snapshot_download

from .paths import MODEL_CACHE_DIR


def get_model_path(repo_id: str) -> Path:
    model_name = repo_id.rsplit("/", maxsplit=1)[-1]
    return MODEL_CACHE_DIR / model_name


def is_model_downloaded(repo_id: str) -> bool:
    model_path = get_model_path(repo_id)
    return model_path.is_dir() and any(model_path.iterdir())


def ensure_model_downloaded(repo_id: str) -> Path:
    model_path = get_model_path(repo_id)

    return Path(
        snapshot_download(
            repo_id=repo_id,
            local_dir=model_path,
        )
    )
