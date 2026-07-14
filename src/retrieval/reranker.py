from .backend import RerankerBackend


RERANK_BATCH_SIZE = 10
FINAL_CHUNK_K = 5
MIN_RERANK_SCORE = 0.20


class Reranker:
    def __init__(self, backend: RerankerBackend) -> None:
        self._backend = backend

    def rank_chunks(
        self,
        query: str,
        chunks: dict[int, dict[str, str | int]]
    ) -> dict[int, dict[str, str | int]]:
        if not chunks:
            return {}

        cids = [cid for cid in chunks]
        docs = [chunks[cid]["text"] for cid in chunks]

        scored = []
        for i in range(0, len(docs), RERANK_BATCH_SIZE):
            end_idx = i + RERANK_BATCH_SIZE
            doc_batch = docs[i : end_idx]
            cid_batch = cids[i: end_idx]

            results = self._backend.rerank(query=query, documents=doc_batch)
            for result in results:
                cid = cid_batch[result["index"]]
                score = result["relevance_score"]

                if score >= MIN_RERANK_SCORE:
                    scored.append((cid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_cids = [cid for cid, _ in scored[:FINAL_CHUNK_K]]
        return {cid: chunks[cid] for cid in top_cids}