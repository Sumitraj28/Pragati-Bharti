import json
import logging
import re
from typing import Any, List, Optional, Set, Tuple
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Document, Page, Question, QuestionStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI specialized in analyzing and structuring examination papers and questionnaires.\n"
    "Your goal is to accurately extract all questions and their corresponding options from the provided document text.\n"
    "The text is divided by page markers like [PAGE 1], [PAGE 2], etc.\n\n"
    "STRICT INSTRUCTIONS:\n"
    "1. Return ONLY a valid, raw JSON array of objects. Do NOT use markdown code blocks (no ```json or ```).\n"
    "2. Each object in the array MUST adhere to this exact schema:\n"
    "   {\n"
    "     \"question_number\": <int or null>,\n"
    "     \"question_text\": \"<exact question text>\",\n"
    "     \"options\": [<list of option strings, e.g. [\"(A) ...\", \"(B) ...\"] or null if not multiple choice>],\n"
    "     \"question_type\": \"<multiple_choice | subjective | true_false | fill_blank>\",\n"
    "     \"source_pages\": [<list of integers for pages where the question appeared, e.g. [1]>],\n"
    "     \"ambiguous\": <boolean, true if question boundary or number was unclear or incomplete, else false>\n"
    "   }\n"
    "3. Extract EVERY question faithfully without omitting any options."
)


def concatenate_pages_text(pages: List[Page]) -> str:
    """Concatenates raw_text from pages with [PAGE X] headers."""
    chunks = []
    for page in sorted(pages, key=lambda p: p.page_number):
        chunks.append(f"[PAGE {page.page_number}]\n{(page.raw_text or '').strip()}")
    return "\n\n".join(chunks)


def extract_questions_rule_based(text: str) -> List[dict]:
    """
    Fallback deterministic parser used when LLM API keys are unavailable,
    rate-limited, or in offline/testing environments.
    """
    questions = []
    current_page = 1

    # Split by pages
    page_sections = re.split(r"\[PAGE\s+(\d+)\]", text)
    # page_sections will be: ['', '1', 'page 1 text', '2', 'page 2 text']
    i = 1
    while i < len(page_sections):
        try:
            page_num = int(page_sections[i])
        except ValueError:
            page_num = 1
        page_text = page_sections[i + 1] if i + 1 < len(page_sections) else ""
        i += 2

        # Look for Question patterns: "Question 1:", "Q1.", "1.", etc.
        pattern = re.compile(
            r"(?:Question\s+(\d+)[:.]?|Q(\d+)[:.]?|^(\d+)[\).])\s*(.*?)(?=(?:Question\s+\d+[:.]?|Q\d+[:.]?|^\d+[\).])|\Z)",
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )

        matches = list(pattern.finditer(page_text))
        for m in matches:
            q_num_str = m.group(1) or m.group(2) or m.group(3)
            q_num = int(q_num_str) if q_num_str and q_num_str.isdigit() else None
            block = m.group(4).strip()

            # Separate options if present: e.g. (A), (B), (C), (D) or A), B), C)
            opt_pattern = re.compile(r"(\([A-Da-d]\)\s*[^()\n]+|[A-Da-d]\)\s*[^()\n]+)")
            opts = opt_pattern.findall(block)

            clean_opts = [o.strip() for o in opts if len(o.strip()) > 2]
            if clean_opts:
                # Remove options from question text
                first_opt_idx = block.find(clean_opts[0])
                q_text = block[:first_opt_idx].strip() if first_opt_idx > 0 else block
                q_type = "multiple_choice"
            else:
                clean_opts = None
                q_text = block
                q_type = "subjective"

            q_text = " ".join(q_text.split())  # normalize whitespace
            if q_text:
                questions.append({
                    "question_number": q_num,
                    "question_text": q_text,
                    "options": clean_opts,
                    "question_type": q_type,
                    "source_pages": [page_num],
                    "ambiguous": False,
                })

    return questions


def _call_llm_api(prompt_text: str, retry_message: Optional[str] = None) -> str:
    """Calls configured LLM provider via standard HTTP endpoint."""
    api_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY
    if not api_key or api_key in ["your_openai_api_key_here", "your_llm_api_key_here"]:
        raise ValueError("No active LLM API key configured.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract all questions from the following text:\n\n{prompt_text}"},
    ]
    if retry_message:
        messages.append({"role": "user", "content": retry_message})

    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.0,
    }

    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=45.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def call_llm_with_retry(prompt_text: str) -> List[dict]:
    """
    Calls the LLM to extract questions as a JSON array.
    Retries once on invalid JSON, or falls back to rule-based parser if no API key is provided.
    """
    raw_response = None
    try:
        raw_response = _call_llm_api(prompt_text)
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
    except Exception as first_err:
        logger.warning(f"First LLM attempt failed or returned invalid JSON ({first_err}). Attempting retry...")
        try:
            raw_response = _call_llm_api(
                prompt_text,
                retry_message="Your previous output was not valid JSON. Return ONLY the raw JSON array starting with '[' and ending with ']'.",
            )
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as retry_err:
            logger.warning(f"LLM API or parsing unavailable/failed ({retry_err}). Using deterministic fallback parser.")
            return extract_questions_rule_based(prompt_text)


def compute_confidence_score(
    q: dict,
    ocr_pages: Set[int],
) -> Tuple[float, QuestionStatus]:
    """
    Assigns initial confidence score using strict requirements:
    - 1.0 if text came from digital extraction AND question_number/options/text are all present
    - 0.7 if OCR was used OR options are missing
    - 0.4 if question_number is missing OR LLM flagged ambiguity
    - status = "needs_review" when confidence_score < 0.6, else "extracted"
    """
    q_num = q.get("question_number")
    q_text = (q.get("question_text") or "").strip()
    options = q.get("options")
    source_pages = q.get("source_pages") or []
    ambiguous = bool(q.get("ambiguous", False))

    ocr_used = any(p in ocr_pages for p in source_pages)

    if q_num is None or ambiguous:
        score = 0.4
    elif ocr_used or not options:
        score = 0.7
    elif (not ocr_used) and (q_num is not None) and options and q_text:
        score = 1.0
    else:
        score = 0.7

    status = QuestionStatus.NEEDS_REVIEW if score < 0.6 else QuestionStatus.EXTRACTED
    return score, status


def extract_and_store_questions(
    document: Document,
    pages: List[Page],
    ocr_pages: Set[int],
    db: Session,
) -> List[Question]:
    """
    Concatenates page text with [PAGE X] headers, invokes LLM extraction,
    scores confidence, and inserts Question rows into the database.
    """
    if not pages:
        logger.warning(f"No pages found for document id {document.id}")
        return []

    concatenated_text = concatenate_pages_text(pages)
    logger.info(f"Extracting questions from document {document.id} ({len(pages)} pages)...")

    parsed_questions = call_llm_with_retry(concatenated_text)
    logger.info(f"Parsed {len(parsed_questions)} questions for document id {document.id}")

    created_questions = []
    for q in parsed_questions:
        confidence, q_status = compute_confidence_score(q, ocr_pages)

        question_row = Question(
            document_id=document.id,
            question_number=q.get("question_number"),
            question_text=q.get("question_text") or "",
            options=q.get("options"),
            question_type=q.get("question_type") or "unknown",
            source_pages=q.get("source_pages") or [1],
            confidence_score=confidence,
            status=q_status,
        )
        db.add(question_row)
        created_questions.append(question_row)

    db.commit()
    for q_row in created_questions:
        db.refresh(q_row)

    return created_questions
