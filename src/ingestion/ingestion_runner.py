import time
from pathlib import Path
import sqlite3

from src.db.paper_repository import PaperRepository
from src.db.chunk_repository import ChunkRepository
from src.db.min_hasher import MinHasher
from src.ui.axon_ui import AxonUI
from src.ui.formatters import emphasis

from .pdf_parser import PdfParser
from .models import ParsedDocument
from .semantic_chunker import SemanticChunker
from .embedding_backend import EmbeddingBackend


JACCARD_SIMILARITY_THRESHOLD = 0.84


class IngestionRunner:
    def __init__(
        self,
        parser: PdfParser,
        chunker: SemanticChunker,
        embedding_backend: EmbeddingBackend,
        chunk_repository: ChunkRepository,
        paper_repository: PaperRepository,
        minhasher: MinHasher,
        ui: AxonUI,
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedding_backend = embedding_backend
        self._chunk_repository = chunk_repository
        self._paper_repository = paper_repository
        self._minhasher = minhasher
        self._ui = ui


    def _format_time(self, start_time: float, end_time: float) -> str:
        elapsed_time = end_time - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        milliseconds = int((elapsed_time * 1000) % 1000)
        return f"{minutes:02d}m {seconds:02d}s {milliseconds:03d}ms"


    def _format_active_identifiers(self, parsed_doc: ParsedDocument) -> str:
        active_ids = []
        if parsed_doc.doi:
            active_ids.append(f"DOI: {parsed_doc.doi}")

        if parsed_doc.arxiv:
            active_ids.append(f"arXiv: {parsed_doc.arxiv}")

        if parsed_doc.pmcid:
            active_ids.append(f"PMCID: {parsed_doc.pmcid}")

        if parsed_doc.pmid:
            active_ids.append(f"PMID: {parsed_doc.pmid}")

        return  ", ".join(active_ids) if active_ids else "Unknown identifiers"


    def _get_pdf_filepaths(self, filepath: Path) -> list[Path]:
        pdf_files = []
        if filepath.is_file():
            pdf_files = [filepath] if filepath.suffix.lower() == ".pdf" else []
        elif filepath.is_dir():
            pdf_files = list(filepath.rglob("*.pdf"))

        if not pdf_files:
            self._ui.warning(f"No PDF files found at: \"{emphasis(filepath)}\".")

        return pdf_files


    def _get_filepath(self, filepath: str) -> Path | None:
        try:
            filepath = Path(filepath).expanduser().resolve()
        except Exception as e:
            self._ui.error(f"OS Error resolving path \"{emphasis(filepath)}\": {e}.")
            return None

        if not filepath.exists():
            self._ui.error(f"Path not found: \"{emphasis(filepath)}\".")
            return None

        return filepath


    def _compare_min_hashes(self, sig_bytes: bytes, lsh_cands: list[tuple[int, bytes]]) -> bool:
        for cand_pid, cand_sig_bytes in lsh_cands:
            jaccard_estimate = self._minhasher.estimate_jaccard(sig_bytes, cand_sig_bytes)
            if jaccard_estimate >= JACCARD_SIMILARITY_THRESHOLD:
                id_str = f"ID: {cand_pid}"
                similarity_str = f"Similarity: {jaccard_estimate:.3f}"
                self._ui.warning(
                    "Duplicate content detected "
                    f"({emphasis(id_str)}, {emphasis(similarity_str)}). Skipping."
                )
                return True

        return False


    def _is_eligible_for_processing(self, parsed_doc: ParsedDocument) -> bool:
        if not parsed_doc.full_raw_text:
            self._ui.warning("Could not extract valid text. Skipping.")
            return False

        if not (
            parsed_doc.doi or
            parsed_doc.arxiv or
            parsed_doc.pmcid or
            parsed_doc.pmid
        ):
            return True

        exists = self._paper_repository.metadata_exists(parsed_doc)

        if exists:
            id_str = self._format_active_identifiers(parsed_doc)
            self._ui.warning(f"Duplicate metadata detected ({emphasis(id_str)}). Skipping.")
            return False

        return True


    def _ingest_paper(self, parsed_doc: ParsedDocument) -> int | None:
        fingerprint = self._minhasher.create_fingerprint(parsed_doc.full_raw_text)
        if fingerprint is None:
            self._ui.warning("Document too short to fingerprint. Skipping.")
            return

        signature, band_hashes = fingerprint
        lsh_cands = self._paper_repository.get_lsh_candidates(band_hashes)
        is_duplicate = self._compare_min_hashes(signature, lsh_cands)
        if is_duplicate:
            return

        pid = self._paper_repository.insert_paper(parsed_doc, signature, band_hashes)
        return pid


    def _process_pdf(self, pdf_path: Path) -> int | None:
        parsed_doc = self._parser(pdf_path)
        can_process = self._is_eligible_for_processing(parsed_doc)
        if not can_process:
            return

        pid = self._ingest_paper(parsed_doc)
        if pid is None:
            return

        self._ui.progress("Generating semantic chunks and embeddings")
        chunks = self._chunker(parsed_doc.blocks_reg)
        self._embedding_backend.embed_chunks(chunks)
        self._ui.success(f"Successfully generated {emphasis(len(chunks))} chunks.")
        self._chunk_repository.insert_chunks(chunks, pid)

        return pid


    def _load_pdf(self, pdf_path: Path) -> None:
        self._ui.display_section(pdf_path.name)
        start_time = time.perf_counter()

        try:
            pid = self._process_pdf(pdf_path)
        except sqlite3.Error as e:
            self._ui.error(f"Database error ingesting \"{emphasis(pdf_path.name)}\": {e}")
            return

        if pid is None:
            return

        end_time = time.perf_counter()
        time_str = self._format_time(start_time, end_time)
        pid_str = f"ID: {pid}"
        self._ui.success(
            f"Paper ingested successfully ({emphasis(pid_str)}) in {emphasis(time_str)}."
        )


    def load_pdfs(self, filepath: str) -> None:
        filepath = self._get_filepath(filepath)
        if filepath is None:
            return

        pdf_files = self._get_pdf_filepaths(filepath)
        if not pdf_files:
            return

        num_pdf_files = f"{len(pdf_files)} PDF files"
        self._ui.progress(f"Starting Axon Ingestion Pipeline ({emphasis(num_pdf_files)}).")
        for pdf_path in pdf_files:
            self._load_pdf(pdf_path)
