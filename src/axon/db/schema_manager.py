import sqlite3

from .sqlite_database import SQLiteDatabase
from .min_hasher import LSH_BAND_COUNT
from .contracts import CHAT_FIELDS


CHUNK_TABLE = "chunks"
VEC_TABLE = "vec"
PAPER_TABLE = "papers"
CHAT_TABLE = "chats"
LSH_TABLE = "lsh"
FTS_TABLE = "fts"

EMBEDDING_DIM = 1024


class SchemaManager:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database


    def _execute_statements(self, *statements: str, connection: sqlite3.Connection) -> None:
        for statement in statements:
            connection.execute(statement)


    def _create_tables(self, connection: sqlite3.Connection) -> None:
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
                band_idx INTEGER NOT NULL CHECK (band_idx >= 0 and band_idx < {LSH_BAND_COUNT}),
                band_hash INTEGER NOT NULL,
                PRIMARY KEY (paper_id, band_idx)
            ) WITHOUT ROWID;
        """

        create_chats_table = f"""
            CREATE TABLE IF NOT EXISTS {CHAT_TABLE} (
                {CHAT_FIELDS.NAME} TEXT PRIMARY KEY,
                {CHAT_FIELDS.CONTENT} TEXT NOT NULL,
                {CHAT_FIELDS.CREATED_AT} TEXT NOT NULL,
                {CHAT_FIELDS.LAST_ACCESSED_AT} TEXT NOT NULL
            );
        """

        self._execute_statements(
            create_paper_table,
            create_chunks_table,
            create_lsh_table,
            create_chats_table,
            connection=connection,
        )


    def _create_virtual_tables(self, connection: sqlite3.Connection) -> None:
        create_fts_table = f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5 (
                markdown,
                content_rowid='id',
                content='{CHUNK_TABLE}',
                tokenize='porter unicode61'
            );
        """

        create_vec_table = f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {VEC_TABLE} USING vec0 (
                id INTEGER PRIMARY KEY,
                embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine
            );
        """

        self._execute_statements(
            create_fts_table,
            create_vec_table,
            connection=connection,
        )


    def _create_triggers(self, connection: sqlite3.Connection) -> None:
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

        self._execute_statements(
            create_fts_insert_trigger,
            create_fts_delete_trigger,
            create_vec_delete_trigger,
            connection=connection,
        )


    def _create_indexes(self, connection: sqlite3.Connection) -> None:
        create_lsh_lookup_index = f"""
            CREATE INDEX IF NOT EXISTS idx_{LSH_TABLE}_lookup
            ON {LSH_TABLE} (band_idx, band_hash)
        """

        self._execute_statements(
            create_lsh_lookup_index,
            connection=connection,
        )


    def _drop_all(self) -> None:
        with self._database.connect() as connection:
            self._execute_statements(
                f"DROP TABLE IF EXISTS {VEC_TABLE};",
                f"DROP TABLE IF EXISTS {CHUNK_TABLE};",
                f"DROP TABLE IF EXISTS {LSH_TABLE};",
                f"DROP TABLE IF EXISTS {FTS_TABLE};",
                f"DROP TABLE IF EXISTS {PAPER_TABLE};",
                f"DROP TABLE IF EXISTS {CHAT_TABLE};",
                connection=connection,
            )


    def initialize(self) -> None:
        with self._database.connect() as connection:
            self._create_tables(connection)
            self._create_virtual_tables(connection)
            self._create_triggers(connection)
            self._create_indexes(connection)


    def reset(self) -> None:
        self._drop_all()

        with self._database.connect() as connection:
            self._execute_statements(
                "VACUUM;",
                connection=connection
            )

        self.initialize()
