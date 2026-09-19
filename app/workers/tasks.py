from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import Document, DocumentStatus, Page
from app.services.ocr import extract_pages_from_document
from app.services.extraction import extract_and_store_questions

logger = get_task_logger(__name__)


@celery_app.task(name="app.workers.tasks.process_document")
def process_document(document_id: int):
    """
    Extracts page-level text, renders page images, and performs question extraction.
    1. Extracts pages using PyMuPDF and pytesseract OCR fallback.
    2. Stores each page as a Page row (document_id, page_number, raw_text, image_path).
    3. Concatenates page text and calls LLM extraction to produce structured questions.
    4. Evaluates confidence scores and creates Question rows.
    5. Transitions Document.status to 'done' (or 'failed' on unhandled error).
    """
    logger.info(f"[Task process_document] Starting processing for document id: {document_id}")
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"[Task process_document] Document id {document_id} not found in database.")
            return {"error": "document_not_found", "document_id": document_id}

        document.status = DocumentStatus.PROCESSING
        db.commit()

        # Step 1: Extract pages using PyMuPDF and OCR fallback
        pages_data = extract_pages_from_document(document)

        saved_pages = []
        ocr_pages = set()
        for p in pages_data:
            if p.get("is_ocr"):
                ocr_pages.add(p["page_number"])

            page_row = Page(
                document_id=document.id,
                page_number=p["page_number"],
                raw_text=p["raw_text"],
                image_path=p["image_path"],
            )
            db.add(page_row)
            saved_pages.append(page_row)

        db.commit()
        for page_row in saved_pages:
            db.refresh(page_row)

        logger.info(
            f"[Task process_document] Saved {len(saved_pages)} pages for document id {document_id}. "
            f"Pages using OCR: {sorted(ocr_pages) if ocr_pages else 'None (all digital text)'}."
        )

        # Step 2: Extract and store questions using LLM
        created_questions = extract_and_store_questions(document, saved_pages, ocr_pages, db)
        logger.info(
            f"[Task process_document] Created {len(created_questions)} Question rows for document id {document_id}."
        )

        document.status = DocumentStatus.DONE
        db.commit()
        return {
            "status": "done",
            "document_id": document_id,
            "pages_count": len(saved_pages),
            "questions_count": len(created_questions),
        }

    except Exception as e:
        logger.exception(f"[Task process_document] Error processing document id {document_id}: {str(e)}")
        db.rollback()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = DocumentStatus.FAILED
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
