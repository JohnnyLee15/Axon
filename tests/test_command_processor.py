import unittest
from unittest.mock import Mock

from axon.commands.contracts import COMMAND_KEYS
from axon.commands.processor import CommandProcessor
from axon.commands.registry import COMMANDS


class CommandProcessorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._handler = Mock()
        self._ui = Mock()
        commands = {
            "library": {
                COMMAND_KEYS.SUBCOMMANDS: {
                    "load": {
                        COMMAND_KEYS.ARGC: 1,
                        COMMAND_KEYS.USAGE: "/library load <file path>",
                        COMMAND_KEYS.HANDLER: "load_pdfs",
                    }
                }
            }
        }
        self._processor = CommandProcessor(
            commands=commands,
            handlers={"load_pdfs": self._handler},
            ui=self._ui,
        )

    async def test_processes_shell_escaped_path_as_one_argument(self) -> None:
        await self._processor.process(
            r"/library load ~/Research\ Papers/paper.pdf"
        )

        self._handler.assert_called_once_with(
            "~/Research Papers/paper.pdf"
        )

    async def test_processes_quoted_path_as_one_argument(self) -> None:
        await self._processor.process(
            '/library load "~/Research Papers/paper.pdf"'
        )

        self._handler.assert_called_once_with(
            "~/Research Papers/paper.pdf"
        )

    async def test_chat_load_accepts_no_name_for_interactive_selection(self) -> None:
        handler = Mock()
        processor = CommandProcessor(
            commands=COMMANDS,
            handlers={"load_chat": handler},
            ui=self._ui,
        )

        await processor.process("/chat load")

        handler.assert_called_once_with()

    async def test_chat_delete_accepts_no_name_for_interactive_selection(self) -> None:
        handler = Mock()
        processor = CommandProcessor(
            commands=COMMANDS,
            handlers={"delete_chat": handler},
            ui=self._ui,
        )

        await processor.process("/chat delete")

        handler.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
