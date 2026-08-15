from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Callable

from axon.ui.axon_ui import AxonUI

from .contracts import LLM_CONTRACT
from .retry import execute_with_retries, execute_with_retries_async
from .errors import InvalidCredentialsError


class LLMAdapter(ABC):
    def __init__(self, ui: AxonUI):
        self._ui = ui


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
        provider_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def _tool_response_message(
        self,
        name: str,
        result: str,
        provider_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def _is_retryable_error(self, error: Exception) -> bool:
        raise NotImplementedError


    @abstractmethod
    def _is_invalid_api_key_error(self, error: Exception) -> bool:
        raise NotImplementedError


    @abstractmethod
    def _request_credential_validation(self) -> None:
        raise NotImplementedError


    @abstractmethod
    async def count_tokens(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
    ) -> int:
        raise NotImplementedError


    @abstractmethod
    async def generate_text(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        raise NotImplementedError


    @abstractmethod
    def generate_text_stream(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
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
    async def generate_with_tools(
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


    async def _execute_with_retries_async(
        self,
        api_func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        return await execute_with_retries_async(
            api_func=api_func,
            is_retryable_error=self._is_retryable_error,
            ui=self._ui,
            *args,
            **kwargs,
        )


    def _execute_with_retries(
        self,
        api_func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        return execute_with_retries(
            api_func=api_func,
            is_retryable_error=self._is_retryable_error,
            ui=self._ui,
            *args,
            **kwargs,
        )


    def _format_history(
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
                contents.append(self._tool_call_message(
                    item[LLM_CONTRACT.NAME],
                    item[LLM_CONTRACT.ARGS],
                    item.get(LLM_CONTRACT.PROVIDER_METADATA),
                ))
            elif item_type == LLM_CONTRACT.TOOL_RESPONSE:
                contents.append(self._tool_response_message(
                    item[LLM_CONTRACT.NAME],
                    item[LLM_CONTRACT.RESULT],
                    item.get(LLM_CONTRACT.PROVIDER_METADATA),
                ))
            else:
                raise ValueError(f"Unknown Axon history item type: {item_type}")

        return contents


    def validate_credentials(self) -> None:
        try:
            self._execute_with_retries(api_func=self._request_credential_validation)
        except Exception as e:
            if self._is_invalid_api_key_error(e):
                raise InvalidCredentialsError from e

            raise
