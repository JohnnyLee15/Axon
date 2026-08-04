import unittest
from unittest.mock import Mock

from google.genai.errors import APIError

from axon.llm.errors import InvalidCredentialsError
from axon.llm.gemini_adapter import GeminiAdapter


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


if __name__ == "__main__":
    unittest.main()
