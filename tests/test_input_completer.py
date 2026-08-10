import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from prompt_toolkit.completion import CompleteEvent, PathCompleter
from prompt_toolkit.document import Document

from axon.ui.input_completer import InputCompleter


class InputCompleterTests(unittest.TestCase):
    def _get_completions(
        self,
        completer: InputCompleter,
        text: str,
    ) -> list:
        document = Document(text=text, cursor_position=len(text))
        event = CompleteEvent(completion_requested=True)
        return list(completer.get_completions(document, event))


    def _create_completer(self, root: Path) -> InputCompleter:
        completer = InputCompleter({
            "/help": "Display help.",
            "/chat load": "Load a chat.",
            "/library load": "Load PDFs.",
        })
        completer._path_completer = PathCompleter(
            get_paths=lambda: [str(root)],
            expanduser=True,
            file_filter=lambda path: (
                Path(path).is_dir() or
                Path(path).suffix.lower() == ".pdf"
            ),
        )
        return completer


    def test_completes_commands_with_descriptions(self) -> None:
        completer = InputCompleter({"/help": "Display help."})

        completions = self._get_completions(completer, "/he")

        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, "/help")
        self.assertEqual(completions[0].display_meta_text, "Display help.")

    def test_library_load_completes_only_directories_and_pdf_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "papers").mkdir()
            (root / "paper.pdf").touch()
            (root / "notes.txt").touch()
            completer = self._create_completer(root)

            completions = self._get_completions(
                completer,
                "/library load pa",
            )

        displays = {completion.display_text for completion in completions}
        self.assertEqual(displays, {"paper.pdf", "papers/"})

        directory = next(
            completion
            for completion in completions
            if completion.display_text == "papers/"
        )
        self.assertEqual(directory.text, f"pers{os.path.sep}")

    def test_library_load_escapes_spaces_and_completes_inside_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            papers = root / "My Papers"
            papers.mkdir()
            (papers / "study.pdf").touch()
            completer = self._create_completer(root)

            directory_completions = self._get_completions(
                completer,
                "/library load My",
            )
            file_completions = self._get_completions(
                completer,
                "/library load My\\ Papers/st",
            )

        self.assertEqual(len(directory_completions), 1)
        self.assertEqual(
            directory_completions[0].text,
            f"\\ Papers{os.path.sep}",
        )
        self.assertEqual(len(file_completions), 1)
        self.assertEqual(file_completions[0].display_text, "study.pdf")
        self.assertEqual(file_completions[0].text, "udy.pdf")

    def test_unrelated_commands_do_not_show_path_completions(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "paper.pdf").touch()
            completer = self._create_completer(root)

            completions = self._get_completions(completer, "/chat load pa")

        self.assertEqual(completions, [])


if __name__ == "__main__":
    unittest.main()
