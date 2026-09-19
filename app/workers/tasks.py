import time
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import Document, DocumentStatus

logger = get_task_logger(__name__)


@celery_app.task(name="app.workers.tasks.process_document")
def process_document(document_id: int):
    """
    Placeholder task that simulates asynchronous document processing.
    Sleeps for 2 seconds, then updates Document.status to 'done'.
    """
    logger.info(f"[Task process_document] Starting background processing for document id: {document_id}")
    time.sleep(2)

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"[Task process_document] Document id {document_id} not found in database.")
            return {"error": "document_not_found", "document_id": document_id}

        document.status = DocumentStatus.DONE
        db.commit()
        logger.info(f"[Task process_document] Document id {document_id} marked as 'done'.")
        return {"status": "done", "document_id": document_id}
    except Exception as e:
        logger.exception(f"[Task process_document] Error processing document id {document_id}: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
