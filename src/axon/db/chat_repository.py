import json
from datetime import datetime, timezone
from typing import Any

from .contracts import CHAT_FIELDS
from .models import ChatSummary
from .sqlite_database import SQLiteDatabase
from .schema_manager import CHAT_TABLE


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database


    def insert_chat(
        self,
        name: str,
        contents: list[dict[str, Any]],
        overwrite: bool = False
    ) -> None:
        sql = f"""
            INSERT INTO {CHAT_TABLE} (
                {CHAT_FIELDS.NAME},
                {CHAT_FIELDS.CONTENT},
                {CHAT_FIELDS.CREATED_AT},
                {CHAT_FIELDS.LAST_ACCESSED_AT}
            )
            VALUES (?, ?, ?, ?)
        """
        if overwrite:
            sql += f"""
                ON CONFLICT ({CHAT_FIELDS.NAME})
                DO UPDATE SET
                    {CHAT_FIELDS.CONTENT} = excluded.{CHAT_FIELDS.CONTENT},
                    {CHAT_FIELDS.LAST_ACCESSED_AT} = excluded.{CHAT_FIELDS.LAST_ACCESSED_AT}
            """

        now = _utc_now()
        with self._database.connect() as connection:
            connection.execute(
                sql,
                (name, json.dumps(contents), now, now),
            )


    def delete_chat(self, chat: str) -> bool:
        sql = f"""
            DELETE FROM {CHAT_TABLE}
            WHERE {CHAT_FIELDS.NAME} = ?;
        """
        with self._database.connect() as connection:
            cursor = connection.execute(sql, (chat,))
            deleted = cursor.rowcount > 0

        return deleted


    def delete_all_chats(self) -> None:
        sql = f"DELETE FROM {CHAT_TABLE}"
        with self._database.connect() as connection:
            connection.execute(sql)


    def get_chat(self, name: str) -> list[dict[str, Any]] | None:
        select_sql = f"""
            SELECT {CHAT_FIELDS.CONTENT}
            FROM {CHAT_TABLE}
            WHERE {CHAT_FIELDS.NAME} = ?;
        """
        update_access_sql = f"""
            UPDATE {CHAT_TABLE}
            SET {CHAT_FIELDS.LAST_ACCESSED_AT} = ?
            WHERE {CHAT_FIELDS.NAME} = ?;
        """

        with self._database.connect() as connection:
            row = connection.execute(select_sql, (name,)).fetchone()
            if row is not None:
                connection.execute(update_access_sql, (_utc_now(), name))

        if row is not None:
            return json.loads(row[0])

        return None


    def get_chat_summaries(self) -> list[ChatSummary]:
        sql = f"""
            SELECT
                {CHAT_FIELDS.NAME},
                {CHAT_FIELDS.CREATED_AT},
                {CHAT_FIELDS.LAST_ACCESSED_AT}
            FROM {CHAT_TABLE}
            ORDER BY {CHAT_FIELDS.LAST_ACCESSED_AT} DESC,
                {CHAT_FIELDS.NAME} COLLATE NOCASE;
        """
        with self._database.connect() as connection:
            rows = connection.execute(sql).fetchall()

        return [ChatSummary(*row) for row in rows]
