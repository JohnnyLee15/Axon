import base64
import json
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError

from axon.ui.axon_ui import AxonUI

from .llm_adapter import LLMAdapter
from .contracts import LLM_CONTRACT


RETRYABLE_STATUS_CODES = {429, 503}

INVALID_API_KEY_REASON = "API_KEY_INVALID"
UNAUTHORIZED_STATUS_CODE = 401

GEMINI_METADATA_KEY = "gemini"
FUNCTION_CALL_ID_KEY = "function_call_id"
THOUGHT_SIGNATURE_KEY = "thought_signature"


class GeminiAdapter(LLMAdapter):
    def __init__(self, ui: AxonUI, api_key: str) -> None:
        super().__init__(ui=ui)

        self._client = genai.Client(api_key=api_key)


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
            tools=tools,
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


    def _user_message(self, text: str) -> dict[str, Any]:
        return {
            "role": "user",
            "parts": [{"text": text}],
        }


    def _model_message(self, text: str) -> dict[str, Any]:
        return {
            "role": "model",
            "parts": [{"text": text}],
        }


    def _get_gemini_metadata(
        self,
        provider_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not provider_metadata:
            return {}

        metadata = provider_metadata.get(GEMINI_METADATA_KEY, {})
        return metadata if isinstance(metadata, dict) else {}


    def _tool_call_message(
        self,
        name: str,
        args: dict[str, Any],
        provider_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = self._get_gemini_metadata(provider_metadata)
        function_call = {
            "name": name,
            "args": args,
        }
        function_call_id = metadata.get(FUNCTION_CALL_ID_KEY)
        if function_call_id:
            function_call["id"] = function_call_id

        part = {"function_call": function_call}
        thought_signature = metadata.get(THOUGHT_SIGNATURE_KEY)
        if thought_signature:
            part["thought_signature"] = base64.b64decode(thought_signature)

        return {
            "role": "model",
            "parts": [part],
        }


    def _tool_response_message(
        self,
        name: str,
        result: str,
        provider_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = self._get_gemini_metadata(provider_metadata)
        function_response = {
            "name": name,
            "response": {"result": result},
        }
        function_call_id = metadata.get(FUNCTION_CALL_ID_KEY)
        if function_call_id:
            function_response["id"] = function_call_id

        return {
            "role": "user",
            "parts": [{"function_response": function_response}],
        }


    def _format_tools(
        self,
        tools: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]] | None:
        if not tools:
            return None

        return [{"function_declarations": tools}]


    def _is_retryable_error(self, error: Exception) -> bool:
        return (
            isinstance(error, APIError)
            and error.code in RETRYABLE_STATUS_CODES
        )


    def _is_invalid_api_key_error(self, error: Exception) -> bool:
        if not isinstance(error, APIError):
            return False

        if error.code == UNAUTHORIZED_STATUS_CODE:
            return True

        response_data = error.details
        if not isinstance(response_data, dict):
            return False

        error_data = response_data.get("error", response_data)
        if not isinstance(error_data, dict):
            return False

        details = error_data.get("details")
        if not isinstance(details, list):
            return False

        return any(
            isinstance(detail, dict)
            and detail.get("reason") == INVALID_API_KEY_REASON
            for detail in details
        )


    def _request_credential_validation(self) -> None:
        self._client.models.list(config={"page_size": 1})


    async def count_tokens(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
    ) -> int:
        contents = self._format_history(contents)
        if system_instruction:
            contents = [
                self._user_message(f"SYSTEM_INSTRUCTION:\n{system_instruction}")
            ] + contents

        response = await self._execute_with_retries_async(
            api_func=self._client.aio.models.count_tokens,
            model=model,
            contents=contents,
        )

        return response.total_tokens


    async def generate_text(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        response = await self._execute_with_retries_async(
            api_func=self._client.aio.models.generate_content,
            model=model,
            contents=self._format_history(contents),
            config=self._generate_config(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )

        return (response.text or "").strip()

    async def generate_text_stream(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        response_stream = await self._execute_with_retries_async(
            api_func=self._client.aio.models.generate_content_stream,
            model=model,
            contents=self._format_history(contents),
            config=self._generate_config(
                system_instruction=system_instruction,
                temperature=temperature,
            ),
        )

        async for response_chunk in response_stream:
            text = response_chunk.text
            if text:
                yield text


    def generate_json(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        response = self._execute_with_retries(
            api_func=self._client.models.generate_content,
            model=model,
            contents=self._format_history(contents),
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


    async def generate_with_tools(
        self,
        *,
        model: str,
        contents: list[dict[str, Any]],
        system_instruction: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        response = await self._execute_with_retries_async(
            api_func=self._client.aio.models.generate_content,
            model=model,
            contents=self._format_history(contents),
            config=self._generate_config(
                system_instruction=system_instruction,
                temperature=temperature,
                tools=self._format_tools(tools),
            ),
        )

        tool_calls = []
        for candidate in response.candidates or []:
            content = candidate.content
            if content is None:
                continue

            for part in content.parts or []:
                call = part.function_call
                if call is None or call.name is None:
                    continue

                gemini_metadata = {}
                if call.id:
                    gemini_metadata[FUNCTION_CALL_ID_KEY] = call.id
                if part.thought_signature:
                    gemini_metadata[THOUGHT_SIGNATURE_KEY] = (
                        base64.b64encode(part.thought_signature).decode("ascii")
                    )

                tool_call = {
                    LLM_CONTRACT.NAME: call.name,
                    LLM_CONTRACT.ARGS: dict(call.args or {}),
                }
                if gemini_metadata:
                    tool_call[LLM_CONTRACT.PROVIDER_METADATA] = {
                        GEMINI_METADATA_KEY: gemini_metadata,
                    }

                tool_calls.append(tool_call)

        return {
            LLM_CONTRACT.TEXT: self._extract_text(response),
            LLM_CONTRACT.TOOL_CALLS: tool_calls,
            LLM_CONTRACT.RAW: response,
        }
