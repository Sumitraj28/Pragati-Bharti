import io
import logging
from pathlib import Path
from typing import List, Optional
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

from app.db.models import Document, Page
from app.storage.local_storage import save_file

logger = logging.getLogger(__name__)

# Threshold in characters: below this length, PDF page is treated as scanned/empty and OCR is invoked
TEXT_LENGTH_THRESHOLD = 30


def detect_and_correct_rotation(image: Image.Image) -> Image.Image:
    """
    Detects page orientation using pytesseract OSD (Orientation and Script Detection)
    and rotates the image to upright before OCR.
    """
    try:
        osd_data = pytesseract.image_to_osd(image)
        rotate_angle = 0
        for line in osd_data.splitlines():
            if "Rotate:" in line:
                rotate_angle = int(line.split(":")[1].strip())
                break

        if rotate_angle in [90, 180, 270]:
            logger.info(f"Detected rotation of {rotate_angle} degrees. Auto-rotating to upright orientation.")
            # PIL rotate rotates counter-clockwise; to undo a clockwise rotation of X, rotate by 360 - X
            return image.rotate(360 - rotate_angle, expand=True)
    except Exception as e:
        logger.debug(f"OSD rotation detection skipped or not applicable: {e}")

    return image


def ocr_image(image: Image.Image) -> str:
    """
    Performs orientation correction and OCR text extraction on a PIL Image.
    """
    corrected_img = detect_and_correct_rotation(image)
    text = pytesseract.image_to_string(corrected_img)
    return text.strip()


def extract_pages_from_document(document: Document) -> List[dict]:
    """
    Extracts text and renders images for each page of the document:
    - If PDF: splits pages with PyMuPDF (fitz), attempts direct text extraction.
      If text length is below TEXT_LENGTH_THRESHOLD, runs pytesseract OCR on the rendered page.
    - If Image (JPG/PNG): runs pytesseract OCR directly.
    Returns a list of dicts with page_number, raw_text, and image_path.
    """
    file_path = document.storage_path
    pages_data = []

    is_pdf = document.file_type == "application/pdf" or file_path.lower().endswith(".pdf")

    if is_pdf:
        logger.info(f"Processing PDF document id={document.id} at {file_path}")
        doc = fitz.open(file_path)
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]

            # 1. Direct text extraction attempt
            direct_text = page.get_text().strip()

            # 2. Render page to image (150 DPI for good OCR quality & reasonable size)
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            rendered_image_path = save_file(img_bytes, f"doc_{document.id}_page_{page_number}.png")

            # 3. If direct text is insufficient, fallback to pytesseract OCR
            if len(direct_text) >= TEXT_LENGTH_THRESHOLD:
                logger.info(f"Page {page_number}: Direct text extraction extracted {len(direct_text)} characters.")
                raw_text = direct_text
                is_ocr = False
            else:
                logger.info(f"Page {page_number}: Direct text empty or below threshold ({len(direct_text)} chars). Running OCR...")
                pil_img = Image.open(io.BytesIO(img_bytes))
                raw_text = ocr_image(pil_img)
                is_ocr = True
                logger.info(f"Page {page_number}: OCR extracted {len(raw_text)} characters.")

            pages_data.append({
                "page_number": page_number,
                "raw_text": raw_text,
                "image_path": rendered_image_path,
                "is_ocr": is_ocr,
            })
        doc.close()

    else:
        # Image file (JPG/PNG)
        logger.info(f"Processing image document id={document.id} at {file_path}")
        with open(file_path, "rb") as f:
            img_bytes = f.read()

        pil_img = Image.open(io.BytesIO(img_bytes))
        raw_text = ocr_image(pil_img)
        logger.info(f"Image document id={document.id}: OCR extracted {len(raw_text)} characters.")

        pages_data.append({
            "page_number": 1,
            "raw_text": raw_text,
            "image_path": file_path,
            "is_ocr": True,
        })

    return pages_data
