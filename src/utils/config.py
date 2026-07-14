"""
Contains constants needed for python files within the src directory
"""
from docling.datamodel.base_models import DocItemLabel
import re
from pathlib import Path
from dotenv import load_dotenv

# ------ Block Processing Constants ------
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
PMCID_PATTERN = re.compile(r"\b(PMC\d+)\b", re.IGNORECASE)
PMCID_FILENAME_PATTERN = re.compile(r"^(PMC\d+)$", re.IGNORECASE)
PMID_PATTERN = re.compile(r"\bpmid\s*:?\s*(\d+)\b", re.IGNORECASE)
ARXIV_PATTERN = re.compile(
    r"\barxiv:\s*("
    r"(?:\d{4}\.\d{4,5}|[A-Za-z\-]+(?:\.[A-Za-z\-]+)?/\d{7})"
    r"(?:v\d+)?"
    r")\b",
    re.IGNORECASE,
)
ARXIV_FILENAME_PATTERN = re.compile(
    r"^(\d{4}\.\d{4,5}(?:v\d+)?)$",
    re.IGNORECASE,
)

# Blocks under this count trigger an LLM review
MIN_WORD_COUNT_THRESHOLD = 15
MIN_CHAR_COUNT = 15

# Maximum characters per Groq API request
LLM_CURATION_BATCH_CHAR_LIMIT = 4000

LLM_CURATION_MODEL = "gemini-2.5-flash-lite"
LLM_METADATA_MODEL = "gemini-2.5-flash-lite"
LLM_CURATION_MODEL_TEMPERATURE = 0.0
LLM_METADATA_MODEL_TEMPERATURE = 0.0
GEM_API_KEY = "GEM_API_KEY"

HYPHEN_WRAP_PATTERN = re.compile(r'([A-Za-z]+)-\s*\n\s*([a-z]+)')
CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\n?|```')

# JSON flag from LLM indicating a block should be deleted
REMOVE_FLAG = 0

# ------ Path Constants ------
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "papers.db")
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(ENV_PATH)

# ------ DB Constants ------
CHUNK_TABLE = "chunks"
VEC_TABLE = "vec"
PAPER_TABLE = "papers"
CHAT_TABLE = "chats"
LSH_TABLE = "lsh"
FTS_TABLE = "fts"
INITIAL_CHUNK_K = 20
REPLACE_WHITESPACE_WITH_SPACE = re.compile(r'\s+')

# ------ MinHasher Constants ------
LSH_BANDS = 16
LSH_ROWS = 16
NUM_MIN_HASH_FUNCS = LSH_BANDS * LSH_ROWS
MIN_HASH_SEED = 16
NUM_CHARS_PER_SHINGLE = 5
NORMALIZE_DOC_PATTERN = re.compile(r"[^a-z0-9]")

# ------ Semantic Chunker Constants ------
EMBEDDING_MODEL = "jinaai/jina-embeddings-v3-hf"
MAX_JINA_TOKS = 2048
MAX_HEADER_CHARS = 250
MAX_HEADER_STACK_CHARS = 600
MIN_CHUNK_CHARS = 300
MAX_CHUNK_CHARS = 1500
EMBEDDING_DIM=1024
WS_RE = re.compile(r'.*(\s)')
MAX_EMBEDDING_TOKS = 8192

# ------ Docling Parser Configurations ------
REFERENCE_HEADERS = [
    "references",
    "bibliography",
    "literature cited",
    "works cited",
    "citations",
    "reference list",
    "selected bibliography"
]

# ------ ReRanker Constants ------
MLX_RERANKER = "jinaai/jina-reranker-v3-mlx"
PYTORCH_RERANKER = "jinaai/jina-reranker-v3"
RERANK_BATCH_SIZE = 10
FINAL_CHUNK_K = 5
MIN_RERANK_SCORE = 0.20

EXCLUDED_DOCLING_LABELS = {
    DocItemLabel.PAGE_HEADER,
    DocItemLabel.PAGE_FOOTER,
    DocItemLabel.DOCUMENT_INDEX,
    DocItemLabel.CHECKBOX_SELECTED,
    DocItemLabel.CHECKBOX_UNSELECTED,
    DocItemLabel.FORM,
    DocItemLabel.GRADING_SCALE,
    DocItemLabel.HANDWRITTEN_TEXT,
    DocItemLabel.REFERENCE,
    DocItemLabel.PICTURE
}

SCIENTIFIC_HEADERS = {
    "abstract", "introduction", "background", "objectives", "aims",
    "methods", "methodology", "materials and methods",
    "experimental procedures", "study design", "results", "findings",
    "discussion", "conclusion", "conclusions", "summary"
}

NOISE_REGEX_PATTERNS = [
    # --- URLs & Identifiers ---
    re.compile(r'https?://\S+', re.IGNORECASE),
    re.compile(r'doi:?\s*10\.', re.IGNORECASE),
    re.compile(r'orcid\.org', re.IGNORECASE),
    re.compile(r'issn\s+\d+', re.IGNORECASE),

    # --- Copyright & Licensing ---
    re.compile(r'©', re.IGNORECASE),
    re.compile(r'copyright', re.IGNORECASE),
    re.compile(r'all rights reserved', re.IGNORECASE),
    re.compile(r'open access', re.IGNORECASE),
    re.compile(r'creative commons', re.IGNORECASE),
    re.compile(r'cc\s+by(-\w+)?\b', re.IGNORECASE), # Catches CC BY, CC BY-NC, etc.

    # --- Publication History & Metadata ---
    re.compile(r'received\s+\d+', re.IGNORECASE),
    re.compile(r'revision\s+received', re.IGNORECASE),
    re.compile(r'accepted\s+\d+', re.IGNORECASE),
    re.compile(r'published\s+online', re.IGNORECASE),
    re.compile(r'available\s+online', re.IGNORECASE),
    re.compile(r'downloaded\s+from', re.IGNORECASE),

    # --- Volume/Issue/Page Formatting ---
    re.compile(r'vol(ume)?\.?\s*\d+', re.IGNORECASE),
    re.compile(r'no\.?\s*\d+', re.IGNORECASE),
    re.compile(r'pp\.?\s*\d+', re.IGNORECASE),
    re.compile(r'page\s+\d+\s+of\s+\d+', re.IGNORECASE),

    # --- Author Info & Disclaimers ---
    re.compile(r'email:', re.IGNORECASE),
    re.compile(r'correspondence:', re.IGNORECASE),
    re.compile(r'conflict(s)? of interest', re.IGNORECASE),
    re.compile(r'competing interest(s)?', re.IGNORECASE),

    # --- Document Types & Headers ---
    re.compile(r'original\s+article', re.IGNORECASE),
    re.compile(r'research\s+article', re.IGNORECASE),
    re.compile(r'keywords\.', re.IGNORECASE),
]

# ------ LLM Prompts and Functions ------
LLM_CURATION_PROMPT = """You are a Data Curation Expert for a Scientific RAG (Retrieval-Augmented Generation) pipeline.
Your task is to classify text blocks extracted from PDF research papers as either "Signal" (Keep) or "Noise" (Remove).

The input contains text blocks wrapped in <block id="x"> tags, all enclosed within an <input_blocks> parent tag.
Analyze the provided blocks and identify the IDs of the blocks that should be REMOVED (marked as noise).

### CRITERIA FOR CLASSIFICATION

**KEEP (Signal) - Do NOT include these IDs in your response:**
1. **Section Headers:** Any standard scientific header (e.g., "Abstract", "Introduction", "Results", "Methods", "Conclusion", "References", "Funding"). **CRITICAL: Do not remove headers.**
2. **Body Text:** Sentences or paragraphs that look like part of the scientific narrative (even if short).
3. **Figure/Table Captions:** Text describing a figure or table (e.g., "Figure 1: Correlation between...").
4. **Formulas/Data:** Mathematical equations or specific data points integral to the paper.

**REMOVE (Noise) - Include these IDs in your response:**
1. **Running Headers/Footers:** Journal names, page numbers (e.g., "Page 1 of 5"), dates, or repeated titles at the top/bottom of pages.
2. **Metadata artifacts:** "Downloaded from...", DOIs, URLs, "Copyright © 2024", "All rights reserved".
3. **Correspondence info:** Author emails, fax numbers, or address blocks (unless part of the main text body).
4. **Navigation garbage:** "Back to top", "Next page", or isolated random symbols.
5. **References/Bibliography:** The list of citations at the end of the paper. (Note: Keep the "References" header itself if you want to know where it starts, but remove the list items).

### INPUT FORMAT
<input_blocks>
<block id='<integer>'>
<text content>
</block>
...
</input_blocks>

**ACTION REQUIRED:** Return a JSON object containing the array of BIDs you have identified as Noise under the key `noise_block_ids`. Do not include Signal IDs.
"""

CURATION_TOOL = {
    "type": "object",
    "properties": {
        "noise_block_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "List of BIDs (Block IDs) that should be removed based on the curation criteria."
        }
    },
    "required": ["noise_block_ids"]
}

TITLE_PROMPT = """Extract the main article title from the raw text of the FIRST PAGE of a scientific PDF.
The raw text will be provided inside <first_page_text> XML tags.

Return only the article title if it can be identified from the first page.

Extraction rules:
1. Extract the main article title only.
2. Do NOT return the journal name, running header, author names, affiliations, correspondence text, abstract heading, footer text, page numbers, dates, or section headings.
3. Reconstruct a multi-line title into one clean string with single spaces.
4. If the title cannot be confidently identified, return null.
5. Do not guess, infer, or fabricate anything.
6. Never return anything except the title field in the JSON response.
"""

TITLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Main article title, cleaned and reconstructed into one line",
            "nullable": True
        }
    },
    "required": ["title"]
}

AXON_SYSTEM_PROMPT = """Your name is Axon. You are a scientific and technical agentic assistant.

You help the user investigate papers, analyze data, reason through technical problems, write and modify code, inspect files, run commands, and complete multi-step tasks accurately and efficiently.

Capabilities:
- Answer scientific and technical questions clearly and directly.
- Analyze documents, papers, code, command output, and other tool results.
- Use available tools to inspect information, retrieve content, run commands, write or modify files, and complete multi-step tasks.
- Combine tool results with your own reasoning when appropriate.

Tool Use:
- You may have access to tools that let you inspect information, retrieve content, run commands, write or modify files, or take other actions.
- Use tools when they are genuinely needed to answer correctly, verify important details, inspect files, perform analysis, or complete the user's task.
- Do not use tools when a direct answer is sufficient.
- Prefer the least invasive tool that can accomplish the task.
- Before taking an action that modifies files, executes commands, or changes state, consider whether the action is necessary and aligned with the user's request.
- If tool results are useful, incorporate them naturally into your answer.
- If tool results are incomplete, empty, irrelevant, or erroring, recover when reasonable; otherwise continue with best-effort reasoning and be honest about the limitation.
- Do not mention internal tool names, raw tool payloads, hidden formatting, or implementation details unless the user explicitly asks.

Task Completion:
- While working on a multi-step task, use tools as needed without giving a final answer prematurely.
- After you have completed all necessary tool calls and no further tool is needed, provide a final answer to the user.
- Do not treat successful tool execution alone as task completion unless the user only asked you to perform an action and no explanation is needed.
- Do not return an empty response after using tools.
- If the task cannot be completed with the available tool results, explain what was done, what is missing, and give the best possible answer.

Tool Recovery:
- Treat tool failures, empty outputs, and unexpected results as diagnostic information, not final answers by themselves.
- When a tool result does not resolve the task, make a reasonable next attempt if there is a safe, obvious way to refine, broaden, or verify the action.
- For inspection tasks, gather enough context to avoid shallow conclusions.
- Prefer small, targeted follow-up actions over broad or risky ones.
- Do not repeatedly retry the same failed action without changing the approach.
- Ask the user only when the next step is ambiguous, risky, or requires information you cannot reasonably infer.

Grounding:
- You may receive information from retrieved excerpts, files, command output, generated analysis, or other tool results.
- Treat relevant tool outputs and retrieved material as evidence.
- If evidence is partial, narrow, or noisy, use the relevant parts and fill the rest with your own knowledge when appropriate.
- Do not invent source-specific facts that are not supported by the available evidence.
- If the user asks specifically about the source material or tool output, describe it faithfully.

Actions:
- If a task involves creating, modifying, or executing something, do so carefully and only as needed for the user's request.
- Favor correctness, clarity, and minimal unnecessary changes.
- When acting on files, code, or commands, stay aligned with the user's stated goal and avoid unrelated changes.

Response Rules:
- Always answer the user's actual question or complete the requested task directly.
- Lead with the answer or result.
- Be clear, natural, and concise.
- If the user asks a broad question and available evidence is narrow or off-topic, answer broadly from your own knowledge.
- Never refuse a question only because retrieved excerpts or tool outputs are missing, incomplete, or unrelated, unless the task genuinely requires missing information.
- Always identify as Axon if asked your name.

Retrieved context format, if present:
- <document> = one source
- <chunk> = one excerpt from that source
- there may be multiple documents and chunks
- excerpts may be partial, overlapping, or noisy
"""

REWRITE_SYSTEM_PROMPT = """You rewrite conversational questions into standalone search queries for retrieval.

Your task is to take the <user_question> and the <chat_history>, and output one clear standalone search query.

RULES:
1. If the <user_question> is already clear and standalone, return it unchanged.
2. Use the <chat_history> only when needed to resolve references like 'it', 'they', 'this', 'that assay', 'the Abbott one', or similar vague follow-ups.
3. If the <user_question> starts a new topic or does not depend on the history, do not force a connection. Output the <user_question> unchanged.
4. Preserve the user's original meaning, scope, and specificity.
5. Do not answer the question.
6. Do not explain your reasoning.
7. Do not refuse. Output only the rewritten search query.
8. Do not invent names, entities, or study details not supported by the latest question or history.
9. The final output must be 8000 characters or fewer.
10. If needed to stay within the limit, shorten only enough to preserve the user's original meaning, scope, and specificity.

Example 1:
History:
User: What is the Xpert HCV VL FS assay?
Assistant: It's a finger-stick viral load test.
User: How sensitive is it?
Output: What is the sensitivity of the Xpert HCV VL FS assay?

Example 2:
History:
User: How did the Xpert HCV Viral Load assay perform?
Assistant: It was compared with the Abbott RealTime HCV assay.
User: How does it compare to the Abbott one?
Output: How does the Xpert HCV Viral Load assay compare to the Abbott RealTime HCV assay?

Example 3:
History:
User: Tell me about HCV.
Assistant: ...
User: Can you tell me about cars?
Output: Can you tell me about cars?
"""

COMPACT_SYSTEM_PROMPT = """You are compressing a long chat history into a single self-contained memory summary that will replace the original conversation.

Your goal is to preserve everything important so a future assistant can continue the conversation with minimal loss of context.

Summarize the conversation into a dense but readable structured record.

Requirements:
1. Preserve concrete facts, decisions, conclusions, preferences, constraints, instructions, plans, and unresolved questions.
2. Preserve important technical context such as code architecture, class names, function names, variables, command behavior, database design ideas, file formats, and implementation decisions.
3. Preserve any user preferences about style, formatting, verbosity, coding style, naming, workflow, or output expectations.
4. Preserve task progress clearly: what has already been completed, what is partially done, what is planned next, and what was intentionally postponed.
5. Preserve references to any important files, documents, prompts, schemas, commands, or tools mentioned in the conversation.
6. Preserve important examples, edge cases, caveats, and tradeoffs that were discussed.
7. Separate confirmed decisions from tentative ideas or open questions.
8. Do not include filler, conversational pleasantries, or repetition.
9. Do not invent missing details. If something was uncertain, mark it as uncertain.
10. Write the summary so that someone who never saw the original chat can immediately understand the full working context.

Output format:
Return the summary using exactly these sections:

OVERVIEW
A concise description of the overall project or discussion.

USER GOALS
The user’s current goals and priorities.

IMPORTANT FACTS AND CONTEXT
Key factual background, assumptions, and constraints.

TECHNICAL STATE
Relevant architecture, code structure, data structures, commands, prompts, configuration, and implementation details.

DECISIONS MADE
Confirmed decisions and chosen approaches.

OPEN QUESTIONS / UNRESOLVED ITEMS
Anything still undecided, risky, blocked, or needing future work.

ACTIVE TASKS / NEXT STEPS
What should likely happen next.

USER PREFERENCES
Important preferences about writing, coding, formatting, workflow, or interaction style.

Be maximally information-dense while staying clear and organized.
"""

# ------ Chat LLM Constants ------
LLM_CHAT_MODEL_DEFAULT = "gemini-2.5-flash-lite"
LLM_REWRITE_MODEL = "gemini-2.5-flash-lite"
LLM_COMPACT_MODEL = "gemini-2.5-flash-lite"
LLM_CONTEXT_SIZE_DEFAULT = 10000
LLM_CHAT_TEMP = 0.1
LLM_REWRITE_TEMP = 0.1
LLM_COMPACT_TEMP = 0.0
REWRITE_MESSAGES = 6
MAX_ROLLING_MSGS = 10
LLMS = [
    {"id": "gemini-2.5-flash-lite", "label": "gemini-2.5-flash-lite (cheapest | quality #6)"},
    {"id": "gemini-2.5-flash", "label": "gemini-2.5-flash (low cost | quality #5)"},
    {"id": "gemini-3.1-flash-lite-preview", "label": "gemini-3.1-flash-lite-preview (budget | quality #4)"},
    {"id": "gemini-3-flash-preview", "label": "gemini-3-flash-preview (mid cost | quality #3)"},
    {"id": "gemini-2.5-pro", "label": "gemini-2.5-pro (high cost | quality #2)"},
    {"id": "gemini-3.1-pro-preview", "label": "gemini-3.1-pro-preview (most expensive | quality #1)"},
]
GEMINI_PROVIDER = "gemini"
MODEL_TO_PROVIDER = {
    "gemini-2.5-flash-lite": GEMINI_PROVIDER,
    "gemini-2.5-flash": GEMINI_PROVIDER,
    "gemini-3.1-flash-lite-preview": GEMINI_PROVIDER,
    "gemini-3-flash-preview": GEMINI_PROVIDER,
    "gemini-2.5-pro": GEMINI_PROVIDER,
    "gemini-3.1-pro-preview": GEMINI_PROVIDER,
}

# ------ API Constants ------
API_BUSY_ERROR_CODES = ["503", "429"]
MAX_RETRIES = 3


# ------ Agent Tools ------
SEARCH_FOR_CHUNKS = {
    "name": "search_for_chunks",
    "description": (
        "Search Axon's scientific paper database for relevant excerpts when you need more information to answer the user."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A standalone search query."
            }
        },
        "required": ["query"]
    }
}
EXECUTE_BASH_CMD = {
    "name": "execute_bash_cmd",
    "description": (
        "Execute a bash command exactly as it should be typed in a terminal. "
        "Do not add backslashes before ordinary single or double quotes unless the shell command itself requires them."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "cmd": {
                "type": "string",
                "description": "The exact bash command to execute as a raw, unescaped bash string."
            }
        },
        "required": ["cmd"]
    }
}
CREATE_FILE = {
    "name": "create_file",
    "description": (
        "Create a new file at the given path with the provided contents. "
        "Use this only for new files; use replace_in_file to modify existing files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path where the new file should be created."
            },
            "content": {
                "type": "string",
                "description": (
                    "The exact full contents to write into the new file. "
                    "Do not wrap the contents in markdown fences."
                )
            }
        },
        "required": ["path", "content"]
    }
}
REPLACE_IN_FILE = {
    "name": "replace_in_file",
    "description": (
        "Edit an existing file by replacing one exact text section with new text. "
        "Use this only for modifying existing files; use create_file for new files. "
        "When editing code, prefer replacing a complete syntactic block, such as "
        "an entire function, loop, or if/else block, rather than a tiny prefix that may leave overlapping code behind."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path of the file to edit."
            },
            "old_str": {
                "type": "string",
                "description": (
                    "The exact text currently in the file to replace. "
                    "It must match exactly, including whitespace and indentation, and appear only once."
                )
            },
            "new_str": {
                "type": "string",
                "description": (
                    "The exact replacement text. "
                    "Do not wrap the contents in markdown fences."
                )
            }
        },
        "required": ["path", "old_str", "new_str"]
    }
}
READ_FILE = {
    "name": "read_file",
    "description": (
        "Read the contents of a file. Returns the text with line numbers to help you navigate. "
        "You can optionally provide start_line and end_line to read a specific section of a file."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path of the file to read."
            },
            "start_line": {
                "type": "integer",
                "description": "Optional 1-indexed first line to read, inclusive. Defaults to 1."
            },
            "end_line": {
                "type": "integer",
                "description": "Optional 1-indexed last line to read, inclusive. Defaults to the end of the file."
            }
        },
        "required": ["path"]
    }
}
INSERT_TO_FILE = {
    "name": "insert_to_file",
    "description": (
        "Insert text into an existing file after a specific line number. "
        "Use read_file first if you need to see line numbers. "
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path of the file to edit."
            },
            "insert_text": {
                "type": "string",
                "description": (
                    "The exact text to insert. "
                    "Do not wrap the contents in markdown fences."
                )
            },
            "insert_after_line": {
                "type": "integer",
                "description": (
                    "Optional 1-indexed line number to insert after. "
                    "Use 0 to insert at the beginning. Defaults to the end of the file."
                )
            }
        },
        "required": ["path", "insert_text"]
    }
}
TOOL_SCHEMAS = [
    SEARCH_FOR_CHUNKS,
    EXECUTE_BASH_CMD,
    CREATE_FILE,
    REPLACE_IN_FILE,
    READ_FILE,
    INSERT_TO_FILE,
]