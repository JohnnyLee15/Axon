from enum import Enum

class CommandKeys:
    SUBCOMMANDS = "subcommands"
    USAGE = "usage"
    DESC = "desc"
    ARGC = "argc"
    HANDLER = "handler"

COMMAND_KEYS = CommandKeys()

class CommandResult(Enum):
    EXIT = "exit"