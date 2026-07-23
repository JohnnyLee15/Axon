import sqlite3

from src.db.chat_repository import ChatRepository
from src.llm.chat_llm import ChatLLM
from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis
from src.commands.flags import OVERWRITE_CHAT_FLAG, DELETE_ALL_CHATS_FLAG
from src.ui.choices import CONFIRM_NO, CONFIRM_YES


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
        chat_repository: ChatRepository,
        llm: ChatLLM,
        ui: AxonUI
    ) -> None:
        self._chat_repository = chat_repository
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
            self._chat_repository.insert_chat(name, self._llm.get_history(), overwrite)
        except sqlite3.IntegrityError:
            overwrite_cmd = f"/chat save {name} {OVERWRITE_CHAT_FLAG}"
            self._ui.warning(
                f"Chat \"{emphasis(name)}\" already exists! No chats saved. "
                f"Use {emphasis(overwrite_cmd)} to overwrite."
            )
            return
        except sqlite3.Error as error:
            self._ui.error(f"Could not save chat: {error}")
            return

        self._ui.success(f"Chat saved as \"{emphasis(name)}\"!")


    def load_chat(self, name: str) -> None:
        name = name.strip()

        try:
            history = self._chat_repository.get_chat(name)
        except sqlite3.Error as error:
            self._ui.error(f"Could not load chat: {error}")
            return

        if history is None:
            self._ui.warning(f"Chat \"{emphasis(name)}\" not found. No chats loaded.")
            return

        self._llm.set_history(history)
        self._ui.success(f"Successfully loaded chat history from \"{emphasis(name)}\"!")


    def clear_chat(self) -> None:
        self._llm.clear_history()
        self._ui.success("Chat history cleared!")


    def list_chats(self) -> None:
        try:
            chat_names = self._chat_repository.get_all_chat_names()
        except sqlite3.Error as error:
            self._ui.error(f"Could not retrieve saved chats: {error}")
            return

        self._ui.display_chat_names(chat_names)


    def _delete_all_chats(self) -> None:
        self._ui.warning("This will permanently delete ALL saved chats.")
        confirm_options = f"{CONFIRM_YES}/{CONFIRM_NO}"
        confirm = self._ui.confirm(f"Are you sure? ({emphasis(confirm_options)}): ")

        if confirm.strip().lower() != CONFIRM_YES:
            self._ui.info("Deletion canceled.")
            return

        try:
            self._chat_repository.delete_all_chats()
        except sqlite3.Error as error:
            self._ui.error(f"Could not delete saved chats: {error}")
            return

        self._ui.success("All saved chats have been deleted!")


    def _delete_single_chat(self, chat_name: str) -> None:
        try:
            deleted = self._chat_repository.delete_chat(chat_name)
        except sqlite3.Error as error:
            self._ui.error(f"Could not delete chat: {error}")
            return

        if deleted:
            self._ui.success(f"Chat \"{emphasis(chat_name)}\" deleted successfully!")
            return

        self._ui.warning(f"Chat \"{emphasis(chat_name)}\" not found.")


    def delete_chat(self, arg: str) -> None:
        arg = arg.strip()

        if arg == DELETE_ALL_CHATS_FLAG:
            self._delete_all_chats()
            return

        self._delete_single_chat(arg)


    def chat_roll(self) -> None:
        enabled = self._llm.toggle_chat_roll()
        status = "on" if enabled else "off"
        self._ui.info(f"Chat rolling successfully toggled {emphasis(status)}!")


    def set_limit(self) -> None:
        selected_limit = self._ui.select_option(CHAT_LIMIT_OPTIONS)
        self._llm.set_chat_limit(selected_limit)
        self._ui.info(f"Chat Context Limit: {emphasis(selected_limit)}.")


    def auto_compact(self) -> None:
        enabled = self._llm.toggle_auto_compact()
        status = "on" if enabled else "off"
        self._ui.info(f"Auto-compact successfully toggled {emphasis(status)}!")


    def compact(self) -> None:
        with self._ui.wait():
            response = self._llm.compact()

        if response is not None:
            self._ui.stream_response(response)
            self._ui.success("Successfully compacted chat history!")