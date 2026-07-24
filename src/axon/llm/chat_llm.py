from typing import Any

from axon.ui.axon_ui import AxonUI
from axon.ui.formatters import emphasis, dim

from .llm_adapter import LLMAdapter
from .models import DEFAULT_CHAT_MODEL, CHAT_UTILITY_MODEL
from .prompts import AXON_SYSTEM_PROMPT, REWRITE_SYSTEM_PROMPT, COMPACT_SYSTEM_PROMPT
from .settings import (
    DEFAULT_CONTEXT_SIZE,
    CHAT_TEMPERATURE,
    COMPACT_TEMPERATURE,
    REWRITE_HISTORY_LIMIT,
    REWRITE_TEMPERATURE,
    ROLLING_HISTORY_LIMIT,
)
from .contracts import LLM_CONTRACT
from .history import (
    user_message,
    model_message,
    text_message,
    tool_call,
    tool_response,
    format_history_transcript,
)


class ChatLLM:
    def __init__(self, ui: AxonUI, llm_adapter: LLMAdapter):
        self._chat_model = DEFAULT_CHAT_MODEL
        self._context_size = DEFAULT_CONTEXT_SIZE
        self._utility_model = CHAT_UTILITY_MODEL
        self._ui = ui
        self._llm_adapter = llm_adapter
        self._auto_compact_enabled = False
        self._chat_roll_enabled = False
        self._history = []


    def _construct_query(self, chunks: str | None, user_input: str) -> str:
        if not chunks:
            return user_input

        return (
            f"<retrieved_excerpts>\n{chunks}\n</retrieved_excerpts>\n"
            f"<user_question>\n{user_input}\n</user_question>".strip()
        )


    def _auto_compact(self, new_message: dict[str, Any] | None = None) -> None:
        if not self._auto_compact_enabled:
            return

        payload = self._history + ([new_message] if new_message else [])
        payload_len = self.get_token_count(payload)

        if payload_len is None:
            return

        if payload_len > self._context_size:
            self._ui.warning("Token limit reached. Triggering auto-compact.")

            if self.compact():
                self._ui.success("Auto-compact successful. Context window refreshed!")


    def _apply_rolling_window(self) -> None:
        if not self._chat_roll_enabled:
            return

        if len(self._history) > ROLLING_HISTORY_LIMIT:
            self._history = self._history[-ROLLING_HISTORY_LIMIT:]


    def _within_token_limit(self, payload_len: int | None) -> bool:
        if payload_len is None:
            return False

        if payload_len <= self._context_size:
            return True

        self._ui.warning(
            f"Context Limit Exceeded: Message requires {emphasis(payload_len)} tokens "
            f"(Limit: {emphasis(self._context_size)})."
        )
        self._ui.info(dim(
            f"Try running {emphasis('/chat compact')} "
            f"or {emphasis('/chat roll')} to free up memory!"
        ))
        return False


    def set_chat_model(self, model: str) -> None:
        self._chat_model = model


    def set_llm_adapter(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter


    def set_chat_limit(self, limit: int) -> None:
        self._context_size = limit


    def get_chat_limit(self) -> int:
        return self._context_size


    def toggle_auto_compact(self) -> bool:
        self._auto_compact_enabled = not self._auto_compact_enabled
        return self._auto_compact_enabled


    def toggle_chat_roll(self) -> bool:
        self._chat_roll_enabled = not self._chat_roll_enabled
        return self._chat_roll_enabled


    def clear_history(self) -> None:
        self._history = []


    def get_history(self) -> list[dict[str, Any]]:
        return self._history.copy()


    def set_history(self, history: list[dict[str, Any]]) -> None:
        self._history = history.copy()


    def add_user_history(self, user_input: str) -> None:
        self._history.append(user_message(user_input))


    def add_model_history(self, response: str) -> None:
        self._history.append(model_message(response))


    def add_tool_call_history(self, tool_name: str, tool_args: dict) -> None:
        self._history.append(tool_call(tool_name, tool_args))


    def add_tool_response_history(self, tool_name: str, result: str) -> None:
        self._history.append(tool_response(tool_name, result))


    def query_chat(self, user_input: str, chunks: str | None) -> str | None:
        new_message = user_message(self._construct_query(chunks, user_input))
        self._apply_rolling_window()
        self._auto_compact(new_message)
        payload = self._history + [new_message]
        payload_len = self.get_token_count(payload)

        if not self._within_token_limit(payload_len):
            return None

        try:
            response = self._llm_adapter.generate_text(
                model=self._chat_model,
                contents=payload,
                system_instruction=AXON_SYSTEM_PROMPT,
                temperature=CHAT_TEMPERATURE,
            )
        except Exception as e:
            self._ui.error(f"Generation Error: {e}.")
            return None

        self.add_user_history(user_input)
        self.add_model_history(response)
        return response


    def query_agent(self, tools: list[dict[str, Any]]) -> dict[str, Any] | None:
        self._apply_rolling_window()
        self._auto_compact()
        payload_len = self.get_token_count(self._history)

        if not self._within_token_limit(payload_len):
            return None

        try:
            response = self._llm_adapter.generate_with_tools(
                model=self._chat_model,
                contents=self._history,
                system_instruction=AXON_SYSTEM_PROMPT,
                tools=tools,
                temperature=CHAT_TEMPERATURE,
            )
        except Exception as e:
            self._ui.error(f"Generation Error: {e}.")
            return None

        return response


    def compact(self) -> str | None:
        if not self._history:
            self._ui.warning("Chat history is empty. Nothing to compact.")
            return None

        transcript = format_history_transcript(self._history)
        compact_content = (
            "Compress the following conversation history into a self-contained "
            f"memory summary that can replace the original chat.\n"
            f"<chat_history>\n{transcript.strip()}\n</chat_history>"
        )

        try:
            response = self._llm_adapter.generate_text(
                model=self._utility_model,
                contents=text_message(compact_content),
                system_instruction=COMPACT_SYSTEM_PROMPT,
                temperature=COMPACT_TEMPERATURE,
            )
        except Exception as e:
            self._ui.error(f"Compaction Error: {e}.")
            return None

        self._history = text_message(response)
        return response


    def get_token_count(self, history: list[dict[str, Any]] | None = None) -> int | None:
        if history is None:
            history = self._history

        try:
            token_count = self._llm_adapter.count_tokens(
                model=self._chat_model,
                contents=history,
                system_instruction=AXON_SYSTEM_PROMPT,
            )
        except Exception as e:
            self._ui.error(f"Error calculating token count: {e}.")
            return None

        return token_count


    def rewrite_query(self, query: str) -> str:
        recent_turns = self._history[-REWRITE_HISTORY_LIMIT:]
        transcript = format_history_transcript(recent_turns)
        user_contents = (
            f"<chat_history>\n{transcript.strip()}\n</chat_history>\n"
            f"<user_question>\n{query}\n</user_question>"
        )

        try:
            rewritten_query = self._llm_adapter.generate_text(
                model=self._utility_model,
                contents=text_message(user_contents),
                system_instruction=REWRITE_SYSTEM_PROMPT,
                temperature=REWRITE_TEMPERATURE,
            )
        except Exception:
            return query

        return rewritten_query
