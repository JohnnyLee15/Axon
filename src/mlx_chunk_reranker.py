import sys
import os
from huggingface_hub import snapshot_download
from rich.console import Console
import importlib
from config import *

class MLXChunkReranker:
    def __init__(self, console: Console) -> None:
        self._console = console
        self._reranker = None
        self._init_mlx()


    def _init_mlx(self) -> None:
        model_path = snapshot_download(MLX_RERANKER)
        if model_path not in sys.path:
            sys.path.append(model_path)
        abs_proj_path = os.path.join(model_path, "projector.safetensors")

        mlx_reranker_class = importlib.import_module("rerank").MLXReranker
        self._reranker = mlx_reranker_class(
            model_path=model_path,
            projector_path=abs_proj_path
        )


    def rank_chunks(
        self,
        query: str,
        chunks: dict[int, dict[str, str | int]]
    ) -> dict[int, dict[str, str | int]]:
        cids = [cid for cid in chunks]
        docs = [chunks[cid]["text"] for cid in chunks]

        scored= []
        for i in range(0, len(docs), RERANK_BATCH_SIZE):
            end_idx = i + RERANK_BATCH_SIZE
            doc_batch = docs[i : end_idx]
            cid_batch = cids[i: end_idx]

            results = self._reranker.rerank(query=query, documents=doc_batch)


            for result in results:
                cid = cid_batch[result["index"]]
                scored.append((cid, result["relevance_score"]))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_cids = [cid for cid, _ in scored[:FINAL_CHUNK_K]]
        return {cid: chunks[cid] for cid in top_cids}
