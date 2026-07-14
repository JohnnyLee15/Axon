from typing import Any

from rich.console import Console

from src.utils.config import *
from src.llm.llm_adapter import LLMAdapter

from .models import DEFAULT_CHAT_MODEL, REWRITE_MODEL, COMPACT_MODEL
from .contracts import LLM_CONTRACT
from .history import (
    user_message,
    model_message,
    text_message,
    tool_call,
    tool_response,
)


class ChatLLM:
    def __init__(self, console: Console, llm_adapter: LLMAdapter):
        self._chat_model = DEFAULT_CHAT_MODEL
        self._context_size = LLM_CONTEXT_SIZE_DEFAULT
        self._rewrite_model = REWRITE_MODEL
        self._compact_model = COMPACT_MODEL
        self._console = console
        self._llm_adapter = llm_adapter
        self._auto_compact_enabled = False
        self._chat_roll_enabled = False
        self._history = []


    def set_chat_llm(self, model: str) -> None:
        self._chat_model = model


    def set_llm_adapter(self, llm_adapter: LLMAdapter) -> None:
        self._llm_adapter = llm_adapter


    def set_chat_limit(self, limit: int) -> None:
        self._context_size = limit


    def get_chat_limit(self) -> int:
        return self._context_size


    def clear_history(self) -> None:
        self._history = []


    def get_history(self) -> list[dict[str, Any]]:
        return self._history


    def set_history(self, history: list[dict[str, Any]]) -> None:
        self._history = history


    def toggle_auto_compact(self) -> bool:
        self._auto_compact_enabled = not self._auto_compact_enabled
        return self._auto_compact_enabled


    def toggle_chat_roll(self) -> bool:
        self._chat_roll_enabled = not self._chat_roll_enabled
        return self._chat_roll_enabled


    def get_token_count(self, history: list[dict[str, Any]] | None = None) -> int:
        if history is None:
            history = self._history

        try:
            return self._llm_adapter.count_tokens(
                model=self._chat_model,
                contents=history,
                system_instruction=AXON_SYSTEM_PROMPT,
            )

        except Exception as e:
            self._console.print(f"\n🪙 [bold red]Error calculating token count: {e}[/bold red]")

        return 0


    def _stringify_history_chat(self, item: dict[str, Any]) -> str:
        item_type = item[LLM_CONTRACT.TYPE]

        if item_type == LLM_CONTRACT.USER_TEXT:
            return f"User: {item[LLM_CONTRACT.TEXT]}"

        if item_type == LLM_CONTRACT.MODEL_TEXT:
            return f"Model: {item[LLM_CONTRACT.TEXT]}"

        if item_type == LLM_CONTRACT.TOOL_CALL:
            return f"Model: called {item[LLM_CONTRACT.NAME]} with args {item[LLM_CONTRACT.ARGS]}"

        if item_type == LLM_CONTRACT.TOOL_RESPONSE:
            return f"User: tool {item[LLM_CONTRACT.NAME]} returned {item[LLM_CONTRACT.RESULT]}"

        return ""


    def rewrite_query(self, query: str) -> str:
        recent_turns = self._history[-REWRITE_MESSAGES:]

        transcript = ""
        for item in recent_turns:
            transcript += f"{self._stringify_history_chat(item)}\n"

        user_contents = (
            f"<chat_history>\n{transcript.strip()}\n</chat_history>\n"
            f"<user_question>\n{query}\n</user_question>"
        )

        try:
            return self._llm_adapter.generate_text(
                model=self._rewrite_model,
                contents=text_message(user_contents),
                system_instruction=REWRITE_SYSTEM_PROMPT,
                temperature=LLM_REWRITE_TEMP,
            )

        except Exception:
            return query


    def _construct_query(self, chunks: str | None, user_input: str) -> str:
        if not chunks:
            return user_input

        return (
            f"<retrieved_excerpts>\n{chunks}\n</retrieved_excerpts>\n"
            f"<user_question>\n{user_input}\n</user_question>".strip()
        )


    def add_user_history(self, user_input: str) -> None:
        self._history.append(user_message(user_input))


    def add_model_history(self, response: str) -> None:
        self._history.append(model_message(response))


    def add_function_call_history(self, tool_name: str, tool_args: dict) -> None:
        self._history.append(tool_call(tool_name, tool_args))


    def add_function_response_history(self, tool_name: str, result: str) -> None:
        self._history.append(tool_response(tool_name, result))


    def _auto_compact(self, new_message: dict[str, Any] | None = None) -> None:
        if not self._auto_compact_enabled:
            return

        payload = self._history + ([new_message] if new_message else [])
        payload_len = self.get_token_count(payload)

        if payload_len > self._context_size:
            self._console.print("\n🗜️  [bold yellow]Token limit reached. Triggering auto-compact.[/bold yellow]")

            if self.compact():
                self._console.print("🧼 [bold]Auto-compact successful. Context window refreshed![/bold]")


    def _apply_rolling_window(self) -> None:
        if not self._chat_roll_enabled:
            return

        if len(self._history) > MAX_ROLLING_MSGS:
            self._history = self._history[-MAX_ROLLING_MSGS:]


    def query_chat(self, user_input: str, chunks: str | None) -> str | None:
        new_message = user_message(self._construct_query(chunks, user_input))
        self._apply_rolling_window()
        self._auto_compact(new_message)
        payload = self._history + [new_message]
        payload_len = self.get_token_count(payload)

        if payload_len > self._context_size:
            self._console.print(
                "\n⚠️  [bold yellow]Context Limit Exceeded:[/bold yellow] "
                f"[bold]Message requires [cyan]{payload_len}[/cyan] tokens "
                f"(Limit: [cyan]{self._context_size}[/cyan]).[bold]"
            )
            self._console.print(
                "💡 [dim]Try running [bold cyan]/chat compact[/bold cyan] "
                "or [bold cyan]/chat roll[/bold cyan] to free up memory![/dim]")
            return None

        try:
            response = self._llm_adapter.generate_text(
                model=self._chat_model,
                contents=payload,
                system_instruction=AXON_SYSTEM_PROMPT,
                temperature=LLM_CHAT_TEMP,
            )

            self.add_user_history(user_input)
            self.add_model_history(response)
            return response

        except Exception as e:
            self._console.print(f"\n❌ [bold red]Generation Error: {e}[/bold red]")

        return None


    def query_agent(self, tools: list) -> list[dict[str, Any]]:
        self._apply_rolling_window()
        self._auto_compact()
        payload_len = self.get_token_count(self._history)

        if payload_len > self._context_size:
            self._console.print(
                "\n⚠️  [bold yellow]Context Limit Exceeded:[/bold yellow] "
                f"[bold]Message requires [cyan]{payload_len}[/cyan] tokens "
                f"(Limit: [cyan]{self._context_size}[/cyan]).[bold]"
            )
            self._console.print(
                "💡 [dim]Try running [bold cyan]/chat compact[/bold cyan] "
                "or [bold cyan]/chat roll[/bold cyan] to free up memory![/dim]")
            return None

        try:
            return self._llm_adapter.generate_with_tools(
                model=self._chat_model,
                contents=self._history,
                system_instruction=AXON_SYSTEM_PROMPT,
                tools=tools,
                temperature=LLM_CHAT_TEMP,
            )

        except Exception as e:
            self._console.print(f"\n❌ [bold red]Generation Error: {e}[/bold red]")

        return None


    def compact(self) -> str | None:
        if not self._history:
            self._console.print("\n📭 [bold yellow]Chat history is empty. Nothing to compact.[/bold yellow]")
            return None

        transcript = ""
        for item in self._history:
            transcript += f"{self._stringify_history_chat(item)}\n"

        compact_content = (
            "Compress the following conversation history into a self-contained "
            f"memory summary that can replace the original chat.\n"
            f"<chat_history>\n{transcript.strip()}\n</chat_history>"
        )

        try:
            response = self._llm_adapter.generate_text(
                model=self._compact_model,
                contents=text_message(compact_content),
                system_instruction=COMPACT_SYSTEM_PROMPT,
                temperature=LLM_COMPACT_TEMP,
            )

            self._history = text_message(response)
            return response

        except Exception as e:
            self._console.print(f"\n❌ [bold red]Compaction Error: {e}[/bold red]")

        return None