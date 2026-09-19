from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import Document, DocumentStatus, DocumentRole, Page
from app.services.ocr import extract_pages_from_document
from app.services.extraction import extract_and_store_questions
from app.services.answer_matcher import (
    process_answer_matching_for_document,
    detect_answer_key_content,
)

logger = get_task_logger(__name__)


@celery_app.task(name="app.workers.tasks.process_document")
def process_document(document_id: int):
    """
    Extracts page-level text, renders page images, performs question extraction,
    and detects & matches answer keys.
    1. Extracts pages using PyMuPDF and pytesseract OCR fallback.
    2. Stores each page as a Page row (document_id, page_number, raw_text, image_path).
    3. Concatenates page text and calls LLM extraction to produce structured questions.
    4. Evaluates confidence scores and creates Question rows.
    5. Detects answer key content and matches answers to questions.
    6. Transitions Document.status to 'done' (or 'failed' on unhandled error).
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

        # Step 2: Role detection & Question Extraction
        combined_text = "\n".join([p.raw_text or "" for p in saved_pages])
        is_answer_key_doc = (
            "answer" in document.filename.lower()
            or (detect_answer_key_content(combined_text) and combined_text.strip().lower().startswith(("answer", "solution", "key")))
        )

        if is_answer_key_doc and "question" not in document.filename.lower():
            document.doc_role = DocumentRole.ANSWER_KEY
            db.commit()
            created_questions = []
            logger.info(f"[Task process_document] Document id {document_id} categorized as ANSWER_KEY. Skipping question extraction.")
        else:
            document.doc_role = DocumentRole.QUESTION_PAPER
            db.commit()
            created_questions = extract_and_store_questions(document, saved_pages, ocr_pages, db)
            logger.info(
                f"[Task process_document] Created {len(created_questions)} Question rows for document id {document_id}."
            )

        # Step 3: Detect and match answer key content
        db.refresh(document)
        created_answers = process_answer_matching_for_document(document, db)
        logger.info(
            f"[Task process_document] Created {len(created_answers)} Answer rows for document id {document_id}."
        )

        document.status = DocumentStatus.DONE
        db.commit()
        return {
            "status": "done",
            "document_id": document_id,
            "pages_count": len(saved_pages),
            "questions_count": len(created_questions),
            "answers_count": len(created_answers),
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
