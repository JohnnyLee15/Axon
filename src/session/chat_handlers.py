import sqlite3

from src.db.vector_database import VectorDatabase
from src.llm.chat_llm import ChatLLM
from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis
from src.commands.flags import OVERWRITE_CHAT_FLAG, DELETE_ALL_CHATS_FLAG
from src.commands.choices import CONFIRM_NO, CONFIRM_YES

CHAT_LIMIT_OPTIONS = [
    {"id": 10000, "label": "10,000 (small)"},
    {"id": 20000, "label": "20,000 (short)"},
    {"id": 50000, "label": "50,000 (medium)"},
    {"id": 100000, "label": "100,000 (large)"},
    {"id": 200000, "label": "200,000 (huge)"},
    {"id": 750000, "label": "750,000 (max)"}
]


class ChatHandlers:
    def __init__(
        self,
        db: VectorDatabase,
        llm: ChatLLM,
        ui: AxonUI
    ) -> None:
        self._db = db
        self._llm = llm
        self._ui = ui


    def save_chat(self, name: str, flag: str | None = None) -> None:
        name = name.strip()
        overwrite = False

        if flag:
            if flag.strip() == OVERWRITE_CHAT_FLAG:
                overwrite = True
            else:
                self._ui.unknown(
                    f"Unknown flag: \"{emphasis(flag)}\". "
                    f"Did you mean \"{emphasis(OVERWRITE_CHAT_FLAG)}\"?"
                )
                return

        try:
            self._db.insert_chat(name, self._llm.get_history(), overwrite)
            self._ui.success(f"Chat saved as \"{emphasis(name)}\"!")

        except sqlite3.IntegrityError:
            overwrite_cmd = f"/chat save {name} {OVERWRITE_CHAT_FLAG}"
            self._ui.warning(
                f"Chat \"{emphasis(name)}\" already exists! No chats saved. "
                f"Use {emphasis(overwrite_cmd)} to overwrite."
            )


    def load_chat(self, name: str) -> None:
        name = name.strip()
        history = self._db.get_chat(name)

        if history is None:
            self._ui.warning(f"Chat \"{emphasis(name)}\" not found. No chats loaded.")
            return

        self._llm.set_history(history)
        self._ui.success(f"Successfully loaded chat history from \"{emphasis(name)}\"!")


    def clear_chat(self) -> None:
        self._llm.clear_history()
        self._ui.success("Chat history cleared!")


    def list_chats(self) -> None:
        chat_names = self._db.get_all_chat_names()
        if chat_names is None:
            return

        self._ui.display_chat_names(chat_names)


    def delete_chat(self, arg: str) -> None:
        arg = arg.strip()

        if arg == DELETE_ALL_CHATS_FLAG:
            self._ui.warning("This will permanently delete ALL saved chats.")
            confirm_options = f"{CONFIRM_YES}/{CONFIRM_NO}"
            confirm = self._ui.confirm(f"Are you sure? ({emphasis(confirm_options)}): ")

            if confirm.strip().lower() == CONFIRM_YES:
                success = self._db.delete_all_chats()
                if success:
                    self._ui.success("All saved chats have been deleted!")
            else:
                self._ui.info("Deletion canceled.")

        else:
            success = self._db.delete_chat(arg)
            if success:
                self._ui.success(f"Chat \"{emphasis(arg)}\" deleted successfully!")
            else:
                self._ui.warning(f"Chat \"{emphasis(arg)}\" not found.")


    def chat_roll(self) -> None:
        bool_val = self._llm.toggle_chat_roll()
        status = "on" if bool_val else "off"
        self._ui.info(f"Chat rolling successfully toggled {emphasis(status)}!")


    def set_limit(self) -> None:
        selected_limit = self._ui.select_option(CHAT_LIMIT_OPTIONS)
        self._llm.set_chat_limit(selected_limit)
        self._ui.info(f"Chat Context Limit: {emphasis(selected_limit)}.")


    def auto_compact(self) -> None:
        bool_val = self._llm.toggle_auto_compact()
        status = "on" if bool_val else "off"
        self._ui.info(f"Auto-compact successfully toggled {emphasis(status)}!")


    def compact(self) -> None:
        with self._ui.wait():
            response = self._llm.compact()

        if response is not None:
            self._ui.stream_response(response)
            self._ui.success("Successfully compacted chat history!")