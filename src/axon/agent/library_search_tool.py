from axon.ingestion.embedding_backend import EmbeddingBackend
from axon.db.chunk_repository import ChunkRepository
from axon.retrieval.reranker import Reranker
from axon.db.contracts import CHUNK_FIELDS

from .tool_contracts import TOOL_RESULTS


class LibrarySearchTool:
    def __init__(
        self,
        embedding_backend: EmbeddingBackend,
        chunk_repository: ChunkRepository,
        reranker: Reranker,
    ) -> None:
        self._embedding_backend = embedding_backend
        self._chunk_repository = chunk_repository
        self._reranker = reranker


    def _format_chunks(self, chunks: dict[int, dict[str, str | int]]) -> str | None:
        if not chunks:
            return None

        sorted_chunks = sorted(
            chunks.values(), key=lambda x: (x[CHUNK_FIELDS.PAPER_ID], x[CHUNK_FIELDS.CHUNK_INDEX])
        )

        curr_paper_id = None
        parts = []

        for chunk_data in sorted_chunks:
            paper_id = chunk_data[CHUNK_FIELDS.PAPER_ID]
            chunk_index = chunk_data[CHUNK_FIELDS.CHUNK_INDEX]
            markdown = chunk_data[CHUNK_FIELDS.TEXT]

            if paper_id != curr_paper_id:
                if curr_paper_id is not None:
                    parts.append("</document>")
                curr_paper_id = paper_id
                parts.append(f"<document id='{paper_id}'>")

            parts.append(f"<chunk id='{chunk_index}'>")
            parts.append(markdown)
            parts.append("</chunk>")

        parts.append("</document>")
        return "\n".join(parts)


    def search_library(
        self,
        query: str
    ) -> dict:
        embedding = self._embedding_backend.embed_query(query)
        chunks = self._chunk_repository.get_top_matches(query, embedding)
        best_chunks = self._reranker.rank_chunks(query, chunks)
        formatted_chunks = self._format_chunks(best_chunks)
        return {
            TOOL_RESULTS.CONTENT: formatted_chunks,
            TOOL_RESULTS.CHUNK_COUNT: len(best_chunks),
            TOOL_RESULTS.DOC_COUNT: len(set(c[CHUNK_FIELDS.PAPER_ID] for c in best_chunks.values())),
            TOOL_RESULTS.RAW_CHUNKS: best_chunks
        }