from abc import ABC, abstractmethod
from typing import Any

from .contracts import LLM_CONTRACT


class LLMAdapter(ABC):
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


    @abstractmethod
    def format_tools(
        self,
        tools: list[dict[str, Any]] | None,
    ) -> Any:
        raise NotImplementedError


    @abstractmethod
    def user_message(self, text: str) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def model_message(self, text: str) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def tool_call_message(
        self,
        name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def tool_response_message(
        self,
        name: str,
        result: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


    def format_history(
        self,
        history: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        contents = []
        for item in history:
            item_type = item[LLM_CONTRACT.TYPE]

            if item_type == LLM_CONTRACT.USER_TEXT:
                contents.append(self.user_message(item[LLM_CONTRACT.TEXT]))
            elif item_type == LLM_CONTRACT.MODEL_TEXT:
                contents.append(self.model_message(item[LLM_CONTRACT.TEXT]))
            elif item_type == LLM_CONTRACT.TOOL_CALL:
                contents.append(self.tool_call_message(item[LLM_CONTRACT.NAME], item[LLM_CONTRACT.ARGS]))
            elif item_type == LLM_CONTRACT.TOOL_RESPONSE:
                contents.append(self.tool_response_message(item[LLM_CONTRACT.NAME], item[LLM_CONTRACT.RESULT]))
            else:
                raise ValueError(f"Unknown Axon history item type: {item_type}")

        return contents

