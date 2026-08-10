import sqlite3

from axon.db.chat_repository import ChatRepository
from axon.db.models import ChatSummary
from axon.llm.chat_llm import ChatLLM
from axon.ui.axon_ui import AxonUI
from axon.ui.formatters import emphasis
from axon.commands.flags import OVERWRITE_CHAT_FLAG, DELETE_ALL_CHATS_FLAG
from axon.ui.choices import CONFIRM_NO, CONFIRM_YES
from axon.config.settings_store import SettingsStore, CHAT_LIMIT_KEY

from .options import CHAT_LIMIT_OPTIONS
from .interrupt_coordinator import InterruptCoordinator


class ChatHandlers:
    def __init__(
        self,
        chat_repository: ChatRepository,
        llm: ChatLLM,
        ui: AxonUI,
        settings: SettingsStore,
        interrupt_coordinator: InterruptCoordinator,
    ) -> None:
        self._chat_repository = chat_repository
        self._llm = llm
        self._ui = ui
        self._settings = settings
        self._interrupt_coordinator = interrupt_coordinator


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


    def _get_chat_summaries(self) -> list[ChatSummary] | None:
        try:
            return self._chat_repository.get_chat_summaries()
        except sqlite3.Error as error:
            self._ui.error(f"Could not retrieve saved chats: {error}")
            return None


    async def _select_saved_chat(self) -> str | None:
        chats = self._get_chat_summaries()
        if chats is None:
            return None

        if not chats:
            self._ui.info("No saved chats found in the database.")
            return None

        return await self._ui.select_chat(chats)


    async def load_chat(self, name: str | None = None) -> None:
        if name is None:
            name = await self._select_saved_chat()
            if name is None:
                return

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


    def display_history(self) -> None:
        history = self._llm.get_history()
        if not history:
            self._ui.info("No chat history is currently retained.")
            return

        self._ui.display_history(history)


    def list_chats(self) -> None:
        chats = self._get_chat_summaries()
        if chats is None:
            return

        self._ui.display_chats(chats)


    def _delete_all_chats(self) -> None:
        self._ui.warning("This will permanently delete ALL saved chats.")
        confirm_options = f"{CONFIRM_YES}/{CONFIRM_NO}"
        confirm = self._ui.confirm(f"Are you sure? ({emphasis(confirm_options)})")

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


    async def delete_chat(self, arg: str | None = None) -> None:
        if arg is None:
            arg = await self._select_saved_chat()
            if arg is None:
                return

        arg = arg.strip()

        if arg == DELETE_ALL_CHATS_FLAG:
            self._delete_all_chats()
            return

        self._delete_single_chat(arg)


    def chat_roll(self) -> None:
        enabled = self._llm.toggle_chat_roll()
        status = "on" if enabled else "off"
        self._ui.info(f"Chat rolling successfully toggled {emphasis(status)}!")


    async def set_limit(self) -> None:
        selected_limit = await self._ui.select_item(
            options=CHAT_LIMIT_OPTIONS,
            selected_option=self._llm.get_chat_limit(),
        )

        if selected_limit is None:
            return

        self._llm.set_chat_limit(selected_limit)
        self._settings.set(key=CHAT_LIMIT_KEY, value=selected_limit)
        self._ui.info(f"Chat Context Limit: {emphasis(selected_limit)}.")


    def auto_compact(self) -> None:
        enabled = self._llm.toggle_auto_compact()
        status = "on" if enabled else "off"
        self._ui.info(f"Auto-compact successfully toggled {emphasis(status)}!")


    async def compact(self) -> None:
        with self._ui.wait(show_cancel_hint=True):
            interrupted, response = await self._interrupt_coordinator.run(
                self._llm.compact()
            )

        if interrupted:
            self._ui.info("Compaction interrupted.")
            return

        if response is not None:
            self._ui.stream_response(response)
            self._ui.success("Successfully compacted chat history!")
