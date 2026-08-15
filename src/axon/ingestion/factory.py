from docling.utils.model_downloader import download_models

from axon.config.model_store import ensure_model_downloaded, is_model_downloaded
from axon.config.paths import MODEL_CACHE_DIR
from axon.ui.axon_ui import AxonUI

from .document_curator import DocumentCurator
from .embedding_backend import EmbeddingBackend
from .metadata_extractor import MetadataExtractor
from .pdf_parser import PdfParser
from .torch_embedding_backend import TorchEmbeddingBackend


EMBEDDING_MODEL = "jinaai/jina-embeddings-v3-hf"
DOCLING_MODEL_DIRECTORIES = (
    "docling-project--docling-layout-heron",
    "docling-project--docling-models",
)


def _docling_models_are_downloaded() -> bool:
    return all(
        (MODEL_CACHE_DIR / directory).is_dir()
        and any((MODEL_CACHE_DIR / directory).iterdir())
        for directory in DOCLING_MODEL_DIRECTORIES
    )


def create_pdf_parser(
    document_curator: DocumentCurator,
    metadata_extractor: MetadataExtractor,
    ui: AxonUI,
) -> PdfParser:
    models_downloaded = _docling_models_are_downloaded()
    action = "Loading" if models_downloaded else "Downloading"

    with ui.wait(label=f"{action} Docling layout and TableFormer models"):
        artifacts_path = download_models(
            output_dir=MODEL_CACHE_DIR,
            progress=False,
            with_code_formula=False,
            with_picture_classifier=False,
            with_rapidocr=False,
        )

    if not models_downloaded:
        ui.success("Docling models downloaded successfully.", leading_blank=False)

    return PdfParser(
        document_curator=document_curator,
        metadata_extractor=metadata_extractor,
        artifacts_path=artifacts_path,
    )


def create_embedding_backend(ui: AxonUI) -> EmbeddingBackend:
    model_downloaded = is_model_downloaded(EMBEDDING_MODEL)
    action = "Loading" if model_downloaded else "Downloading"

    with ui.wait(label=f'{action} model "{EMBEDDING_MODEL}"'):
        model_path = ensure_model_downloaded(EMBEDDING_MODEL)
        backend = TorchEmbeddingBackend(model_path=model_path)

    if not model_downloaded:
        ui.success(
            f'Model "{EMBEDDING_MODEL}" downloaded successfully.',
            leading_blank=False,
        )

    return backend
