from src.utils.config import *
from src.ingestion.semantic_chunker import SemanticChunker
from src.db.vector_database import VectorDatabase
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
        chunker: SemanticChunker,
        db: VectorDatabase,
        reranker: Reranker
    ):
        self._chunker = chunker
        self._db = db
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
        embedding = self._chunker.embed_query(query)
        chunks = self._db.top_chunk_matches(query, embedding)
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
            f"# Directory changed to {os.getcwd()}"

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
                return {"content": f"# File already exists: {filepath}\nUse edit_file to modify existing files."}

            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            return {"content": f"# Successfully created {filepath}"}

        except Exception as e:
            return {"content": str(e)}


    def edit_file(self, path: str, old_str: str, new_str: str) -> dict:
        try:
            filepath = Path(path.strip()).expanduser().resolve()
            if not filepath.exists():
                return {"content": f"Error: The file \"{filepath}\" does not exist."}

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


