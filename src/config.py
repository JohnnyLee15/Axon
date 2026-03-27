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

LLM_CURATION_MODEL = "llama-3.3-70b-versatile"
LLM_CURATION_MODEL_TEMPERATURE = 0.0
GROQ_API_KEY = "GROQ_API_KEY"

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
MAX_QUERY_CHARS = 1500

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
Analyze the provided blocks and use the provided tool to submit the IDs of the blocks that should be REMOVED (marked as noise).

### CRITERIA FOR CLASSIFICATION

**KEEP (Signal) - Do NOT submit these IDs:**
1. **Section Headers:** Any standard scientific header (e.g., "Abstract", "Introduction", "Results", "Methods", "Conclusion", "References", "Funding"). **CRITICAL: Do not remove headers.**
2. **Body Text:** Sentences or paragraphs that look like part of the scientific narrative (even if short).
3. **Figure/Table Captions:** Text describing a figure or table (e.g., "Figure 1: Correlation between...").
4. **Formulas/Data:** Mathematical equations or specific data points integral to the paper.

**REMOVE (Noise) - Submit these IDs via the tool:**
1. **Running Headers/Footers:** Journal names, page numbers (e.g., "Page 1 of 5"), dates, or repeated titles at the top/bottom of pages.
2. **Metadata artifacts:** "Downloaded from...", DOIs, URLs, "Copyright © 2024", "All rights reserved".
3. **Correspondence info:** Author emails, fax numbers, or address blocks (unless part of the main text body).
4. **Navigation garbage:** "Back to top", "Next page", or isolated random symbols.
5. **References/Bibliography:** The list of citations at the end of the paper. (Note: Keep the "References" header itself if you want to know where it starts, but remove the list items).

### INPUT FORMAT
Each block is separated by "=============".
[BID: <integer>]
<text content>

**ACTION REQUIRED:** Call the tool with the array of BIDs you have identified as Noise. Do not include Signal IDs.
"""

CURATION_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_noise_blocks",
        "description": "Submit the IDs of the text blocks that have been identified as noise.",
        "parameters": {
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
    }
}

AXON_SYSTEM_PROMPT = """You are Axon, an advanced scientific research assistant. Your job is to answer scientific and academic questions clearly, accurately, and accessibly.

You may be given retrieved literature excerpts in the following format:
- Each <document> block represents one paper or source.
- Each <chunk> block inside a document is one retrieved passage from that paper.
- A prompt may contain multiple documents, and each document may contain multiple chunks.
- Chunks may be incomplete, may overlap slightly, and may sometimes contain fragmented prose, tables, captions, or headings.

Treat these excerpts as your primary evidence.

Rules:
1. Do not mention document tags, chunk tags, document IDs, chunk IDs, retrieval systems, or hidden formatting in your answer. Answer naturally.
2. Use the provided excerpts as the main evidence for your answer. You may use general scientific knowledge for brief background, definitions, or interpretation, but do not invent study details that are not supported by the excerpts.
3. Synthesize chunks from the same document before drawing conclusions about that paper.
4. If multiple documents are provided, compare them carefully and keep their findings distinct unless the evidence clearly supports a shared conclusion.
5. Interpret incomplete or fragmented chunks cautiously. Do not over-interpret partial sentences, isolated values, or broken table fragments.
6. If the evidence is limited, mixed, or incomplete, say so clearly. Do not guess at sample sizes, methods, statistics, or conclusions that are not stated.
7. Explain technical material in clear, conversational language without losing scientific accuracy.
8. Focus on the main takeaway, the key supporting evidence, and the most important caveats or limitations.
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
LLM_CHAT_MODEL = "openai/gpt-oss-120b"
LLM_REWRITE_MODEL = "llama-3.1-8b-instant"
LLM_CHAT_MAX_TOKS = 128000
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
COLOUR = "cyan"