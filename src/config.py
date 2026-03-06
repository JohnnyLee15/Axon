"""
Contains constants needed for python files within the src directory
"""
from docling.datamodel.base_models import DocItemLabel
import re

# ------ Block Processing Constants ------

# Blocks under this count trigger an LLM review
MIN_WORD_COUNT_THRESHOLD = 15

# Maximum characters per Groq API request
LLM_CURATION_BATCH_CHAR_LIMIT = 4000

LLM_CURATION_MODEL = "llama-3.3-70b-versatile"
LLM_CURATION_MODEL_TEMPERATURE = 0.0
GROQ_API_KEY = "GROQ_API_KEY"

HYPHEN_WRAP_PATTERN = re.compile(r'([A-Za-z]+)-\s*\n\s*([a-z]+)')
CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\n?|```')

# JSON flag from LLM indicating a block should be deleted
REMOVE_FLAG = 0

# ------ Semantic Chunker Constants ------
EMBEDDING_MODEL = "jinaai/jina-embeddings-v3"
MAX_JINA_LARGE_CHUNK_CHARS = 16000
MIN_SPACE_SPLIT_THRESHOLD_CHARS = 10000
MAX_HEADER_CHARS = 500
MIN_CHUNK_CHARS = 300
MAX_CHUNK_CHARS = 1500

# ------ Docling Parser Configurations ------

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
    re.compile(r'downloaded\s+from'),
    re.compile(r'https?://\S+'),
    re.compile(r'doi:?\s*10\.'),
    re.compile(r'vol(ume)?\.?\s*\d+'),
    re.compile(r'no\.?\s*\d+'),
    re.compile(r'pp\.?\s*\d+'),
    re.compile(r'©'),
    re.compile(r'copyright'),
    re.compile(r'all rights reserved'),
    re.compile(r'received\s+\d+'),
    re.compile(r'accepted\s+\d+'),
    re.compile(r'published\s+online'),
    re.compile(r'email:'),
    re.compile(r'correspondence:'),
    re.compile(r'issn\s+\d+'),
    re.compile(r'keywords\.'),
]

# ------ LLM Prompts ------

LLM_CURATION_PROMPT = """
You are a Data Curation Expert for a Scientific RAG (Retrieval-Augmented Generation) pipeline.
Your task is to classify text blocks extracted from PDF research papers as either "Signal" (Keep) or "Noise" (Remove).

The input contains text blocks marked with IDs (e.g., [BID: 12]).
You must output a JSON object mapping the BID to a binary flag:
- 1 (KEEP): Valid content.
- 0 (REMOVE): Fluff/Noise.

### CRITERIA FOR CLASSIFICATION

**MARK AS 1 (KEEP - Signal):**
1. **Section Headers:** Any standard scientific header (e.g., "Abstract", "Introduction", "Results", "Methods", "Conclusion", "References", "Funding"). **CRITICAL: Do not remove headers.**
2. **Body Text:** Sentences or paragraphs that look like part of the scientific narrative (even if short).
3. **Figure/Table Captions:** Text describing a figure or table (e.g., "Figure 1: Correlation between...").
4. **Formulas/Data:** Mathematical equations or specific data points integral to the paper.

**MARK AS 0 (REMOVE - Noise):**
1. **Running Headers/Footers:** Journal names, page numbers (e.g., "Page 1 of 5"), dates, or repeated titles at the top/bottom of pages.
2. **Metadata artifacts:** "Downloaded from...", DOIs, URLs, "Copyright © 2024", "All rights reserved".
3. **Correspondence info:** Author emails, fax numbers, or address blocks (unless part of the main text body).
4. **Navigation garbage:** "Back to top", "Next page", or isolated random symbols.
5. **References/Bibliography:** The list of citations at the end of the paper. (Note: Keep the "References" header itself if you want to know where it starts, but remove the list items).

### INPUT FORMAT
Each block is separated by "=============".
[BID: <integer>]
<text content>

### OUTPUT FORMAT
Return ONLY a valid JSON object. Do not include markdown formatting or explanations.
Example:
{
    "12": 0,
    "45": 1
}
"""