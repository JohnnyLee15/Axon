import unittest
from unittest.mock import Mock, patch

from axon import __main__ as entrypoint


class MainEntrypointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._ui = Mock()
        self._credentials = Mock()

    def _dependency_patches(self):
        return (
            patch.object(entrypoint, "initialize_axon_home"),
            patch.object(entrypoint, "CredentialStore", return_value=self._credentials),
            patch.object(entrypoint, "AxonUI", return_value=self._ui),
            patch.object(entrypoint, "SessionManager"),
        )

    def test_starts_session_after_successful_setup(self) -> None:
        adapter = Mock()
        initialize, credential_store, axon_ui, session_manager = (
            self._dependency_patches()
        )

        with (
            initialize,
            credential_store,
            axon_ui,
            session_manager as manager_class,
            patch.object(entrypoint, "setup_gemini", return_value=adapter),
        ):
            entrypoint.main()

        manager_class.assert_called_once_with(
            ui=self._ui,
            llm_adapter=adapter,
        )
        manager_class.return_value.run.assert_called_once_with()

    def test_exits_with_failure_when_setup_cannot_validate_credentials(self) -> None:
        initialize, credential_store, axon_ui, session_manager = (
            self._dependency_patches()
        )

        with (
            initialize,
            credential_store,
            axon_ui,
            session_manager,
            patch.object(entrypoint, "setup_gemini", return_value=None),
            self.assertRaises(SystemExit) as raised,
        ):
            entrypoint.main()

        self.assertEqual(raised.exception.code, 1)

    def test_exits_as_interrupted_when_user_cancels_setup(self) -> None:
        initialize, credential_store, axon_ui, session_manager = (
            self._dependency_patches()
        )

        with (
            initialize,
            credential_store,
            axon_ui,
            session_manager,
            patch.object(
                entrypoint,
                "setup_gemini",
                side_effect=KeyboardInterrupt,
            ),
            self.assertRaises(SystemExit) as raised,
        ):
            entrypoint.main()

        self.assertEqual(raised.exception.code, 130)
        self._ui.info.assert_called_once_with(
            "Gemini setup canceled. Axon was not started."
        )


if __name__ == "__main__":
    unittest.main()
