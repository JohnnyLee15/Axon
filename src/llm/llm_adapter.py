from abc import ABC, abstractmethod
from typing import Any


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
    def user_message(self, text: str) -> dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def model_message(self, text: str) -> dict[str, Any]:
        raise NotImplementedError


    def text_message(self, text: str) -> dict[str, Any]:
        return [self.user_message(text)]


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
