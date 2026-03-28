"""
Contains constants needed for python files within the src directory
"""
from docling.datamodel.base_models import DocItemLabel
import re
from pathlib import Path

# ------ Block Processing Constants ------

# Blocks under this count trigger an LLM review
MIN_WORD_COUNT_THRESHOLD = 15

MIN_CHAR_COUNT = 15

# Maximum characters per Groq API request
LLM_CURATION_BATCH_CHAR_LIMIT = 4000

LLM_CURATION_MODEL = "gemini-2.5-flash-lite"
LLM_CURATION_MODEL_TEMPERATURE = 0.0
GEM_API_KEY = "GEM_API_KEY"

HYPHEN_WRAP_PATTERN = re.compile(r'([A-Za-z]+)-\s*\n\s*([a-z]+)')
CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\n?|```')

# JSON flag from LLM indicating a block should be deleted
REMOVE_FLAG = 0

# ------ Path Constants ------
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "papers.db")

# ------ DB Constants ------
CHUNK_TABLE = "chunks"
VEC_TABLE = "vec"
PAPER_TABLE = "papers"
CHUNKS_MATCHED = 5
MAX_COS_DIST = 0.45

# ------ Semantic Chunker Constants ------
EMBEDDING_MODEL = "jinaai/jina-embeddings-v3"
MAX_JINA_TOKS = 4096
MAX_HEADER_CHARS = 250
MAX_HEADER_STACK_CHARS = 600
MIN_CHUNK_CHARS = 300
MAX_CHUNK_CHARS = 1500
EMBEDDING_DIM=1024
WS_RE = re.compile(r'.*(\s)')
MAX_QUERY_CHARS = 8000

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

The input contains text blocks marked with integer IDs (e.g., [BID: 12]).
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
Each block is separated by "=============".
[BID: <integer>]
<text content>

**ACTION REQUIRED:** Return a JSON object containing the array of BIDs you have identified as Noise under the key `noise_block_ids`. Do not include Signal IDs.
"""

CURATION_TOOL = {
    "type": "OBJECT",
    "properties": {
        "noise_block_ids": {
            "type": "ARRAY",
            "items": {"type": "INTEGER"},
            "description": "List of BIDs (Block IDs) that should be removed based on the curation criteria."
        }
    },
    "required": ["noise_block_ids"]
}

AXON_SYSTEM_PROMPT = """Your name is Axon. You are a versatile AI assistant with strong scientific and technical knowledge.

A RAG system may attach retrieved source excerpts to the prompt to help you answer the user's question.

Retrieved context format:
- <document> = one source or paper
- <chunk> = one retrieved excerpt from that source
- there may be multiple documents and multiple chunks
- chunks may be partial, overlapping, or contain fragmented prose, tables, captions, or headings

How to use retrieved context:
- Use the retrieved excerpts if they are helpful for answering the user's question.
- If the excerpts help only partially, combine them with your own knowledge.
- If the excerpts are irrelevant or insufficient, ignore them and answer from your own knowledge.
- Never tell the user you cannot answer just because the retrieved excerpts do not contain the answer.
- Never focus your reply on the existence or absence of retrieved excerpts unless the user explicitly asks about the source material.
- Always answer the # User Question directly.

Behavior rules:
- Always identify as Axon if asked your name.
- Do not mention document tags, chunk tags, IDs, retrieval systems, or hidden formatting.
- Do not invent study-specific details that are not supported by retrieved source text.
- Answer clearly, directly, and naturally.
- Lead with the answer.
"""

REWRITE_SYSTEM_PROMPT = """You rewrite conversational questions into standalone search queries for retrieval.

Your task is to take the user's latest question and recent chat history, and output one clear standalone search query.

RULES:
1. If the latest question is already clear and standalone, return it unchanged.
2. Use chat history only when needed to resolve references like 'it', 'they', 'this', 'that assay', 'the Abbott one', or similar vague follow-ups.
3. If the latest question starts a new topic or does not depend on the chat history, do not force a connection. Output the user's question unchanged.
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

# ------ Chat LLM Constants ------
LLM_CHAT_MODEL = "gemini-2.5-flash-lite"
LLM_REWRITE_MODEL = "gemini-2.5-flash-lite"
LLM_LARGE_CONTEXT_TOKS = 200000
LLM_MED_CONTEXT_TOKS = 100000
LLM_SMALL_CONTEXT_TOKS = 50000
LLM_CHAT_TEMP = 0.1
LLM_REWRITE_TEMP = 0.1
REWRITE_MESSAGES = 6
USER_HEADER = "# User Question"
NO_CHUNKS_TEXT = "No relevant excerpts were retrieved for this question."

# ------ Interface Constants ------
LOGO = """
⠀⠀⠀⣤⣤⣤⣤⣤⣤⣤⠀⠀⠀⢠⣤⣤⣤⣤⡀⠀⠀⣠⣤⣤⣤⣤⠀⠀⠀⢀⣀⣤⣤⣤⣄⣀⠀⠀⠀⠀⢠⣤⣤⣤⣄⠀⠀⢠⣤⣤⣤⣤
⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠘⣿⣿⣿⣿⣧⠀⢰⣿⣿⣿⣿⡏⠀⢀⣴⣿⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⢸⣿⣿⣿⣿⣆⠀⢸⣿⣿⣿⣿
⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠸⣿⣿⣿⣿⣆⣿⣿⣿⣿⡟⠀⠀⣾⣿⣿⣿⣿⡿⣿⣿⣿⣿⣿⡆⠀⢸⣿⣿⣿⣿⣿⡄⢸⣿⣿⣿⣿
⠀⢠⣿⣿⣿⣿⠹⣿⣿⣿⣿⡄⠀⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⢸⣿⣿⣿⣿⡏⠀⢸⣿⣿⣿⣿⣿⠀⢸⣿⣿⣿⣿⣿⣷⣸⣿⣿⣿⣿
⠀⢸⣿⣿⣿⣿⠀⣿⣿⣿⣿⣇⠀⠀⠀⢀⣼⣿⣿⣿⣿⣿⣧⡀⠀⠀⢸⣿⣿⣿⣿⡇⠀⠀⣿⣿⣿⣿⣿⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠀⣿⣿⣿⣿⣿⣤⣿⣿⣿⣿⣿⠀⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⢸⣿⣿⣿⣿⣇⠀⢰⣿⣿⣿⣿⣿⠀⢸⣿⣿⣿⣿⢹⣿⣿⣿⣿⣿⣿
⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⣼⣿⣿⣿⣿⠇⣿⣿⣿⣿⣿⡀⠘⣿⣿⣿⣿⣿⣶⣾⣿⣿⣿⣿⡏⠀⢸⣿⣿⣿⣿⠀⢻⣿⣿⣿⣿⣿
⣸⣿⣿⣿⣿⠋⠉⠙⣿⣿⣿⣿⣧⢠⣿⣿⣿⣿⡿⠀⢸⣿⣿⣿⣿⣇⠀⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⢸⣿⣿⣿⣿⠀⠈⣿⣿⣿⣿⣿
⠛⠻⠿⠿⠛⠀⠀⠀⠛⠿⠿⠿⠛⠸⠿⠿⠿⠿⠃⠀⠀⠻⠿⠿⠿⠿⠀⠀⠀⠙⠛⠻⠿⠿⠛⠋⠁⠀⠀⠀⠘⠛⠿⠿⠛⠀⠀⠘⠛⠿⠿⠟
"""
WELCOME_MESSAGE = "Good to see you — let's skip the reading and get straight to the facts"
MAIN_COLOUR_RICH = "cyan"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW =  "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"