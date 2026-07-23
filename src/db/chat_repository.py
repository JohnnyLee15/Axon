import json
from typing import Any

from .sqlite_database import SQLiteDatabase
from .schema_manager import CHAT_TABLE


class ChatRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database


    def insert_chat(
        self,
        name: str,
        contents: list[dict[str, Any]],
        overwrite: bool = False
    ) -> None:
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

        with self._database.connect() as connection:
            connection.execute(sql, (name, json.dumps(contents)))


    def delete_chat(self, chat: str) -> bool:
        sql = f"DELETE FROM {CHAT_TABLE} WHERE name = ?;"
        with self._database.connect() as connection:
            cursor = connection.execute(sql, (chat,))
            deleted = cursor.rowcount > 0

        return deleted


    def delete_all_chats(self) -> None:
        sql = f"DELETE FROM {CHAT_TABLE}"
        with self._database.connect() as connection:
            connection.execute(sql)


    def get_chat(self, name: str) -> list[dict[str, Any]] | None:
        sql = f"SELECT chat_content FROM {CHAT_TABLE} WHERE name = ?;"
        with self._database.connect() as connection:
            row  = connection.execute(sql, (name,)).fetchone()

        if row is not None:
            return json.loads(row[0])

        return None


    def get_all_chat_names(self) -> list[str]:
        sql = f"SELECT name FROM {CHAT_TABLE};"
        with self._database.connect() as connection:
            rows = connection.execute(sql).fetchall()

        return [row[0] for row in rows]
