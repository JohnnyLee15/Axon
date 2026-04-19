from device_utils import get_torch_device
from config import *
from typing import Any

class Reranker:
    def __init__(self) -> None:
        self._reranker = None
        self._init()


    def _init(self) -> None:
        raise ValueError("Implement this method in subclass. This is an abstract method.")


    def _set_reranker(self, reranker: Any) -> None:
        self._reranker = reranker


    def _get_reranker(self) -> Any:
        if self._reranker is None:
            raise ValueError("Reranker has not been initialized.")
        return self._reranker


    def rank_chunks(
        self,
        query: str,
        chunks: dict[int, dict[str, str | int]]
    ) -> dict[int, dict[str, str | int]] | None:
        if not chunks:
            return None

        cids = [cid for cid in chunks]
        docs = [chunks[cid]["text"] for cid in chunks]

        scored = []
        for i in range(0, len(docs), RERANK_BATCH_SIZE):
            end_idx = i + RERANK_BATCH_SIZE
            doc_batch = docs[i : end_idx]
            cid_batch = cids[i: end_idx]

            results = self._reranker.rerank(query=query, documents=doc_batch)
            for result in results:
                cid = cid_batch[result["index"]]
                score = result["relevance_score"]

                if score >= MIN_RERANK_SCORE:
                    scored.append((cid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_cids = [cid for cid, _ in scored[:FINAL_CHUNK_K]]
        return {cid: chunks[cid] for cid in top_cids}