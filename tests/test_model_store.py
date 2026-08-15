from pathlib import Path
from unittest.mock import patch

from axon.config.model_store import (
    ensure_model_downloaded,
    get_model_path,
    is_model_downloaded,
)


def test_ensure_model_downloaded_uses_axon_model_directory(tmp_path: Path) -> None:
    repo_id = "organization/example-model"
    model_path = tmp_path / "example-model"

    with (
        patch("axon.config.model_store.MODEL_CACHE_DIR", tmp_path),
        patch(
            "axon.config.model_store.snapshot_download",
            return_value=str(model_path),
        ) as download,
    ):
        result = ensure_model_downloaded(repo_id)

    assert result == model_path
    download.assert_called_once_with(
        repo_id=repo_id,
        local_dir=model_path,
    )


def test_get_model_path_uses_repository_name(tmp_path: Path) -> None:
    with patch("axon.config.model_store.MODEL_CACHE_DIR", tmp_path):
        result = get_model_path("organization/example-model")

    assert result == tmp_path / "example-model"


def test_is_model_downloaded_requires_nonempty_directory(tmp_path: Path) -> None:
    repo_id = "organization/example-model"
    model_path = tmp_path / "example-model"

    with patch("axon.config.model_store.MODEL_CACHE_DIR", tmp_path):
        assert not is_model_downloaded(repo_id)

        model_path.mkdir()
        assert not is_model_downloaded(repo_id)

        (model_path / "config.json").write_text("{}", encoding="utf-8")
        assert is_model_downloaded(repo_id)
