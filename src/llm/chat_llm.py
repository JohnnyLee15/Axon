from src.utils.config import *
from src.utils.api_utils import execute_with_retries

import os
from google import genai
from rich.console import Console

from typing import Any

class ChatLLM:
    def __init__(self, console: Console):
        self._chat_model = LLM_CHAT_MODEL_DEFAULT
        self._context_size = LLM_CONTEXT_SIZE_DEFAULT
        self._rewrite_model = LLM_REWRITE_MODEL
        self._compact_model = LLM_COMPACT_MODEL
        self._console = console
        self._auto_compact_enabled = False
        self._chat_roll_enabled = False
        self._client = genai.Client(api_key=os.getenv("GEM_API_KEY"))
        self._history = []


    def set_chat_llm(self, model: str) -> None:
        self._chat_model = model


    def set_chat_limit(self, limit: int) -> None:
        self._context_size = limit


    def get_chat_limit(self) -> int:
        return self._context_size


    def clear_history(self) -> None:
        self._history = []


    def get_history(self) -> list[dict[str, str]]:
        return self._history


    def set_history(self, history: list[dict[str, str]]) -> None:
        self._history = history


    def toggle_auto_compact(self) -> bool:
        self._auto_compact_enabled = not self._auto_compact_enabled
        return self._auto_compact_enabled


    def toggle_chat_roll(self) -> bool:
        self._chat_roll_enabled = not self._chat_roll_enabled
        return self._chat_roll_enabled


    def get_token_count(self, history: list[dict[str, str]] | None = None) -> int:
        if history is None:
            history = self._history

        try:
            contents = [{
                "role": "user",
                "parts": [{"text": f"SYSTEM_INSTRUCTION:\n{AXON_SYSTEM_PROMPT}"}]
            }] + history
            response = execute_with_retries(
                api_func=self._client.models.count_tokens,
                console=self._console,
                num_retries=MAX_RETRIES,
                model=self._chat_model,
                contents=contents,
            )
            return response.total_tokens

        except Exception as e:
            self._console.print(f"\n🪙 [bold red]Error calculating token count: {e}[/bold red]")

        return 0


    def _stringify_history_chat(self, role: str, part: dict) -> str:
        if "text" in part:
            return f"{role}: {part['text']}"

        if "function_call" in part:
            fc = part["function_call"]
            return f"{role}: called tool {fc['name']} with args {fc['args']}"

        if "function_response" in part:
            fr = part["function_response"]
            result = fr["response"]["result"]
            return f"{role}: tool {fr['name']} returned {result}"

        return ""


    def rewrite_query(self, query: str) -> str:
        recent_turns = self._history[-REWRITE_MESSAGES:]

        transcript = ""
        for msg in recent_turns:
            role = "User" if msg["role"] == "user" else "Model"
            content = self._stringify_history_chat(role, msg["parts"][0])
            transcript += f"{content}\n"

        user_content = (
            f"<chat_history>\n{transcript.strip()}\n</chat_history>\n"
            f"<user_question>\n{query}\n</user_question>"
        )

        try:
            response = execute_with_retries(
                api_func=self._client.models.generate_content,
                console=self._console,
                num_retries=MAX_RETRIES,
                model=self._rewrite_model,
                contents=user_content,
                config={
                    "system_instruction": REWRITE_SYSTEM_PROMPT,
                    "temperature": LLM_REWRITE_TEMP
                }
            )
            return response.text.strip()

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
        self._history.append({
            "role": "user",
            "parts": [{"text": user_input}]
        })


    def add_model_history(self, response: str) -> None:
        self._history.append({
            "role": "model",
            "parts": [{"text": response}]
        })


    def add_function_call_history(self, tool_name: str, tool_args: dict) -> None:
        self._history.append({
            "role": "model",
            "parts": [{
                "function_call": {
                    "name": tool_name,
                    "args": tool_args
                }
            }]
        })


    def add_function_response_history(self, tool_name: str, result: str) -> None:
        self._history.append({
            "role": "user",
            "parts": [{
                "function_response": {
                    "name": tool_name,
                    "response": {"result": result}
                }
            }]
        })


    def _auto_compact(self, new_message: dict[str, str | list] | None = None) -> None:
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
        new_message = {
            "role": "user",
            "parts": [{"text": self._construct_query(chunks, user_input)}]
        }

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
            response = execute_with_retries(
                api_func=self._client.models.generate_content,
                console=self._console,
                num_retries=MAX_RETRIES,
                model=self._chat_model,
                contents=payload,
                config={
                    "system_instruction": AXON_SYSTEM_PROMPT,
                    "temperature": LLM_CHAT_TEMP
                }
            )

            response_text = response.text.strip()
            self.add_user_history(user_input)
            self.add_model_history(response_text)
            return response_text

        except Exception as e:
            self._console.print(f"\n❌ [bold red]Generation Error: {e}[/bold red]")

        return None


    def query_agent(self, tools: list) -> Any:
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
            response = execute_with_retries(
                api_func=self._client.models.generate_content,
                console=self._console,
                num_retries=MAX_RETRIES,
                model=self._chat_model,
                contents=self._history,
                config={
                    "system_instruction": AXON_SYSTEM_PROMPT,
                    "temperature": LLM_CHAT_TEMP,
                    "tools": tools
                }
            )

            return response

        except Exception as e:
            self._console.print(f"\n❌ [bold red]Generation Error: {e}[/bold red]")

        return None


    def compact(self) -> str | None:
        if not self._history:
            self._console.print("\n📭 [bold yellow]Chat history is empty. Nothing to compact.[/bold yellow]")
            return None

        transcript = ""
        for msg in self._history:
            role = "User" if msg["role"] == "user" else "Model"
            content = self._stringify_history_chat(role, msg["parts"][0])
            transcript += f"{content}\n"

        compact_content = (
            "Compress the following conversation history into a self-contained "
            f"memory summary that can replace the original chat.\n"
            f"<chat_history>\n{transcript.strip()}\n</chat_history>"
        )

        try:
            response = execute_with_retries(
                api_func=self._client.models.generate_content,
                console=self._console,
                num_retries=MAX_RETRIES,
                model=self._compact_model,
                contents = compact_content,
                config={
                    "system_instruction": COMPACT_SYSTEM_PROMPT,
                    "temperature": LLM_COMPACT_TEMP
                }
            )

            response_text = response.text.strip()
            self._history = [{
                "role": "user",
                "parts": [{"text": response_text}]
            }]

            return response_text

        except Exception as e:
            self._console.print(f"\n❌ [bold red]Compaction Error: {e}[/bold red]")

        return None