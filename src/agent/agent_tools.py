from src.ingestion.embedding_backend import EmbeddingBackend
from src.db.chunk_repository import ChunkRepository
from src.retrieval.reranker import Reranker
from src.utils.file_utils import get_path_relative_to_project_root

import os
import subprocess
import shlex
from pathlib import Path
import difflib


class AgentTools:
    def __init__(
        self,
        embedding_backend: EmbeddingBackend,
        chunk_repository: ChunkRepository,
        reranker: Reranker,
    ):
        self._embedding_backend = embedding_backend
        self._chunk_repository = chunk_repository
        self._reranker = reranker


    def _format_chunks(self, chunks: dict[int, dict[str, str | int]]) -> str | None:
        if not chunks:
            return None

        sorted_chunks = sorted(
            chunks.values(), key=lambda x: (x["paper_id"], x["chunk_index"])
        )

        curr_paper_id = None
        parts = []

        for chunk_data in sorted_chunks:
            paper_id = chunk_data["paper_id"]
            chunk_index = chunk_data["chunk_index"]
            markdown = chunk_data["text"]

            if paper_id != curr_paper_id:
                if curr_paper_id is not None:
                    parts.append("</document>")
                curr_paper_id = paper_id
                parts.append(f"<document id='{paper_id}'>")

            parts.append(f"<chunk id='{chunk_index}'>")
            parts.append(markdown)
            parts.append("</chunk>")

        parts.append("</document>")
        return "\n".join(parts)


    def search_for_chunks(
        self,
        query: str
    ) -> dict:
        embedding = self._embedding_backend.embed_query(query)
        chunks = self._chunk_repository.get_top_matches(query, embedding)
        best_chunks = self._reranker.rank_chunks(query, chunks)
        formatted_chunks = self._format_chunks(best_chunks)
        return {
            "content": formatted_chunks,
            "chunk_count": len(best_chunks),
            "doc_count": len(set(c["paper_id"] for c in best_chunks.values())),
            "raw_chunks": best_chunks
        }


    def _execute_bash_cd(self, cmd: str) -> str:
        try:
            parts = shlex.split(cmd)
            if len(parts) > 2:
                raise ValueError(f"cd: expected 0 or 1 arguments, received {len(parts) - 1}")

            path = parts[1] if len(parts) == 2 else "~"
            os.chdir(os.path.expanduser(path))
            return f"# Directory changed to {os.getcwd()}"

        except Exception as e:
            return str(e)


    def execute_bash_cmd(self, cmd: str) -> dict:
        cmd = cmd.strip()

        if not cmd:
            return {"content": "# No command provided."}

        if cmd == "cd" or cmd.startswith("cd "):
            return {"content": self._execute_bash_cd(cmd)}

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            output = result.stdout.strip()
            error = result.stderr.strip()
            content = []
            if output:
                content.append(output)
            if error:
                content.append(f"STDERR:\n{error}")

            if not content:
                if result.returncode == 0:
                    return {"content": "# Command executed successfully (no output)."}
                return {"content": f"# Command failed with exit code {result.returncode} (no output)."}

            content = "\n".join(content)

            if result.returncode != 0:
                content = f"Exit Code: {result.returncode}\n{content}"

            return {"content": content}

        except Exception as e:
            return {"content": str(e)}


    def create_file(self, path: str, content: str) -> dict:
        try:
            filepath = Path(path.strip()).expanduser().resolve()
            if filepath.exists():
                return {"content": f"# File already exists: {filepath}\nUse replace_in_file to modify existing files."}

            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            return {"content": f"# Successfully created {filepath}"}

        except Exception as e:
            return {"content": str(e)}


    def replace_in_file(self, path: str, old_str: str, new_str: str) -> dict:
        try:
            filepath = Path(path.strip()).expanduser().resolve()
            if not filepath.exists():
                return {"content": f"Error: The file \"{filepath}\" does not exist."}

            if old_str == new_str:
                return {
                    "content": (
                        f"Error: Could not edit \"{filepath}\" because old_str and new_str are identical.\n"
                        "The file was not modified."
                    )
                }

            file_content = filepath.read_text(encoding="utf-8")
            match_count = file_content.count(old_str)

            if match_count == 0:
                return {
                    "content": (
                        f"Error: Could not edit \"{filepath}\" because old_str was not found exactly in the file.\n"
                        "The file was not modified.\n"
                        "Please inspect the current file contents and try again with an exact old_str, including whitespace and indentation."
                    )
                }

            if match_count > 1:
                return {
                    "content": (
                        f"Error: Could not edit \"{filepath}\" because old_str appears {match_count} times in the file.\n"
                        "The file was not modified.\n"
                        "Please provide a larger unique old_str that identifies exactly one section to replace."
                    )
                }

            display_path = get_path_relative_to_project_root(filepath)
            new_content = file_content.replace(old_str, new_str)
            filepath.write_text(new_content, encoding="utf-8")
            diff = difflib.unified_diff(
                file_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{display_path}",
                tofile=f"b/{display_path}",
                n=3
            )
            diff_text = "".join(diff)

            return {
                "content": f"# Successfully edited {filepath}\n\n```diff\n{diff_text}\n```",
                "diff": diff_text
            }

        except Exception as e:
            return {"content": str(e)}


    def read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None
    ) -> dict:
        try:
            filepath = Path(path).expanduser().resolve()
            if not filepath.exists():
                return {"content": f"Error: The file \"{filepath}\" does not exist."}

            if filepath.is_dir():
                return {
                    "content": (
                        f"Error: \"{filepath}\" is a directory, not a file. "
                        f"Use execute_bash_cmd with \"ls -la {filepath}\" to see its contents."
                    )
                }

            file_contents = filepath.read_text(encoding="utf-8")
            lines = file_contents.splitlines()
            num_lines = len(lines)

            if start_line is None:
                start_line = 1

            if end_line is None:
                end_line = num_lines

            if num_lines == 0:
                return {"content": f"File \"{filepath}\" is empty.", "start_line": 1, "end_line": 0}

            if start_line < 1 or end_line < 1:
                return {"content": "Error: start_line and end_line must be 1-indexed line numbers. The first line is line 1."}

            if start_line > end_line:
                return {"content": f"Error: start_line={start_line} > end_line={end_line}. Try again and ensure start_line <= end_line."}

            if start_line > num_lines:
                return {
                    "content": (
                        f"Error: Cannot read from line {start_line} in \"{filepath}\" because "
                        f"the file only has {num_lines} lines."
                    )
                }

            end_line = min(end_line, num_lines)
            selected_lines = lines[start_line-1:end_line]
            line_num_spaces = len(str(end_line))
            llm_content = ""
            for i, line in enumerate(selected_lines, start=start_line):
                llm_content += f"{i:{line_num_spaces}} | {line}\n"

            return {"content": llm_content, "start_line": start_line, "end_line": end_line}

        except Exception as e:
            return {"content": str(e)}


    def insert_to_file(
        self,
        path: str,
        insert_text: str,
        insert_after_line: int | None = None
    ) -> dict:
        try:
            filepath = Path(path).expanduser().resolve()
            if not filepath.exists():
                return {"content": f"Error: The file \"{filepath}\" does not exist."}

            if not filepath.is_file():
                return {
                    "content": f"Error: Cannot insert into \"{filepath}\" because it is not a regular file."
                }

            if not insert_text:
                return {
                    "content": "Error: insert_text was not provided. Try again and provide non-empty insert_text."
                }

            file_contents = filepath.read_text(encoding="utf-8")
            lines = file_contents.splitlines(keepends=True)
            num_lines = len(lines)

            if insert_after_line is None:
                insert_after_line = num_lines

            if insert_after_line < 0:
                return {"content": (
                        "Error: insert_after_line must be a non-negative integer. "
                        "To insert at the beginning of the file use insert_after_line=0."
                    )
                }

            if insert_after_line > num_lines:
                return {
                    "content": (
                        f"Error: Cannot insert content after line {insert_after_line} in \"{filepath}\" because "
                        f"the file only has {num_lines} lines."
                    )
                }

            if not insert_text.endswith('\n'):
                insert_text += '\n'

            if insert_after_line == num_lines and num_lines > 0:
                if not lines[-1].endswith("\n"):
                    lines[-1] += "\n"

            lines.insert(insert_after_line, insert_text)
            new_content = "".join(lines)
            filepath.write_text(new_content, encoding="utf-8")

            display_path = get_path_relative_to_project_root(filepath)
            diff = difflib.unified_diff(
                file_contents.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{display_path}",
                tofile=f"b/{display_path}",
                n=3
            )
            diff_text = "".join(diff)

            return {
                "content": f"# Successfully inserted into {filepath}\n\n```diff\n{diff_text}\n```",
                "diff": diff_text
            }

        except Exception as e:
            return {"content": str(e)}
