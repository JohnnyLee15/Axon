from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from axon.config.paths import MODEL_CACHE_DIR
from axon.ingestion.factory import (
    EMBEDDING_MODEL,
    create_embedding_backend,
    create_pdf_parser,
)
from axon.retrieval.factory import (
    MLX_RERANKER_MODEL,
    TORCH_RERANKER_MODEL,
    create_reranker,
)


def test_create_pdf_parser_downloads_required_docling_models() -> None:
    artifacts_path = Path("/models/docling")
    document_curator = object()
    metadata_extractor = object()
    ui = MagicMock()

    with (
        patch(
            "axon.ingestion.factory._docling_models_are_downloaded",
            return_value=False,
        ),
        patch(
            "axon.ingestion.factory.download_models",
            return_value=artifacts_path,
        ) as download,
        patch("axon.ingestion.factory.PdfParser") as parser_class,
    ):
        result = create_pdf_parser(
            document_curator=document_curator,
            metadata_extractor=metadata_extractor,
            ui=ui,
        )

    ui.wait.assert_called_once_with(
        label="Downloading Docling layout and TableFormer models"
    )
    download.assert_called_once_with(
        output_dir=MODEL_CACHE_DIR,
        progress=False,
        with_code_formula=False,
        with_picture_classifier=False,
        with_rapidocr=False,
    )
    parser_class.assert_called_once_with(
        document_curator=document_curator,
        metadata_extractor=metadata_extractor,
        artifacts_path=artifacts_path,
    )
    ui.success.assert_called_once_with(
        "Docling models downloaded successfully.",
        leading_blank=False,
    )
    assert result == parser_class.return_value


def test_create_embedding_backend_downloads_model_before_loading() -> None:
    model_path = Path("/models/embedding")
    ui = MagicMock()

    with (
        patch(
            "axon.ingestion.factory.is_model_downloaded",
            return_value=False,
        ),
        patch(
            "axon.ingestion.factory.ensure_model_downloaded",
            return_value=model_path,
        ) as download,
        patch("axon.ingestion.factory.TorchEmbeddingBackend") as backend_class,
    ):
        result = create_embedding_backend(ui)

    ui.wait.assert_called_once_with(
        label=f'Downloading model "{EMBEDDING_MODEL}"'
    )
    download.assert_called_once_with(EMBEDDING_MODEL)
    backend_class.assert_called_once_with(model_path=model_path)
    ui.success.assert_called_once_with(
        f'Model "{EMBEDDING_MODEL}" downloaded successfully.',
        leading_blank=False,
    )
    assert result == backend_class.return_value


def test_create_reranker_uses_mlx_model_on_mps() -> None:
    model_path = Path("/models/mlx-reranker")
    ui = MagicMock()

    with (
        patch(
            "axon.retrieval.factory.get_torch_device",
            return_value=SimpleNamespace(type="mps"),
        ),
        patch(
            "axon.retrieval.factory.is_model_downloaded",
            return_value=True,
        ),
        patch(
            "axon.retrieval.factory.ensure_model_downloaded",
            return_value=model_path,
        ) as download,
        patch("axon.retrieval.factory.MLXRerankerBackend") as backend_class,
        patch("axon.retrieval.factory.Reranker") as reranker_class,
    ):
        result = create_reranker(ui)

    ui.wait.assert_called_once_with(
        label=f'Loading model "{MLX_RERANKER_MODEL}"'
    )
    download.assert_called_once_with(MLX_RERANKER_MODEL)
    backend_class.assert_called_once_with(model_path=model_path)
    reranker_class.assert_called_once_with(backend_class.return_value)
    ui.success.assert_not_called()
    assert result == reranker_class.return_value


def test_create_reranker_uses_torch_model_on_non_mps_device() -> None:
    device = SimpleNamespace(type="cuda")
    model_path = Path("/models/torch-reranker")
    ui = MagicMock()

    with (
        patch(
            "axon.retrieval.factory.get_torch_device",
            return_value=device,
        ),
        patch(
            "axon.retrieval.factory.is_model_downloaded",
            return_value=False,
        ),
        patch(
            "axon.retrieval.factory.ensure_model_downloaded",
            return_value=model_path,
        ) as download,
        patch("axon.retrieval.factory.TorchRerankerBackend") as backend_class,
        patch("axon.retrieval.factory.Reranker") as reranker_class,
    ):
        result = create_reranker(ui)

    ui.wait.assert_called_once_with(
        label=f'Downloading model "{TORCH_RERANKER_MODEL}"'
    )
    download.assert_called_once_with(TORCH_RERANKER_MODEL)
    backend_class.assert_called_once_with(device=device, model_path=model_path)
    reranker_class.assert_called_once_with(backend_class.return_value)
    ui.success.assert_called_once_with(
        f'Model "{TORCH_RERANKER_MODEL}" downloaded successfully.',
        leading_blank=False,
    )
    assert result == reranker_class.return_value
