from .contracts import COMMAND_KEYS
from .flags import OVERWRITE_CHAT_FLAG, DELETE_ALL_CHATS_FLAG

CHAT_COMMANDS = {
    "save": {
        COMMAND_KEYS.USAGE: f"/chat save <chat name> [{OVERWRITE_CHAT_FLAG}]",
        COMMAND_KEYS.DESC: f"Saves the current chat history to disk. use {OVERWRITE_CHAT_FLAG} to overwrite.",
        COMMAND_KEYS.ARGC: [1, 2],
        COMMAND_KEYS.HANDLER: "save_chat"
    },
    "load": {
        COMMAND_KEYS.USAGE: "/chat load [chat name]",
        COMMAND_KEYS.DESC: "Selects and loads a saved chat, or loads one by name.",
        COMMAND_KEYS.ARGC: [0, 1],
        COMMAND_KEYS.HANDLER: "load_chat"
    },
    "clear": {
        COMMAND_KEYS.USAGE: "/chat clear",
        COMMAND_KEYS.DESC: "Clears the current chat history.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "clear_chat"
    },
    "history": {
        COMMAND_KEYS.USAGE: "/chat history",
        COMMAND_KEYS.DESC: "Reprints the conversation history currently retained by Axon.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "display_history"
    },
    "limit": {
        COMMAND_KEYS.USAGE: "/chat limit",
        COMMAND_KEYS.DESC: "Sets the context window size.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "set_limit"
    },
    "compact": {
        COMMAND_KEYS.USAGE: "/chat compact",
        COMMAND_KEYS.DESC: "Replaces the current chat history with a condensed summary.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "compact"
    },
    "auto-compact": {
        COMMAND_KEYS.USAGE: "/chat auto-compact",
        COMMAND_KEYS.DESC: "Toggles automatic chat history summarization when the context limit is hit.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "auto_compact"
    },
    "list": {
        COMMAND_KEYS.USAGE: "/chat list",
        COMMAND_KEYS.DESC: "List all chats saved in the database.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "list_chats"
    },
    "delete": {
        COMMAND_KEYS.USAGE: f"/chat delete [chat name | {DELETE_ALL_CHATS_FLAG}]",
        COMMAND_KEYS.DESC: f"Selects and deletes a saved chat. Use {DELETE_ALL_CHATS_FLAG} to delete all chats.",
        COMMAND_KEYS.ARGC: [0, 1],
        COMMAND_KEYS.HANDLER: "delete_chat"
    },
    "roll": {
        COMMAND_KEYS.USAGE: "/chat roll",
        COMMAND_KEYS.DESC: "Toggles a rolling window that keeps the last 5 user-model chat pairs.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "chat_roll"
    }
}

LIBRARY_COMMANDS = {
    "load": {
        COMMAND_KEYS.USAGE: "/library load <file path>",
        COMMAND_KEYS.DESC: "Loads a file or folder (and subfolders) of PDFs into the database.",
        COMMAND_KEYS.ARGC: 1,
        COMMAND_KEYS.HANDLER: "load_pdfs"
    },
    "clear": {
        COMMAND_KEYS.USAGE: "/library clear",
        COMMAND_KEYS.DESC: "Removes all papers from the database.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "clear_library"
    }
}

COMMANDS = {
    "chat": {
        COMMAND_KEYS.SUBCOMMANDS: CHAT_COMMANDS
    },
    "library": {
        COMMAND_KEYS.SUBCOMMANDS: LIBRARY_COMMANDS
    },
    "clear": {
        COMMAND_KEYS.USAGE: "/clear",
        COMMAND_KEYS.DESC: "Clears the terminal screen.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "clear_screen"
    },
    "model": {
        COMMAND_KEYS.USAGE: "/model",
        COMMAND_KEYS.DESC: "Sets the chat LLM model.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "select_model"
    },
    "exit": {
        COMMAND_KEYS.USAGE: "/exit",
        COMMAND_KEYS.DESC: "Safely shuts down Axon and exits.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "exit"
    },
    "help": {
        COMMAND_KEYS.USAGE: "/help",
        COMMAND_KEYS.DESC: "Print a menu listing all available commands.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "help"
    },
    "agent": {
        COMMAND_KEYS.USAGE: "/agent",
        COMMAND_KEYS.DESC: "Toggles Agent Mode on/off for complex autonomous research.",
        COMMAND_KEYS.ARGC: 0,
        COMMAND_KEYS.HANDLER: "toggle_agent"
    }
}
