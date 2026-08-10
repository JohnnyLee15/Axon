import unittest
from unittest.mock import Mock

from axon.commands.contracts import COMMAND_KEYS
from axon.commands.processor import CommandProcessor


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


if __name__ == "__main__":
    unittest.main()
