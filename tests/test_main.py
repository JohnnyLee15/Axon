import unittest
from unittest.mock import Mock, patch

from axon import __main__ as entrypoint


class MainEntrypointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._ui = Mock()
        self._credentials = Mock()
        self._settings = Mock()
        self._settings_store_patcher = patch.object(
            entrypoint,
            "SettingsStore",
            return_value=self._settings,
        )
        self._settings_store_patcher.start()
        self.addCleanup(self._settings_store_patcher.stop)

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
            settings=self._settings,
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

    def test_exits_as_interrupted_when_session_receives_keyboard_interrupt(self) -> None:
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
            self.assertRaises(SystemExit) as raised,
        ):
            manager_class.return_value.run.side_effect = KeyboardInterrupt
            entrypoint.main()

        self.assertEqual(raised.exception.code, 130)
        self._ui.display_goodbye.assert_called_once_with()

    def test_exits_cleanly_when_session_reaches_end_of_input(self) -> None:
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
            manager_class.return_value.run.side_effect = EOFError
            entrypoint.main()

        self._ui.display_goodbye.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
