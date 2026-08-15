# Axon

Axon is a terminal AI agent for research, knowledge retrieval, and software development. The application runs locally and keeps its PDF library, embeddings, chat database, settings, and credentials on the user's machine while using a cloud-hosted LLM for generation and analysis. Axon can answer questions with cited local sources, search the web, and use shell and file tools with explicit user permission.

> Axon is currently pre-1.0. Gemini is the only supported LLM provider, and macOS on Apple silicon is the primary tested platform.

## Features

- Parse, clean, semantically chunk, embed, and index individual PDFs or entire directories.
- Combine BM25 full-text search and vector similarity search, then rerank results with a dedicated model.
- Detect duplicate papers using publication identifiers and MinHash/LSH similarity.
- Stream grounded answers with references to papers in the local library.
- Search the public web using Gemini’s built-in Google Search integration and display linked sources.
- Run an agent with library search, web search, shell, and file tools.
- Save, load, list, and delete conversations with creation and last-accessed timestamps.
- Persist prompt history, the selected model, and the context limit between launches.
- Provide command completion, path completion, selection menus, and interruptible model operations in a Rich terminal interface.

## Requirements

- pipx 1.12 or newer for a standard installation, or Python 3.12 or newer for development
- A [Gemini API key](https://aistudio.google.com/apikey)
- Internet access for Gemini requests and the initial Hugging Face model downloads
- Enough memory and disk space for the local embedding and reranking models

Axon automatically selects CUDA, Apple MPS, Intel XPU, or CPU where supported. CPU-only use is possible, but startup, ingestion, and retrieval can be substantially slower.

## Installation

### Install with pipx

[`pipx`](https://pipx.pypa.io/) installs Axon and its dependencies into an isolated environment while making the `axon` command available from any directory. First, follow the official [pipx installation guide](https://pipx.pypa.io/latest/how-to/install-pipx.html), then ensure its application directory is on your `PATH`:

```bash
pipx ensurepath
```

Open a new terminal, then install Axon:

```bash
pipx install --python 3.12 --fetch-python=missing "git+https://github.com/JohnnyLee15/Axon.git"
```

After installation, start Axon from any directory:

```bash
axon
```

If Python 3.12 is unavailable, pipx downloads it for Axon. pipx manages Axon's virtual environment automatically, so you can run `axon` from any directory without activating an environment yourself.

### Development install

```bash
git clone https://github.com/JohnnyLee15/Axon.git
cd Axon
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
axon
```

On the first launch, Axon validates and requests a Gemini API key. You can provide one ahead of time instead:

```bash
export GEMINI_API_KEY="your-api-key"
axon
```

The initial launch also downloads Docling's layout and table models, the Jina embedding model, and the platform-appropriate reranking model directly into `~/.axon/models/`. This may take several minutes depending on your internet connection. Subsequent launches reuse the downloaded models.

## Local data

By default, Axon creates `~/.axon` for its runtime data:

| Path | Contents |
| --- | --- |
| `~/.axon/.env` | Gemini API key entered during setup |
| `~/.axon/settings.json` | Selected model and chat context limit |
| `~/.axon/data/axon.db` | Papers, chunks, embeddings, and saved chats |
| `~/.axon/data/prompt_history` | Previously submitted prompts used for up and down arrow history |
| `~/.axon/models/` | Axon-managed document-processing, embedding, and reranking model weights |

No configuration is required to use the default location. If you prefer another location, set `AXON_HOME` before starting Axon:

```bash
export AXON_HOME="$HOME/custom-axon-home"
axon
```

Environment variables take precedence over values stored in Axon's `.env` file.

## Quick start

Start Axon from the directory you want its shell and file tools to treat as the current workspace:

```bash
cd ~/projects/my-project
axon
```

Then load one PDF or recursively load every PDF in a directory:

```text
/library load ~/papers/attention-is-all-you-need.pdf
/library load ~/papers
```

Ask a question normally to search the local paper library and receive a streamed answer with references:

```text
What are the main contributions of Attention Is All You Need?
```

Enable Agent Mode when Axon should choose and call tools:

```text
/agent
Find the latest follow-up work on sparse attention and compare it with papers in my library.
```

Use `Ctrl+J` to insert a newline. Press `Esc` when the interface shows an escape-to-cancel hint to interrupt the current model operation.

## Commands

| Command | Description |
| --- | --- |
| `/chat save <name> [-f]` | Save the current chat; use `-f` to overwrite an existing name. |
| `/chat load [name]` | Load a saved chat by name, or select one from a menu. |
| `/chat clear` | Clear the current in-memory chat history. |
| `/chat history` | Reprint the conversation history retained by Axon. |
| `/chat limit` | Select the chat context limit. |
| `/chat compact` | Replace the current history with an LLM-generated summary. |
| `/chat auto-compact` | Toggle automatic compaction when the context limit is exceeded. |
| `/chat list` | List saved chats and their timestamps. |
| `/chat delete [name \| -a]` | Delete a selected/named chat, or all chats with `-a`. |
| `/chat roll` | Toggle a rolling history of the latest five user/model pairs. |
| `/library load <path>` | Ingest a PDF or recursively ingest PDFs in a directory. |
| `/library clear` | Delete every indexed paper and chunk. |
| `/model` | Select the Gemini chat model. |
| `/agent` | Toggle Agent Mode. |
| `/clear` | Clear the terminal display without clearing chat history. |
| `/help` | Display the command menu. |
| `/exit` | Shut down Axon. |

## Agent tools and permissions

Agent Mode gives Gemini access to these tools:

- Local paper-library search
- Grounded web search
- Shell command execution
- File creation, reading, exact-text replacement, and line-based insertion

Before a tool runs, Axon asks whether to allow it once, trust that tool for the current Axon process, or deny it. Session trust is held only in memory and resets when Axon exits.

Shell and file tools are **not sandboxed**. They execute with the same filesystem access and operating-system permissions as the user running Axon. Review proposed commands and file operations carefully before approving them. Relative tool paths are resolved from the directory in which `axon` was started.

## Retrieval pipeline

```text
PDFs
  -> Docling parsing and structural cleanup
  -> Gemini-assisted metadata extraction and noise curation
  -> semantic chunking
  -> Jina v3 chunk embeddings
  -> SQLite FTS5 + sqlite-vec indexes

Question
  -> Gemini query rewrite
  -> BM25 + vector candidate retrieval
  -> Jina reranking
  -> Gemini answer generation
  -> local paper references
```

On Apple MPS devices, Axon uses the MLX version of Jina Reranker v3. Other supported devices use the Torch backend. Embeddings currently use Torch on every platform.

## Privacy and security

Axon keeps its SQLite library, saved chats, settings, and prompt history on the local machine. It is not fully offline:

- PDFs are parsed and embedded locally, but selected extracted text is sent to Gemini for metadata extraction and noise curation.
- Questions and relevant retrieved excerpts are sent to Gemini to generate answers.
- Web-search queries are sent to the Gemini API, which uses Google Search to retrieve current information and source links.
- An API key entered during setup is stored as plaintext in `~/.axon/.env`, created with user-only file permissions on supported systems.

Review these data flows and tool permissions before using Axon with confidential material.

## Project structure

```text
src/axon/
├── agent/          # Agent tool implementations and schemas
├── commands/       # Command registry, parsing, and completion
├── config/         # Runtime paths, credentials, and settings
├── db/             # SQLite schema and repositories
├── ingestion/      # PDF parsing, curation, chunking, and embeddings
├── llm/            # Provider adapter, history, prompts, and chat logic
├── retrieval/      # Torch/MLX reranking backends
├── session/        # Application wiring, runners, and command handlers
├── ui/             # Rich and prompt-toolkit terminal interface
└── web_search/     # Provider-independent web-search contract and Gemini backend
```

## Testing

From the repository root with the development environment active, run:

```bash
python -m pytest tests
```

Because Axon is pre-1.0, storage schemas and configuration formats may change without an automatic migration. The current PDF parser also has OCR disabled, so image-only scanned PDFs are not supported.

## License

Axon is licensed under the [Apache License 2.0](LICENSE).
