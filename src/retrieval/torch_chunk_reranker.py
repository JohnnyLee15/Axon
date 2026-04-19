from huggingface_hub import snapshot_download
from transformers import AutoModel

from src.retrieval.reranker import Reranker
from src.utils.config import *
from src.utils.device_utils import get_dtype, get_torch_device


class TorchChunkReranker(Reranker):
    def _init(self) -> None:
        device = get_torch_device()
        model_path = snapshot_download(PYTORCH_RERANKER)
        self._set_reranker(AutoModel.from_pretrained(
            model_path,
            dtype=get_dtype(),
            trust_remote_code=True
        ))
        self._get_reranker().to(device)
        self._get_reranker().eval()