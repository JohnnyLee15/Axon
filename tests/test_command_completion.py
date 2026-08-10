import unittest

from axon.commands.completion import build_command_options
from axon.commands.contracts import COMMAND_KEYS
from axon.commands.registry import COMMANDS


class CommandCompletionTests(unittest.TestCase):
    def test_builds_base_and_subcommand_completions(self) -> None:
        command_options = build_command_options(COMMANDS)

        self.assertIn("/help", command_options)
        self.assertIn("/chat save", command_options)
        self.assertIn("/chat history", command_options)
        self.assertIn("/library clear", command_options)
        self.assertNotIn("/chat", command_options)
        self.assertNotIn("/library", command_options)
        self.assertEqual(
            command_options["/chat load"],
            "Selects and loads a saved chat, or loads one by name.",
        )

    def test_builds_one_option_for_every_registered_command(self) -> None:
        command_options = build_command_options(COMMANDS)
        expected_count = sum(
            len(command[COMMAND_KEYS.SUBCOMMANDS])
            if COMMAND_KEYS.SUBCOMMANDS in command
            else 1
            for command in COMMANDS.values()
        )

        self.assertEqual(len(command_options), expected_count)


if __name__ == "__main__":
    unittest.main()
