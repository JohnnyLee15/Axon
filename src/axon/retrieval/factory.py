from axon.config.model_store import ensure_model_downloaded, is_model_downloaded
from axon.ui.axon_ui import AxonUI
from axon.utils.device import get_torch_device

from .mlx_backend import MLXRerankerBackend
from .torch_backend import TorchRerankerBackend
from .reranker import Reranker


MLX_RERANKER_MODEL = "jinaai/jina-reranker-v3-mlx"
TORCH_RERANKER_MODEL = "jinaai/jina-reranker-v3"


def create_reranker(ui: AxonUI) -> Reranker:
    device = get_torch_device()

    if device.type == "mps":
        repo_id = MLX_RERANKER_MODEL
    else:
        repo_id = TORCH_RERANKER_MODEL

    model_downloaded = is_model_downloaded(repo_id)
    action = "Loading" if model_downloaded else "Downloading"

    with ui.wait(label=f'{action} model "{repo_id}"'):
        model_path = ensure_model_downloaded(repo_id)

        if device.type == "mps":
            backend = MLXRerankerBackend(model_path=model_path)
        else:
            backend = TorchRerankerBackend(device=device, model_path=model_path)

    if not model_downloaded:
        ui.success(
            f'Model "{repo_id}" downloaded successfully.',
            leading_blank=False,
        )

    return Reranker(backend)
