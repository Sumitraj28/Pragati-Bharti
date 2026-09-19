from pathlib import Path
from PIL import Image
import pytest

from app.services.ocr import detect_and_correct_rotation, ocr_image
from app.db.models import Document, DocumentStatus, DocumentRole
from app.services.ocr import extract_pages_from_document


def test_ocr_scanned_sample_image():
    """Test OCR extraction on sample_docs/scanned_sample.png."""
    image_path = Path("sample_docs/scanned_sample.png")
    assert image_path.is_file(), "Sample scanned image must exist"

    img = Image.open(image_path)
    extracted_text = ocr_image(img)

    assert len(extracted_text) > 20
    # Check for expected terms from the sample
    assert any(term in extracted_text for term in ["Question", "car", "meters", "speed", "velocity"])


def test_pdf_page_extraction_digital():
    """Test PyMuPDF extraction on sample_docs/digital_sample.pdf."""
    pdf_path = Path("sample_docs/digital_sample.pdf")
    assert pdf_path.is_file(), "Sample digital PDF must exist"

    dummy_doc = Document(
        id=99999,
        owner_id=1,
        filename="digital_sample.pdf",
        file_type="application/pdf",
        storage_path=str(pdf_path),
        status=DocumentStatus.PENDING,
        doc_role=DocumentRole.UNKNOWN,
    )

    pages = extract_pages_from_document(dummy_doc)
    assert len(pages) == 1
    page = pages[0]
    assert page["page_number"] == 1
    assert "National Science Olympiad" in page["raw_text"]
    assert "Question 1" in page["raw_text"]
    assert Path(page["image_path"]).is_file()


def test_rotation_handler_does_not_crash():
    """Test detect_and_correct_rotation on an image without errors."""
    img = Image.new("RGB", (300, 200), color=(255, 255, 255))
    rotated = detect_and_correct_rotation(img)
    assert isinstance(rotated, Image.Image)
