from abc import ABC, abstractmethod
from typing import Any, Callable

from src.ui.axon_ui import AxonUI

from .contracts import LLM_CONTRACT
from .retry import execute_with_retries


class LLMAdapter(ABC):
    @abstractmethod
    def _format_tools(
        self,
        tools: list[dict[str, Any]] | None,
    ) -> Any:
        raise NotImplementedError


    @abstractmethod
    def _user_message(self, text: str) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def _model_message(self, text: str) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def _tool_call_message(
        self,
        name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def _tool_response_message(
        self,
        name: str,
        result: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def _is_retryable_error(self, error: Exception) -> bool:
        """Return whether a provider error should be retried."""
        raise NotImplementedError


    @abstractmethod
    def count_tokens(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
    ) -> int:
        raise NotImplementedError


    @abstractmethod
    def generate_text(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        raise NotImplementedError


    @abstractmethod
    def generate_json(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def generate_with_tools(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """
        Returns:
            {
                "text": str,
                "tool_calls": [
                    {"name": str, "args": dict}
                ],
                "raw": Any
            }
        """
        raise NotImplementedError


    def _execute_with_retries(
        self,
        api_func: Callable,
        ui: AxonUI,
        *args,
        **kwargs
    ) -> Any:
        return execute_with_retries(
            api_func,
            self._is_retryable_error,
            ui,
            *args,
            **kwargs,
        )


    def format_history(
        self,
        history: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        contents = []
        for item in history:
            item_type = item[LLM_CONTRACT.TYPE]

            if item_type == LLM_CONTRACT.USER_TEXT:
                contents.append(self._user_message(item[LLM_CONTRACT.TEXT]))
            elif item_type == LLM_CONTRACT.MODEL_TEXT:
                contents.append(self._model_message(item[LLM_CONTRACT.TEXT]))
            elif item_type == LLM_CONTRACT.TOOL_CALL:
                contents.append(self._tool_call_message(item[LLM_CONTRACT.NAME], item[LLM_CONTRACT.ARGS]))
            elif item_type == LLM_CONTRACT.TOOL_RESPONSE:
                contents.append(self._tool_response_message(item[LLM_CONTRACT.NAME], item[LLM_CONTRACT.RESULT]))
            else:
                raise ValueError(f"Unknown Axon history item type: {item_type}")

        return contents



