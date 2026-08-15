import importlib
import sys
from pathlib import Path
from typing import Any

from .backend import RerankerBackend


class MLXRerankerBackend(RerankerBackend):
    def __init__(self, model_path: Path) -> None:
        model_path_str = str(model_path)

        if model_path_str not in sys.path:
            sys.path.append(model_path_str)

        projector_path = model_path / "projector.safetensors"

        backend_class = importlib.import_module("rerank").MLXReranker
        self._model = backend_class(
            model_path=model_path_str,
            projector_path=str(projector_path),
        )


    def rerank(self, *, query: str, documents: list[str]) -> list[dict[str, Any]]:
        return self._model.rerank(query=query, documents=documents)
