import sys
import os
import importlib
from typing import Any

from huggingface_hub import snapshot_download

from .backend import RerankerBackend


MLX_RERANKER_MODEL = "jinaai/jina-reranker-v3-mlx"


class MLXRerankerBackend(RerankerBackend):
    def __init__(self) -> None:
        model_path = snapshot_download(MLX_RERANKER_MODEL)

        if model_path not in sys.path:
            sys.path.append(model_path)

        abs_proj_path = os.path.join(model_path, "projector.safetensors")

        backend_class = importlib.import_module("rerank").MLXReranker
        self._model = backend_class(
            model_path=model_path,
            projector_path=abs_proj_path
        )


    def rerank(self, *, query: str, documents: list[str]) -> list[dict[str, Any]]:
        return self._model.rerank(query=query, documents=documents)
