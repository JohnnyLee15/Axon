import os
from collections.abc import Iterable
from pathlib import Path

from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    PathCompleter,
    WordCompleter,
)
from prompt_toolkit.document import Document


LIBRARY_LOAD_PREFIX = "/library load "
ESCAPED_SPACE = r"\ "


def _is_library_path(path: str) -> bool:
    return os.path.isdir(path) or Path(path).suffix.lower() == ".pdf"


class InputCompleter(Completer):
    def __init__(self, command_options: dict[str, str]) -> None:
        self._command_completer = WordCompleter(
            list(command_options),
            sentence=True,
            meta_dict=command_options,
        )
        self._path_completer = PathCompleter(
            expanduser=True,
            file_filter=_is_library_path,
        )


    def _get_path_document(self, document: Document) -> Document:
        argument_text = document.text[len(LIBRARY_LOAD_PREFIX):]
        argument_cursor = document.cursor_position - len(LIBRARY_LOAD_PREFIX)

        text_before_cursor = argument_text[:argument_cursor].replace(
            ESCAPED_SPACE,
            " ",
        )
        text_after_cursor = argument_text[argument_cursor:].replace(
            ESCAPED_SPACE,
            " ",
        )

        return Document(
            text=text_before_cursor + text_after_cursor,
            cursor_position=len(text_before_cursor),
        )


    def _get_path_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        path_document = self._get_path_document(document)

        for completion in self._path_completer.get_completions(
            path_document,
            complete_event,
        ):
            completion_text = completion.text.replace(" ", ESCAPED_SPACE)
            if completion.display_text.endswith("/"):
                completion_text += os.path.sep

            yield Completion(
                text=completion_text,
                start_position=completion.start_position,
                display=completion.display,
                display_meta=completion.display_meta,
            )


    def is_path_input(self, document: Document) -> bool:
        return document.text_before_cursor.startswith(LIBRARY_LOAD_PREFIX)


    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        if self.is_path_input(document):
            yield from self._get_path_completions(document, complete_event)
            return

        yield from self._command_completer.get_completions(
            document,
            complete_event,
        )
