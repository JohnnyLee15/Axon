from typing import Any

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModel

from .backend import RerankerBackend
from src.utils.device_utils import get_dtype


TORCH_RERANKER_MODEL = "jinaai/jina-reranker-v3"


class TorchRerankerBackend(RerankerBackend):
    def __init__(self, device: torch.device) -> None:
        model_path = snapshot_download(TORCH_RERANKER_MODEL)

        self._model = AutoModel.from_pretrained(
            model_path,
            dtype=get_dtype(),
            trust_remote_code=True
        )

        self._model.to(device)
        self._model.eval()


    def rerank(self, *, query: str, documents: list[str]) -> list[dict[str, Any]]:
        return self._model.rerank(query=query, documents=documents)
