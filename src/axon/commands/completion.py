from typing import Any

from .contracts import COMMAND_KEYS


def build_command_options(commands: dict[str, Any]) -> dict[str, str]:
    command_options = {}

    for command, command_data in commands.items():
        if COMMAND_KEYS.SUBCOMMANDS not in command_data:
            command_options[f"/{command}"] = command_data[COMMAND_KEYS.DESC]
            continue

        for subcommand, subcommand_data in command_data[COMMAND_KEYS.SUBCOMMANDS].items():
            command_options[f"/{command} {subcommand}"] = subcommand_data[COMMAND_KEYS.DESC]

    return command_options
