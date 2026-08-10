import inspect
import shlex
from typing import Any, Callable

from axon.ui.axon_ui import AxonUI
from axon.ui.formatters import emphasis

from .contracts import COMMAND_KEYS, CommandResult

BASE_CMD_IDX = 0
BASE_CMD_ARGS_START_IDX = 1
SUB_CMD_IDX = 1
SUB_CMD_ARGS_START_IDX = 2
CMD_START_CHAR = "/"


class CommandProcessor:
    def __init__(
        self,
        commands: dict[str, Any],
        handlers: dict[str, Callable],
        ui: AxonUI
    ) -> None:
        self._commands = commands
        self._handlers = handlers
        self._ui = ui


    def _resolve_subcommand(
        self,
        parts: list[str],
        cmd_data: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, list[str]]:
        if len(parts) <= SUB_CMD_IDX:
            return None, []

        sub = parts[SUB_CMD_IDX]
        subcommands = cmd_data[COMMAND_KEYS.SUBCOMMANDS]
        sub_cmd_data = subcommands.get(sub)
        if sub_cmd_data is None:
            return None, []

        return sub_cmd_data, parts[SUB_CMD_ARGS_START_IDX:]


    def _resolve_command(self, cmd: str) -> tuple[dict[str, Any] | None, list[str]]:
        try:
            parts = shlex.split(cmd.lstrip(CMD_START_CHAR))
        except ValueError:
            return None, []

        if not parts:
            return None, []

        base = parts[BASE_CMD_IDX]
        cmd_data = self._commands.get(base)
        if cmd_data is None:
            return None, []

        if COMMAND_KEYS.SUBCOMMANDS in cmd_data:
            return self._resolve_subcommand(parts, cmd_data)

        return cmd_data, parts[BASE_CMD_ARGS_START_IDX:]


    def _has_valid_arg_count(self, args: list[str], expected_argc: int | list[int]) -> bool:
        if isinstance(expected_argc, list):
            return len(args) in expected_argc

        return len(args) == expected_argc


    async def process(self, cmd: str) -> bool:
        cmd_data, args = self._resolve_command(cmd)

        if cmd_data is None:
            self._ui.unknown(
                f"Unknown command: {emphasis(cmd)}. "
                f"Type {emphasis('/help')} for a list of available commands."
            )
            return False

        if not self._has_valid_arg_count(args, cmd_data[COMMAND_KEYS.ARGC]):
            usage = cmd_data[COMMAND_KEYS.USAGE]
            self._ui.error(f"Invalid number of arguments. Usage: {emphasis(usage)}")
            return False


        handler_name = cmd_data[COMMAND_KEYS.HANDLER]
        result = self._handlers[handler_name](*args)

        if inspect.isawaitable(result):
            result = await result

        return result == CommandResult.EXIT
