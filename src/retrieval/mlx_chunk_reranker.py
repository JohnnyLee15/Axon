import sys
import os
from huggingface_hub import snapshot_download
import importlib

from src.utils.config import *
from src.retrieval.reranker import Reranker

class MLXChunkReranker(Reranker):
    def _init(self) -> None:
        model_path = snapshot_download(MLX_RERANKER)
        if model_path not in sys.path:
            sys.path.append(model_path)
        abs_proj_path = os.path.join(model_path, "projector.safetensors")

        mlx_reranker_class = importlib.import_module("rerank").MLXReranker
        self._reranker = mlx_reranker_class(
            model_path=model_path,
            projector_path=abs_proj_path
        )
