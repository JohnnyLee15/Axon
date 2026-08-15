import unittest
from unittest.mock import Mock, call, patch

from axon.llm.errors import InvalidCredentialsError
from axon.llm.provider_setup import setup_provider_api_key
from axon.llm.providers import (
    GEMINI_PROVIDER,
    PROVIDER_TO_API_KEY_ENV_VAR,
)


FACTORY_PATH = "axon.llm.provider_setup.create_llm_adapter"
GEMINI_API_KEY_ENV_VAR = PROVIDER_TO_API_KEY_ENV_VAR[GEMINI_PROVIDER]


class ProviderSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._ui = Mock()
        self._credentials = Mock()


    @patch(FACTORY_PATH)
    def test_returns_valid_stored_credential_without_prompting_or_saving(
        self,
        create_adapter: Mock,
    ) -> None:
        validation_adapter = Mock()
        self._credentials.get.return_value = "stored-key"
        create_adapter.return_value = validation_adapter

        result = setup_provider_api_key(
            GEMINI_PROVIDER,
            self._ui,
            self._credentials,
        )

        self.assertEqual(result, "stored-key")
        create_adapter.assert_called_once_with(
            provider=GEMINI_PROVIDER,
            ui=self._ui,
            api_key="stored-key",
        )
        self._ui.request_secret.assert_not_called()
        self._credentials.set.assert_not_called()


    @patch(FACTORY_PATH)
    def test_prompts_validates_and_saves_missing_credential(
        self,
        create_adapter: Mock,
    ) -> None:
        validation_adapter = Mock()
        self._credentials.get.return_value = None
        self._ui.request_secret.return_value = "  entered-key  "
        create_adapter.return_value = validation_adapter

        result = setup_provider_api_key(
            GEMINI_PROVIDER,
            self._ui,
            self._credentials,
        )

        self.assertEqual(result, "entered-key")
        create_adapter.assert_called_once_with(
            provider=GEMINI_PROVIDER,
            ui=self._ui,
            api_key="entered-key",
        )
        self._credentials.set.assert_called_once_with(
            key=GEMINI_API_KEY_ENV_VAR,
            value="entered-key",
        )


    @patch(FACTORY_PATH)
    def test_reprompts_after_stored_credential_is_rejected(
        self,
        create_adapter: Mock,
    ) -> None:
        rejected_adapter = Mock()
        rejected_adapter.validate_credentials.side_effect = (
            InvalidCredentialsError
        )
        valid_adapter = Mock()

        self._credentials.get.return_value = "rejected-key"
        self._ui.request_secret.return_value = "replacement-key"
        create_adapter.side_effect = [rejected_adapter, valid_adapter]

        result = setup_provider_api_key(
            GEMINI_PROVIDER,
            self._ui,
            self._credentials,
        )

        self.assertEqual(result, "replacement-key")
        self.assertEqual(
            create_adapter.call_args_list,
            [
                call(
                    provider=GEMINI_PROVIDER,
                    ui=self._ui,
                    api_key="rejected-key",
                ),
                call(
                    provider=GEMINI_PROVIDER,
                    ui=self._ui,
                    api_key="replacement-key",
                ),
            ],
        )
        self._ui.error.assert_called_once_with(
            "The Gemini API key is invalid."
        )
        self._credentials.set.assert_called_once_with(
            key=GEMINI_API_KEY_ENV_VAR,
            value="replacement-key",
        )


    @patch(FACTORY_PATH)
    def test_reprompts_when_entered_credential_is_empty(
        self,
        create_adapter: Mock,
    ) -> None:
        validation_adapter = Mock()
        self._credentials.get.return_value = None
        self._ui.request_secret.side_effect = ["   ", "valid-key"]
        create_adapter.return_value = validation_adapter

        result = setup_provider_api_key(
            GEMINI_PROVIDER,
            self._ui,
            self._credentials,
        )

        self.assertEqual(result, "valid-key")
        self.assertEqual(self._ui.request_secret.call_count, 2)
        self._ui.error.assert_called_once_with(
            "The Gemini API key cannot be empty."
        )
        create_adapter.assert_called_once_with(
            provider=GEMINI_PROVIDER,
            ui=self._ui,
            api_key="valid-key",
        )
        self._credentials.set.assert_called_once_with(
            key=GEMINI_API_KEY_ENV_VAR,
            value="valid-key",
        )


    @patch(FACTORY_PATH)
    def test_returns_none_when_validation_fails_for_unrelated_reason(
        self,
        create_adapter: Mock,
    ) -> None:
        validation_adapter = Mock()
        validation_adapter.validate_credentials.side_effect = RuntimeError(
            "service unavailable"
        )
        self._credentials.get.return_value = "stored-key"
        create_adapter.return_value = validation_adapter

        result = setup_provider_api_key(
            GEMINI_PROVIDER,
            self._ui,
            self._credentials,
        )

        self.assertIsNone(result)
        self._ui.error.assert_called_once_with(
            "Could not validate Gemini credentials: service unavailable."
        )
        self._credentials.set.assert_not_called()


    @patch(FACTORY_PATH)
    def test_returns_none_when_adapter_creation_fails(
        self,
        create_adapter: Mock,
    ) -> None:
        self._credentials.get.return_value = "stored-key"
        create_adapter.side_effect = RuntimeError("client creation failed")

        result = setup_provider_api_key(
            GEMINI_PROVIDER,
            self._ui,
            self._credentials,
        )

        self.assertIsNone(result)
        self._ui.error.assert_called_once_with(
            "Could not validate Gemini credentials: client creation failed."
        )
        self._credentials.set.assert_not_called()


    def test_rejects_provider_without_api_key_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported provider: unknown"):
            setup_provider_api_key(
                "unknown",
                self._ui,
                self._credentials,
            )


if __name__ == "__main__":
    unittest.main()
