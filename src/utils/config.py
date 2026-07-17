"""
Contains constants needed for python files within the src directory
"""
from docling.datamodel.base_models import DocItemLabel
import re
from pathlib import Path
from dotenv import load_dotenv

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

