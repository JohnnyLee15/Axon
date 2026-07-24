import logging
import os
import warnings


MODEL_LIBRARY_LOGGERS = (
    "torch",
    "transformers",
    "transformers_modules",
    "huggingface_hub",
    "tokenizers",
    "safetensors",
)

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

for logger_name in MODEL_LIBRARY_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL + 1)

warnings.filterwarnings(
    "ignore",
    module=(
        r"^(torch|transformers|transformers_modules|huggingface_hub|"
        r"tokenizers|safetensors)(\.|$)"
    ),
)


import torch
from huggingface_hub.utils import disable_progress_bars
from transformers import AutoModel, AutoTokenizer
from transformers.utils.logging import disable_progress_bar
from transformers.tokenization_utils_base import BatchEncoding

disable_progress_bars()
disable_progress_bar()

from axon.utils.device import get_dtype, get_torch_device

from .embedding_backend import EmbeddingBackend
from .context_buffer_tracker import ContextBufferTracker
from .models import Chunk


EMBEDDING_MODEL = "jinaai/jina-embeddings-v3-hf"
MAX_QUERY_TOKENS = 8192
MAX_CONTEXT_TOKENS = 2048
PASSAGE_EMBEDDING_TASK = "retrieval.passage"
QUERY_EMBEDDING_TASK = "retrieval.query"


class TorchEmbeddingBackend(EmbeddingBackend):
    def __init__(self) -> None:
        self._device = get_torch_device()
        self._model = AutoModel.from_pretrained(EMBEDDING_MODEL, dtype=get_dtype())
        self._model.to(self._device)
        self._model.eval()

        self._tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)


    def _count_tokens(self, text: str) -> int:
        tokens = self._tokenizer(
            text,
            return_attention_mask=False,
            return_token_type_ids=False,
        )
        return len(tokens["input_ids"])


    def _build_context_buffers(
        self,
        chunks: dict[int, Chunk]
    ) -> tuple[list[str], list[dict[int, tuple[int, int]]]]:
        tracker = ContextBufferTracker()
        for cid in sorted(chunks):
            chunk_text = chunks[cid].markdown
            separator = "\n\n" if len(tracker) else ""
            candidate_text = separator + chunk_text
            combined_text = tracker.get_curr_buffer() + candidate_text

            if self._count_tokens(combined_text) <= MAX_CONTEXT_TOKENS:
                tracker.add_chunk(candidate_text, cid)
            else:
                tracker.flush()
                tracker.add_chunk(chunk_text, cid)

        tracker.flush()
        return tracker.get_context_buffers(), tracker.get_char_map_list()


    def _encode_tokens(
        self,
        tokens: BatchEncoding,
        task: str
    ) -> torch.Tensor:
        token_ids = tokens["input_ids"].to(self._device)
        attention_mask = tokens["attention_mask"].to(self._device)

        with torch.no_grad():
            output = self._model(
                input_ids=token_ids,
                attention_mask=attention_mask,
                task=task
            )

        return output.last_hidden_state[0]


    def _encode_context(
        self,
        content: str,
    ) -> tuple[torch.Tensor, list[tuple[int, int]]]:
        tokens = self._tokenizer(
            content,
            return_tensors="pt",
            return_offsets_mapping=True,
        )

        raw_offsets = tokens["offset_mapping"][0].tolist()
        offsets = [(start, end) for start, end in raw_offsets]

        enriched_tokens = self._encode_tokens(tokens, PASSAGE_EMBEDDING_TASK)
        return enriched_tokens, offsets


    def _get_chunk_token_indices(
        self,
        map_start: int,
        map_end: int,
        offsets: list[tuple[int, int]],
        token_idx: int
    ) -> tuple[list[int], int]:
        token_indices = []

        while token_idx < len(offsets):
            token_start, token_end = offsets[token_idx]

            if token_start >= map_end:
                break

            is_special_token = (token_start == 0) and (token_end == 0)
            if not is_special_token and token_end > map_start:
                token_indices.append(token_idx)

            token_idx += 1

        next_token_idx = max(0, token_idx - 1)
        return token_indices, next_token_idx


    def _embed_content_chunks(
        self,
        context: str,
        char_map: dict[int, tuple[int, int]],
    ) -> tuple[list[int], list[torch.Tensor]]:
        enriched_tokens, offsets = self._encode_context(context)

        cids = []
        embeddings = []
        token_idx = 0

        for cid in sorted(char_map):
            map_start, map_end = char_map[cid]
            token_indices, token_idx = self._get_chunk_token_indices(
                map_start,
                map_end,
                offsets,
                token_idx
            )

            if not token_indices:
                raise ValueError(f"No embedding tokens found for chunk {cid}.")

            start_token = token_indices[0]
            end_token = token_indices[-1] + 1

            embedding = torch.mean(
                enriched_tokens[start_token:end_token, :],
                dim=0,
                dtype=torch.float32,
            )

            cids.append(cid)
            embeddings.append(embedding)

        return cids, embeddings


    def _assign_chunk_embeddings(
        self,
        chunks: dict[int, Chunk],
        chunk_ids: list[int],
        embeddings: list[torch.Tensor],
    ) -> None:
        if not embeddings:
            return

        embedding_values = torch.stack(embeddings, dim=0).cpu().tolist()

        for cid, embedding in zip(chunk_ids, embedding_values, strict=True):
            chunks[cid].embedding = embedding


    def _generate_chunk_embeddings(
        self,
        chunks: dict[int, Chunk],
        context_buffers: list[str],
        char_maps: list[dict[int, tuple[int, int]]]
    ) -> None:
        cids = []
        embeddings = []

        for context, char_map in zip(context_buffers, char_maps, strict=True):
            context_chunk_ids, context_embeddings = self._embed_content_chunks(
                context,
                char_map
            )
            cids.extend(context_chunk_ids)
            embeddings.extend(context_embeddings)

        self._assign_chunk_embeddings(chunks, cids, embeddings)


    def embed_chunks(self, chunks: dict[int, Chunk]) -> None:
        if not chunks:
            return

        context_buffers, char_maps = self._build_context_buffers(chunks)
        self._generate_chunk_embeddings(chunks, context_buffers, char_maps)


    def embed_query(self, query: str) -> list[float]:
        tokens = self._tokenizer(
            query,
            return_tensors="pt",
            max_length=MAX_QUERY_TOKENS,
            truncation=True
        )

        enriched_tokens = self._encode_tokens(
            tokens,
            QUERY_EMBEDDING_TASK,
        )

        embedding = torch.mean(
            enriched_tokens,
            dim=0,
            dtype=torch.float32,
        )

        return embedding.cpu().tolist()
