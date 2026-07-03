import os
from typing import Any
import json

from rich.console import Console
from google import genai
from google.genai import types

from .llm_adapter import LLMAdapter
from src.utils.api_utils import execute_with_retries
from src.utils.config import GEM_API_KEY, MAX_RETRIES

class GeminiAdapter(LLMAdapter):
    def __init__(self, console: Console) -> None:
        self._console = console
        self._client = genai.Client(api_key=os.getenv(GEM_API_KEY))


    def _generate_config(
        self,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        response_mime_type: str | None = None,
        response_schema: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
            tools=tools
        )


    def _extract_text(self, response: Any) -> str:
        text_parts = []

        for candidate in response.candidates or []:
            content = candidate.content
            if not content:
                continue

            for part in content.parts or []:
                text = getattr(part, "text", None)
                if text:
                    text_parts.append(text)

        return "\n".join(text_parts).strip()


    def count_tokens(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None
    ) -> int:
        if system_instruction:
            contents = [
                self.user_message(f"SYSTEM_INSTRUCTION:\n{system_instruction}")
            ] + contents

        response = execute_with_retries(
            api_func=self._client.models.count_tokens,
            console=self._console,
            num_retries=MAX_RETRIES,
            model=model,
            contents=contents,
        )

        return response.total_tokens


    def generate_text(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        temperature: float = 0.0
    ) -> str:
        response = execute_with_retries(
            api_func=self._client.models.generate_content,
            console=self._console,
            num_retries=MAX_RETRIES,
            model=model,
            contents=contents,
            config=self._generate_config(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )

        return (response.text or "").strip()


    def generate_json(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str,
        schema: dict[str, Any],
        temperature: float = 0.0
    ) -> dict[str, Any]:
        response = execute_with_retries(
            api_func=self._client.models.generate_content,
            console=self._console,
            num_retries=MAX_RETRIES,
            model=model,
            contents=contents,
            config=self._generate_config(
                system_instruction=system_instruction,
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )

        text = (response.text or "").strip()
        if not text:
            return {}

        return json.loads(text)


    def generate_with_tools(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        response = execute_with_retries(
            api_func=self._client.models.generate_content,
            console=self._console,
            num_retries=MAX_RETRIES,
            model=model,
            contents=contents,
            config=self._generate_config(
                system_instruction=system_instruction,
                temperature=temperature,
                tools=tools,
            ),
        )

        tool_calls = []
        for call in response.function_calls or []:
            tool_calls.append({
                "name": call.name,
                "args": dict(call.args)
            })

        return {
            "text": self._extract_text(response),
            "tool_calls": tool_calls,
            "raw": response
        }


    def user_message(self, text: str) -> dict[str, Any]:
        return {
            "role": "user",
            "parts": [{"text": text}],
        }


    def model_message(self, text: str) -> dict[str, Any]:
        return {
            "role": "model",
            "parts": [{"text": text}],
        }


    def tool_call_message(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {
            "role": "model",
            "parts": [{
                "function_call": {
                    "name": name,
                    "args": args,
                },
            }],
        }


    def tool_response_message(self, name: str, result: str) -> dict[str, Any]:
        return {
            "role": "user",
            "parts": [{
                "function_response": {
                    "name": name,
                    "response": {"result": result},
                },
            }],
        }
