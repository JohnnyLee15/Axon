from src.utils.device import get_torch_device

from .mlx_backend import MLXRerankerBackend
from .torch_backend import TorchRerankerBackend
from .reranker import Reranker


def create_reranker() -> Reranker:
    device = get_torch_device()

    if device.type == "mps":
        backend = MLXRerankerBackend()
    else:
        backend = TorchRerankerBackend(device=device)

    return Reranker(backend)
