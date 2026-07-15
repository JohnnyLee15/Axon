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
