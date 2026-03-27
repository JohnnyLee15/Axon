import sqlite3
import sqlite_vec
from config import *
from chunk_tracker import Chunk

class VectorDatabase:
    def __init__(self) -> None:
        self._init_db()


    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn


    def _init_db(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        create_chunks_table = f"""
            CREATE TABLE IF NOT EXISTS {CHUNK_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL CHECK (paper_id > 0) REFERENCES {PAPER_TABLE}(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
                markdown TEXT NOT NULL
            )
        """
        create_vec_table = f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {VEC_TABLE} USING vec0 (
                id INTEGER PRIMARY KEY,
                embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine
            )
        """
        create_paper_table = f"""
            CREATE TABLE IF NOT EXISTS {PAPER_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        """

        try:
            cursor.execute(create_paper_table)
            cursor.execute(create_chunks_table)
            cursor.execute(create_vec_table)
            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error creating database tables: {e}")

        finally:
            cursor.close()
            conn.close()


    def drop_all(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        drop_papers = f"DROP TABLE IF EXISTS {PAPER_TABLE}"
        drop_chunks = f"DROP TABLE IF EXISTS {CHUNK_TABLE}"
        drop_vec = f"DROP TABLE IF EXISTS {VEC_TABLE}"

        try:
            cursor.execute(drop_vec)
            cursor.execute(drop_chunks)
            cursor.execute(drop_papers)
            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error dropping tables during reset: {e}")

        finally:
            cursor.close()
            conn.close()


    def reset_db(self) -> None:
        self.drop_all()
        self._init_db()


    def create_paper(self) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = f"INSERT INTO {PAPER_TABLE} DEFAULT VALUES"

        try:
            cursor.execute(sql)
            paper_id = cursor.lastrowid
            conn.commit()
            return paper_id

        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error creating new paper: {e}")
            return -1

        finally:
            cursor.close()
            conn.close()

    def insert_paper_chunks(self, chunks: dict[int, Chunk], paper_id: int) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        insert_chunk = f"""
            INSERT INTO {CHUNK_TABLE} (
                paper_id,
                chunk_index,
                markdown
            )
            VALUES (?, ?, ?)
        """
        insert_vec = f"""
            INSERT INTO {VEC_TABLE} (
                id,
                embedding
            )
            VALUES (?, ?)
        """
        try:
            for chunk_index in chunks:
                chunk = chunks[chunk_index]
                chunk_params = (
                    paper_id,
                    chunk_index,
                    chunk.markdown
                )
                cursor.execute(insert_chunk, chunk_params)

                chunk_id = cursor.lastrowid
                cursor.execute(
                    insert_vec,
                    (chunk_id, sqlite_vec.serialize_float32(chunk.embedding))
                )
            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error inserting chunk into database: {e}")

        finally:
            cursor.close()
            conn.close()


    def _get_top_k_chunks(self, query_embedding: list[float]) -> list[tuple]:
        conn = self._get_connection()
        cursor = conn.cursor()
        rows = []
        sql = f"""
            SELECT
                c.paper_id,
                c.chunk_index,
                c.markdown,
                v.distance
            FROM {VEC_TABLE} v
            JOIN {CHUNK_TABLE} c
                ON c.id = v.id
            WHERE v.embedding MATCH ?
                AND k = {CHUNKS_MATCHED}
                AND v.distance <= {MAX_COS_DIST}
            ORDER BY c.paper_id, c.chunk_index
        """

        try:
            cursor.execute(
                sql,
                (sqlite_vec.serialize_float32(query_embedding),)
            )
            rows = cursor.fetchall()

        except sqlite3.Error as e:
            print(f"Error retrieving top {CHUNKS_MATCHED} chunks: {e}")

        finally:
            cursor.close()
            conn.close()

        return rows


    def get_formatted_chunks(self, query_embedding: list[float]) -> str | None:
        rows = self._get_top_k_chunks(query_embedding)
        if not rows:
            return None

        curr_paper_id = None
        parts = []
        for row in rows:
            paper_id, chunk_index, markdown, _ = row
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





