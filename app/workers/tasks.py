from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import Document, DocumentStatus, Page
from app.services.ocr import extract_pages_from_document

logger = get_task_logger(__name__)


@celery_app.task(name="app.workers.tasks.process_document")
def process_document(document_id: int):
    """
    Extracts page-level text and renders page images for human review.
    Uses PyMuPDF for direct text extraction and pytesseract OCR fallback.
    Stores each page's result as a Page row (document_id, page_number, raw_text, image_path).
    Transitions Document.status to 'done' (or 'failed' on error).
    """
    logger.info(f"[Task process_document] Starting text extraction for document id: {document_id}")
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"[Task process_document] Document id {document_id} not found in database.")
            return {"error": "document_not_found", "document_id": document_id}

        document.status = DocumentStatus.PROCESSING
        db.commit()

        # Extract pages using PyMuPDF and pytesseract OCR
        pages_data = extract_pages_from_document(document)

        # Store each page as a Page database row
        for p in pages_data:
            page_row = Page(
                document_id=document.id,
                page_number=p["page_number"],
                raw_text=p["raw_text"],
                image_path=p["image_path"],
            )
            db.add(page_row)

        document.status = DocumentStatus.DONE
        db.commit()
        logger.info(
            f"[Task process_document] Document id {document_id} completed successfully. "
            f"{len(pages_data)} pages stored with status 'done'."
        )
        return {"status": "done", "document_id": document_id, "pages_count": len(pages_data)}

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
