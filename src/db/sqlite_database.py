import sqlite3
from contextlib import contextmanager
from collections.abc import Generator
from pathlib import Path

import sqlite_vec

from src.utils.paths import DATA_DIR


DB_PATH = DATA_DIR / "axon.db"


class SQLiteDatabase:
    def __init__(self, path: Path = DB_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._path)

        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            yield conn
            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()
