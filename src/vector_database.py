import sqlite3
import sqlite_vec
from config import *
from chunk_tracker import Chunk
import json
from rich.console import Console

class VectorDatabase:
    def __init__(self) -> None:
        self._console = Console()
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
        create_chats_table = f"""
            CREATE TABLE IF NOT EXISTS {CHAT_TABLE} (
                name TEXT PRIMARY KEY,
                chat_content TEXT
            )
        """

        try:
            cursor.execute(create_paper_table)
            cursor.execute(create_chunks_table)
            cursor.execute(create_vec_table)
            cursor.execute(create_chats_table)
            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            self._console.print(f"\n🏗️ [bold red]Error creating database tables: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()


    def clear(self) -> None:
        #TODO: Figure our what clear means, do we also clear chats?
        # Best is probably db clear papers and db remove chat --all
        conn = self._get_connection()
        cursor = conn.cursor()
        clear_vec = f"DELETE FROM {VEC_TABLE}"
        clear_chunks = f"DELETE FROM {CHUNK_TABLE}"
        clear_papers = f"DELETE FROM {PAPER_TABLE}"

        try:
            cursor.execute(clear_vec)
            cursor.execute(clear_chunks)
            cursor.execute(clear_papers)
            conn.commit()

            cursor.execute("VACUUM")

        except sqlite3.Error as e:
            conn.rollback()
            self._console.print(f"\n🧹 [bold red]Error dropping tables during database clear: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()


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
            self._console.print(f"\n📄 [bold red]Error creating new paper: {e}[/bold red]")
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
            self._console.print(f"\n🧩 [bold red]Error inserting chunk into database: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()


    def insert_chat(
        self,
        name: str,
        contents: list[dict[str, str]],
        overwrite: bool = False
    ) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        if overwrite:
            prefix = "INSERT OR REPLACE"
        else:
            prefix = "INSERT"

        sql = f"""
            {prefix} INTO {CHAT_TABLE} (
                name,
                chat_content
            )
            VALUES (?, ?)
        """
        try:
            cursor.execute(sql, (name, json.dumps(contents)))
            conn.commit()

        except Exception as e:
            if not isinstance(e, sqlite3.IntegrityError):
                self._console.print(f"\n💾 [bold red]Error saving chat [cyan]\"{name}\"[/cyan]: {e}[/bold red]")

            raise e

        finally:
            cursor.close()
            conn.close()


    def get_chat(self, name: str) -> list[dict[str, str]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = f"SELECT chat_content FROM {CHAT_TABLE} WHERE name = ?"

        try:
            cursor.execute(sql,(name, ))
            row = cursor.fetchone()

            if row:
                return json.loads(row[0])

        except Exception as e:
            self._console.print(f"\n📂 [bold red]Error retrieving chat [cyan]\"{name}\"[/cyan]: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return None


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
            self._console.print(f"\n🔍 [bold red]Error retrieving top {CHUNKS_MATCHED} chunks: {e}[/bold red]")

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





