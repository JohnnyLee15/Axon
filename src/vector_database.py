import sqlite3
import sqlite_vec
from config import *
from chunk_tracker import Chunk
from document_state import ParsedDoc
import json
from rich.console import Console

class VectorDatabase:
    def __init__(self, console: Console) -> None:
        self._console = console
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

        # --- TABLES ---
        create_paper_table = f"""
            CREATE TABLE IF NOT EXISTS {PAPER_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                doi TEXT UNIQUE,
                arxiv TEXT UNIQUE,
                pmcid TEXT UNIQUE,
                pmid TEXT UNIQUE,
                minhash_sig BLOB NOT NULL
            );
        """

        create_chunks_table = f"""
            CREATE TABLE IF NOT EXISTS {CHUNK_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL CHECK (paper_id > 0) REFERENCES {PAPER_TABLE}(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
                markdown TEXT NOT NULL
            );
        """

        create_lsh_table = f"""
            CREATE TABLE IF NOT EXISTS {LSH_TABLE} (
                paper_id INTEGER NOT NULL REFERENCES {PAPER_TABLE}(id) ON DELETE CASCADE,
                band_idx INTEGER NOT NULL CHECK (band_idx >= 0 and band_idx < {LSH_BANDS}),
                band_hash INTEGER NOT NULL,
                PRIMARY KEY (paper_id, band_idx)
            ) WITHOUT ROWID;
        """

        create_chats_table = f"""
            CREATE TABLE IF NOT EXISTS {CHAT_TABLE} (
                name TEXT PRIMARY KEY,
                chat_content TEXT
            );
        """

        # --- VIRTUAL TABLES ---
        create_fts_table = f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5 (
                markdown,
                content_rowid='id',
                content='{CHUNK_TABLE}',
                tokenize='unicode61'
            );
        """

        create_vec_table = f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {VEC_TABLE} USING vec0 (
                id INTEGER PRIMARY KEY,
                embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine
            );
        """

        # --- TRIGGERS ---
        create_fts_insert_trigger = f"""
            CREATE TRIGGER IF NOT EXISTS {CHUNK_TABLE}_after_insert
            AFTER INSERT ON {CHUNK_TABLE}
            BEGIN
                INSERT INTO {FTS_TABLE} (
                    rowid,
                    markdown
                )
                VALUES (new.id, new.markdown);
            END;
        """

        create_fts_delete_trigger = f"""
            CREATE TRIGGER IF NOT EXISTS {CHUNK_TABLE}_after_delete
            AFTER DELETE ON {CHUNK_TABLE}
            BEGIN
                INSERT INTO {FTS_TABLE} (
                    {FTS_TABLE},
                    rowid,
                    markdown
                )
                VALUES ('delete', old.id, old.markdown);
            END;
        """

        create_vec_delete_trigger = f"""
            CREATE TRIGGER IF NOT EXISTS {CHUNK_TABLE}_after_delete_vec
            AFTER DELETE ON {CHUNK_TABLE}
            BEGIN
                DELETE FROM {VEC_TABLE} WHERE id = old.id;
            END;
        """

        # --- INDEXES ---
        create_lsh_lookup_index = f"""
            CREATE INDEX IF NOT EXISTS idx_{LSH_TABLE}_lookup
            ON {LSH_TABLE} (band_idx, band_hash)
        """

        try:
            cursor.execute(create_paper_table)
            cursor.execute(create_chunks_table)
            cursor.execute(create_lsh_table)
            cursor.execute(create_chats_table)

            cursor.execute(create_fts_table)
            cursor.execute(create_vec_table)

            cursor.execute(create_fts_insert_trigger)
            cursor.execute(create_fts_delete_trigger)
            cursor.execute(create_vec_delete_trigger)

            cursor.execute(create_lsh_lookup_index)
            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            self._console.print(f"\n🏗️ [bold red]Error creating database tables: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()


    def _drop_all(self) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        drop_vec = f"DROP TABLE IF EXISTS {VEC_TABLE};"
        drop_chunks = f"DROP TABLE IF EXISTS {CHUNK_TABLE};"
        drop_lsh = f"DROP TABLE IF EXISTS {LSH_TABLE};"
        drop_fts = f"DROP TABLE IF EXISTS {FTS_TABLE};"
        drop_papers = f"DROP TABLE IF EXISTS {PAPER_TABLE};"
        drop_chats = f"DROP TABLE IF EXISTS {CHAT_TABLE};"

        try:
            cursor.execute(drop_vec)
            cursor.execute(drop_chunks)
            cursor.execute(drop_lsh)
            cursor.execute(drop_fts)
            cursor.execute(drop_papers)
            cursor.execute(drop_chats)
            conn.commit()

            cursor.execute("VACUUM")

            return True

        except sqlite3.Error as e:
            conn.rollback()
            self._console.print(f"\n🧹 [bold red]Error dropping tables during database clear: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return False


    def reset(self) -> None:
        if self._drop_all():
            self._init_db()


    def metadata_exists(self, parsed_doc: ParsedDoc) -> bool | None:
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = f"""
            SELECT 1
            FROM {PAPER_TABLE}
            WHERE doi = ?
                OR arxiv = ?
                OR pmcid = ?
                OR pmid = ?
            LIMIT 1;
        """

        params = (parsed_doc.doi, parsed_doc.arxiv, parsed_doc.pmcid, parsed_doc.pmid)
        try:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return row is not None

        except Exception as e:
            active_ids = []
            if parsed_doc.doi:
                active_ids.append(f"DOI: {parsed_doc.doi}")

            if parsed_doc.arxiv:
                active_ids.append(f"arXiv: {parsed_doc.arxiv}")

            if parsed_doc.pmcid:
                active_ids.append(f"PMCID: {parsed_doc.pmcid}")

            if parsed_doc.pmid:
                active_ids.append(f"PMID: {parsed_doc.pmid}")

            id_str = ", ".join(active_ids) if active_ids else "No Identifiers"
            self._console.print(f"\n❌ [bold red]Database Error checking metadata [cyan]({id_str})[/cyan]:[/bold red] {e}")

        finally:
            cursor.close()
            conn.close()

        return None


    def get_lsh_candidates(self, band_hashes: list[int]) -> list[tuple[int, bytes]] | None:
        conn = self._get_connection()
        cursor = conn.cursor()

        band_conds = " OR ".join(
            [f"(band_idx = {i} AND band_hash = ?)" for i in range(len(band_hashes))]
        )
        sql = f"""
            SELECT DISTINCT p.id, p.minhash_sig
            FROM {PAPER_TABLE} p
            JOIN {LSH_TABLE} l ON p.id = l.paper_id
            WHERE {band_conds};
        """

        try:
            cursor.execute(sql, tuple(band_hashes))
            return cursor.fetchall()

        except Exception as e:
            self._console.print(f"\n🔍 [bold red]Error retrieving LSH candidates: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return None


    def insert_paper(
        self,
        parsed_doc: ParsedDoc,
        minhash_sig: bytes,
        band_hashes: list[int]
    ) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        paper_stmt = f"""
            INSERT INTO {PAPER_TABLE} (
                title,
                doi,
                arxiv,
                pmcid,
                pmid,
                minhash_sig
            )
            VALUES (?, ?, ?, ?, ?, ?);
        """
        lsh_stmt = f"""
            INSERT INTO {LSH_TABLE} (
                paper_id,
                band_idx,
                band_hash
            )
            VALUES (?, ?, ?);
        """

        paper_params = (
            parsed_doc.title,
            parsed_doc.doi,
            parsed_doc.arxiv,
            parsed_doc.pmcid,
            parsed_doc.pmid,
            minhash_sig
        )

        try:
            cursor.execute(paper_stmt, paper_params)
            paper_id = cursor.lastrowid

            lsh_params = [(paper_id, i, h) for i, h in enumerate(band_hashes)]
            cursor.executemany(lsh_stmt, lsh_params)

            conn.commit()
            return paper_id

        except sqlite3.Error as e:
            conn.rollback()
            self._console.print(f"\n📄 [bold red]Error creating new paper: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return -1


    def insert_paper_chunks(self, chunks: dict[int, Chunk], paper_id: int) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
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
            VALUES (?, ?);
        """
        try:
            cursor.execute(sql, (name, json.dumps(contents)))
            conn.commit()

        except Exception as e:
            conn.rollback()
            if not isinstance(e, sqlite3.IntegrityError):
                self._console.print(f"\n💾 [bold red]Error saving chat [cyan]\"{name}\"[/cyan]: {e}[/bold red]")

            raise e

        finally:
            cursor.close()
            conn.close()


    def delete_chat(self, chat: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = f"DELETE FROM {CHAT_TABLE} WHERE name = ?;"

        try:
            cursor.execute(sql, (chat,))
            if cursor.rowcount == 0:
                return False

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            self._console.print(f"\n📂 [bold red]Error deleting chat [cyan]\"{chat}\"[/cyan]: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return False


    def delete_all_chats(self) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = f"DELETE FROM {CHAT_TABLE}"

        try:
            cursor.execute(sql)
            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            self._console.print(f"\n📂 [bold red]Error deleting all chats: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return False


    def get_chat(self, name: str) -> list[dict[str, str]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = f"SELECT chat_content FROM {CHAT_TABLE} WHERE name = ?;"

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


    def get_all_chat_names(self) -> list[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        sql = f"SELECT name FROM {CHAT_TABLE};"

        try:
            cursor.execute(sql)
            rows = cursor.fetchall()

            return [row[0] for row in rows]

        except Exception as e:
            self._console.print(f"\n📂 [bold red]Error retrieving chats: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return None


    def _get_top_k_vector_ids(self, query_embedding: list[float]) -> list[tuple]:
        conn = self._get_connection()
        cursor = conn.cursor()
        rows = []
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

        try:
            cursor.execute(
                sql,
                (sqlite_vec.serialize_float32(query_embedding),)
            )
            rows = cursor.fetchall()

        except sqlite3.Error as e:
            self._console.print(f"\n🔍 [bold red]Error retrieving top {INITIAL_CHUNK_K} vector chunks: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return rows


    def _get_top_k_bm25_ids(self, query: str) -> list[tuple]:
        query = REPLACE_WHITESPACE_WITH_SPACE.sub(" ", query)
        tokens = query.split()
        query = " OR ".join(f'"{tok.replace(chr(34), chr(34)*2)}"' for tok in tokens)

        conn = self._get_connection()
        cursor = conn.cursor()
        rows = []
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

        try:
            cursor.execute(sql, (query,))
            return cursor.fetchall()

        except Exception as e:
            self._console.print(f"\n🔍 [bold red]Error retrieving top {INITIAL_CHUNK_K} BM25 chunks: {e}[/bold red]")

        finally:
            cursor.close()
            conn.close()

        return rows


    def top_chunk_matches(self, query: str, query_embedding: list[float]) -> dict[int, dict[str, str | int]]:
        bm25_chunks = self._get_top_k_bm25_ids(query)
        vec_chunks = self._get_top_k_vector_ids(query_embedding)

        chunks = {}
        for cid, pid, cidx, text in bm25_chunks:
            chunks[cid] = {
                "paper_id": pid,
                "chunk_index": cidx,
                "text": text
            }

        for cid, pid, cidx, text in vec_chunks:
            chunks[cid] = {
                "paper_id": pid,
                "chunk_index": cidx,
                "text": text
            }

        return chunks


    # def get_formatted_chunks(self, query_embedding: list[float]) -> str | None:
    #     rows = self._get_top_k_vector_ids(query_embedding)
    #     if not rows:
    #         return None

    #     curr_paper_id = None
    #     parts = []
    #     for row in rows:
    #         paper_id, chunk_index, markdown, _ = row
    #         if paper_id != curr_paper_id:
    #             if curr_paper_id is not None:
    #                 parts.append("</document>")
    #             curr_paper_id = paper_id
    #             parts.append(f"<document id='{paper_id}'>")

    #         parts.append(f"<chunk id='{chunk_index}'>")
    #         parts.append(markdown)
    #         parts.append("</chunk>")

    #     parts.append("</document>")
    #     return "\n".join(parts)





