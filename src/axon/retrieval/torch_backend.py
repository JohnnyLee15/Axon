from pathlib import Path
from typing import Any

import torch
from transformers import AutoModel

from axon.utils.device import get_dtype

from .backend import RerankerBackend


class TorchRerankerBackend(RerankerBackend):
    def __init__(self, device: torch.device, model_path: Path) -> None:
        self._model = AutoModel.from_pretrained(
            model_path,
            dtype=get_dtype(),
            trust_remote_code=True
        )

        self._model.to(device)
        self._model.eval()


    def rerank(self, *, query: str, documents: list[str]) -> list[dict[str, Any]]:
        return self._model.rerank(query=query, documents=documents)
