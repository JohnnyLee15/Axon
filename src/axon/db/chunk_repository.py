import re
import sqlite_vec

from axon.ingestion.models import Chunk

from .sqlite_database import SQLiteDatabase
from .schema_manager import VEC_TABLE, CHUNK_TABLE, FTS_TABLE
from .contracts import CHUNK_FIELDS


INITIAL_CHUNK_K = 20


class ChunkRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database


    def insert_chunks(self, chunks: dict[int, Chunk], paper_id: int) -> None:
        insert_chunk = f"""
            INSERT INTO {CHUNK_TABLE} (
                paper_id,
                chunk_index,
                markdown
            )
            VALUES (?, ?, ?);
        """
        insert_vec = f"""
            INSERT INTO {VEC_TABLE} (
                id,
                embedding
            )
            VALUES (?, ?);
        """

        with self._database.connect() as connection:
            for chunk_index, chunk in chunks.items():
                if chunk.embedding is None:
                    raise ValueError(
                        f"Chunk {chunk_index} cannot be inserted without an embedding."
                    )

                chunk_params = (
                    paper_id,
                    chunk_index,
                    chunk.markdown,
                )
                chunk_id = connection.execute(insert_chunk, chunk_params).lastrowid

                connection.execute(
                    insert_vec,
                    (chunk_id, sqlite_vec.serialize_float32(chunk.embedding)),
                )



    def _get_vector_matches(self, query_embedding: list[float]) -> list[tuple]:
        sql = f"""
            SELECT
                c.id,
                c.paper_id,
                c.chunk_index,
                c.markdown
            FROM {VEC_TABLE} v
            JOIN {CHUNK_TABLE} c
                ON c.id = v.id
            WHERE v.embedding MATCH ?
                AND k = {INITIAL_CHUNK_K}
        """

        with self._database.connect() as connection:
            rows = connection.execute(
                sql,
                (sqlite_vec.serialize_float32(query_embedding),)
            ).fetchall()

        return rows


    def _get_bm25_matches(self, query: str) -> list[tuple]:
        tokens = query.split()
        if not tokens:
            return []

        fts_query = " OR ".join(
            f'"{tok.replace(chr(34), chr(34)*2)}"'
            for tok in tokens
        )

        sql = f"""
            SELECT
                c.id,
                c.paper_id,
                c.chunk_index,
                c.markdown
            FROM {FTS_TABLE}
            JOIN {CHUNK_TABLE} c
                ON {FTS_TABLE}.rowid = c.id
            WHERE {FTS_TABLE} MATCH ?
            ORDER BY bm25({FTS_TABLE})
            LIMIT {INITIAL_CHUNK_K}
        """

        with self._database.connect() as connection:
            rows = connection.execute(sql, (fts_query,)).fetchall()

        return rows


    def get_top_matches(
        self,
        query: str,
        query_embedding: list[float]
    ) -> dict[int, dict[str, str | int]]:
        bm25_chunks = self._get_bm25_matches(query)
        vector_chunks = self._get_vector_matches(query_embedding)

        if not bm25_chunks and not vector_chunks:
            return {}

        chunks = {}
        for cid, pid, cidx, text in bm25_chunks:
            chunks[cid] = {
                CHUNK_FIELDS.PAPER_ID: pid,
                CHUNK_FIELDS.CHUNK_INDEX: cidx,
                CHUNK_FIELDS.TEXT: text,
            }

        for cid, pid, cidx, text in vector_chunks:
            chunks[cid] = {
                CHUNK_FIELDS.PAPER_ID: pid,
                CHUNK_FIELDS.CHUNK_INDEX: cidx,
                CHUNK_FIELDS.TEXT: text,
            }

        return chunks
