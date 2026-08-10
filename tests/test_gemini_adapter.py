import base64
import json
import unittest
from unittest.mock import AsyncMock, Mock

from google.genai import types
from google.genai.errors import APIError

from axon.llm.contracts import LLM_CONTRACT
from axon.llm.errors import InvalidCredentialsError
from axon.llm.gemini_adapter import (
    FUNCTION_CALL_ID_KEY,
    GEMINI_METADATA_KEY,
    THOUGHT_SIGNATURE_KEY,
    GeminiAdapter,
)
from axon.llm.history import tool_call, tool_response


class GeminiAdapterCredentialTests(unittest.TestCase):
    def setUp(self) -> None:
        self._adapter = object.__new__(GeminiAdapter)

    def test_recognizes_unauthorized_status_as_invalid_credentials(self) -> None:
        error = APIError(401, {})

        invalid = self._adapter._is_invalid_api_key_error(error)

        self.assertTrue(invalid)

    def test_recognizes_wrapped_invalid_api_key_reason(self) -> None:
        error = APIError(
            400,
            {
                "error": {
                    "details": [{"reason": "API_KEY_INVALID"}],
                },
            },
        )

        invalid = self._adapter._is_invalid_api_key_error(error)

        self.assertTrue(invalid)

    def test_rejects_unrelated_api_error(self) -> None:
        error = APIError(
            400,
            {
                "error": {
                    "details": [{"reason": "OTHER_REASON"}],
                },
            },
        )

        invalid = self._adapter._is_invalid_api_key_error(error)

        self.assertFalse(invalid)

    def test_validate_credentials_translates_provider_error(self) -> None:
        error = APIError(401, {})
        self._adapter._execute_with_retries = Mock(side_effect=error)

        with self.assertRaises(InvalidCredentialsError) as raised:
            self._adapter.validate_credentials()

        self.assertIs(raised.exception.__cause__, error)

    def test_validate_credentials_preserves_noncredential_error(self) -> None:
        error = RuntimeError("network unavailable")
        self._adapter._execute_with_retries = Mock(side_effect=error)

        with self.assertRaises(RuntimeError) as raised:
            self._adapter.validate_credentials()

        self.assertIs(raised.exception, error)


class GeminiAdapterGenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._adapter = object.__new__(GeminiAdapter)
        self._adapter._client = Mock()
        self._adapter._execute_with_retries_async = AsyncMock()
        self._adapter._execute_with_retries = Mock()

    async def test_count_tokens_uses_async_client(self) -> None:
        response = Mock(total_tokens=42)
        self._adapter._execute_with_retries_async.return_value = response

        result = await self._adapter.count_tokens(
            model="gemini-test",
            contents=[],
        )

        self.assertEqual(result, 42)
        self.assertIs(
            self._adapter._execute_with_retries_async.await_args.kwargs["api_func"],
            self._adapter._client.aio.models.count_tokens,
        )

    async def test_generate_text_uses_async_client(self) -> None:
        response = Mock(text="  response text  ")
        self._adapter._execute_with_retries_async.return_value = response

        result = await self._adapter.generate_text(
            model="gemini-test",
            contents=[],
        )

        self.assertEqual(result, "response text")
        self.assertIs(
            self._adapter._execute_with_retries_async.await_args.kwargs["api_func"],
            self._adapter._client.aio.models.generate_content,
        )

    async def test_generate_with_tools_uses_async_client(self) -> None:
        response = Mock(function_calls=[], candidates=[])
        self._adapter._execute_with_retries_async.return_value = response

        result = await self._adapter.generate_with_tools(
            model="gemini-test",
            contents=[],
        )

        self.assertEqual(result["tool_calls"], [])
        self.assertIs(
            self._adapter._execute_with_retries_async.await_args.kwargs["api_func"],
            self._adapter._client.aio.models.generate_content,
        )

    async def test_tool_metadata_survives_history_round_trip(self) -> None:
        signature = b"encrypted-thought-signature"
        call_id = "function-call-123"
        response = types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                function_call=types.FunctionCall(
                                    id=call_id,
                                    name="execute_shell_cmd",
                                    args={"cmd": "pwd"},
                                ),
                                thought_signature=signature,
                            )
                        ],
                    )
                )
            ]
        )
        self._adapter._execute_with_retries_async.return_value = response

        result = await self._adapter.generate_with_tools(
            model="gemini-test",
            contents=[],
        )

        extracted_call = result[LLM_CONTRACT.TOOL_CALLS][0]
        metadata = extracted_call[LLM_CONTRACT.PROVIDER_METADATA]
        gemini_metadata = metadata[GEMINI_METADATA_KEY]
        self.assertEqual(gemini_metadata[FUNCTION_CALL_ID_KEY], call_id)
        self.assertEqual(
            gemini_metadata[THOUGHT_SIGNATURE_KEY],
            base64.b64encode(signature).decode("ascii"),
        )

        history = [
            tool_call(
                extracted_call[LLM_CONTRACT.NAME],
                extracted_call[LLM_CONTRACT.ARGS],
                metadata,
            ),
            tool_response(
                extracted_call[LLM_CONTRACT.NAME],
                "command complete",
                metadata,
            ),
        ]
        json.dumps(history)
        formatted_history = self._adapter._format_history(history)

        call_part = formatted_history[0]["parts"][0]
        response_part = formatted_history[1]["parts"][0]
        self.assertEqual(call_part["thought_signature"], signature)
        self.assertEqual(call_part["function_call"]["id"], call_id)
        self.assertEqual(
            response_part["function_response"]["id"],
            call_id,
        )

    def test_generate_json_keeps_using_sync_client(self) -> None:
        response = Mock(text='{"answer": true}')
        self._adapter._execute_with_retries.return_value = response

        result = self._adapter.generate_json(
            model="gemini-test",
            contents=[],
            system_instruction="Return JSON",
            schema={},
        )

        self.assertEqual(result, {"answer": True})
        self.assertIs(
            self._adapter._execute_with_retries.call_args.kwargs["api_func"],
            self._adapter._client.models.generate_content,
        )


if __name__ == "__main__":
    unittest.main()
