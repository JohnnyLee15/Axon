from src.utils.config import *
from src.ingestion.semantic_chunker import SemanticChunker
from src.db.vector_database import VectorDatabase
from src.retrieval.reranker import Reranker


class AgentTools:
    def __init__(
        self,
        chunker: SemanticChunker,
        db: VectorDatabase,
        reranker: Reranker
    ):
        self._chunker = chunker
        self._db = db
        self._reranker = reranker


    def _format_chunks(self, chunks: dict[int, dict[str, str | int]]) -> str | None:
        if not chunks:
            return None

        sorted_chunks = sorted(
            chunks.values(), key=lambda x: (x["paper_id"], x["chunk_index"])
        )

        curr_paper_id = None
        parts = []

        for chunk_data in sorted_chunks:
            paper_id = chunk_data["paper_id"]
            chunk_index = chunk_data["chunk_index"]
            markdown = chunk_data["text"]

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


    def search_for_chunks(
        self,
        query: str
    ) -> dict:
        embedding = self._chunker.embed_query(query)
        chunks = self._db.top_chunk_matches(query, embedding)
        best_chunks = self._reranker.rank_chunks(query, chunks)
        formatted_chunks = self._format_chunks(best_chunks)
        return {
            "content": formatted_chunks,
            "chunk_count": len(best_chunks),
            "doc_count": len(set(c["paper_id"] for c in best_chunks.values())),
            "raw_chunks": best_chunks
        }
