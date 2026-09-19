import difflib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Answer, Document, DocumentRole, Page, Question

logger = logging.getLogger(__name__)


def detect_answer_key_content(text: str) -> bool:
    """
    Detects whether the given text contains answer-key content:
    - Look for headings like 'Answer Key', 'Answers', 'Solutions', 'Answer Sheet'.
    - Look for patterns of 'Q.No -> Answer', '1. (A)', 'Q1: B', etc.
    """
    if not text:
        return False

    # Heading check
    heading_pattern = r"(?i)\b(answer\s*keys?|answers?|solutions?|key\s*&\s*explanations?|answer\s*sheet|marking\s*scheme)\b"
    if re.search(heading_pattern, text):
        return True

    # Pattern check: 2 or more occurrences of numbered answers like "1. A", "Q2: B", "Q1. (A)", "3 -> C"
    pattern = r"(?:^|\n|\s)(?:Q(?:uestion)?\.?\s*\d+[\.\:\-\)]?|\b\d{1,3}\s*[\.\:\-\)])\s*(?:[A-Da-d]\b|\([A-Da-d]\)|Option\s+[A-Da-d])"
    matches = re.findall(pattern, text)
    if len(matches) >= 2:
        return True

    return False


def parse_answers_rule_based(text: str) -> List[Dict[str, Any]]:
    """
    Extracts answer items using structured regex patterns.
    Handles:
      - "1. (B) Paris"
      - "Q1: B"
      - "Question 2 -> 100°C"
      - "99. Photosynthesis produces glucose and oxygen"
      - Unnumbered lines in answer sections
    """
    answers = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Check if there is an "Answer Key" header, and focus on lines after it if present
    in_answer_section = False
    candidate_lines = []
    has_header = False

    for line in lines:
        if re.search(r"(?i)\b(answer\s*keys?|answers?|solutions?)\b", line):
            has_header = True
            in_answer_section = True
            continue
        if in_answer_section or not has_header:
            candidate_lines.append(line)

    if not candidate_lines:
        candidate_lines = lines

    # Regex for numbered answer: e.g. "Q1: (B) Paris", "1. B", "Q. 2 -> Option C", "99. Some answer text"
    numbered_regex = re.compile(
        r"^(?:Q(?:uestion)?\.?\s*(\d+)|\b(\d+)[\.\:\-\)]|\bAns(?:wer)?\.?\s*(\d+)[\.\:\-\)]?)\s*[\:\-\=\>]?\s*(.+)$",
        re.IGNORECASE,
    )

    for line in candidate_lines:
        match = numbered_regex.match(line)
        if match:
            q_num_str = match.group(1) or match.group(2) or match.group(3)
            q_num = int(q_num_str) if q_num_str else None
            ans_text = match.group(4).strip()
            answers.append(
                {
                    "question_number": q_num,
                    "raw_answer_text": ans_text,
                    "ambiguous": False,
                }
            )
        else:
            # Check for tabular or bulleted format like "- Option B" or "(A) 25m/s" without question number
            if line.startswith(("-", "*", "•")) or re.match(r"^\([A-Da-d]\)", line):
                cleaned = re.sub(r"^[\-\*\•\s]+", "", line).strip()
                if cleaned:
                    answers.append(
                        {
                            "question_number": None,
                            "raw_answer_text": cleaned,
                            "ambiguous": True,
                        }
                    )

    return answers


def parse_answers_with_llm(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Attempts to call LLM to parse answers from text into structured JSON.
    Returns None if LLM is unavailable or fails.
    """
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.strip() in ("", "placeholder", "test-key"):
        return None

    import urllib.request
    import urllib.error

    prompt = (
        "You are an expert exam parser. Detect and extract all answers from the following answer key text. "
        "Return ONLY a valid JSON array of objects with the following structure:\n"
        '[{"question_number": int or null, "raw_answer_text": string, "ambiguous": boolean}]\n\n'
        "Text to parse:\n"
        f"{text[:4000]}"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
    }
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }

    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            # Clean possible markdown wrapping
            content = re.sub(r"^```json\s*", "", content.strip())
            content = re.sub(r"```$", "", content.strip())
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
    except Exception as e:
        logger.warning(f"LLM answer parsing failed or skipped: {e}")

    return None


def calculate_text_similarity(str1: str, str2: str) -> float:
    """
    Computes text similarity using normalized character ratio and token overlap.
    """
    if not str1 or not str2:
        return 0.0

    s1 = str1.lower().strip()
    s2 = str2.lower().strip()

    # Direct substring / containment check
    if s1 in s2 or s2 in s1:
        return 0.9

    # Sequence matcher ratio
    seq_ratio = difflib.SequenceMatcher(None, s1, s2).ratio()

    # Token overlap (Jaccard similarity)
    tokens1 = set(re.findall(r"\w+", s1))
    tokens2 = set(re.findall(r"\w+", s2))
    if tokens1 and tokens2:
        jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)
    else:
        jaccard = 0.0

    return max(seq_ratio, jaccard)


def find_best_question_match(
    answer_item: Dict[str, Any], questions: List[Question]
) -> Tuple[Optional[Question], float, Optional[str]]:
    """
    Matches a parsed answer item against candidate questions:
    1. First tries matching by question_number.
    2. Falls back to text similarity across question text and options.
    Returns: (matched_question, confidence_score, reason)
    """
    ans_q_num = answer_item.get("question_number")
    ans_text = answer_item.get("raw_answer_text", "")
    is_ambiguous = answer_item.get("ambiguous", False)

    # 1. Match by question_number first
    if ans_q_num is not None:
        matching_q = next((q for q in questions if q.question_number == ans_q_num), None)
        if matching_q:
            confidence = 1.0 if not is_ambiguous else 0.8
            return matching_q, confidence, None
        else:
            # Question number specified but not found among questions. Check similarity fallback
            best_q = None
            best_sim = 0.0
            for q in questions:
                # Check against question text
                sim = calculate_text_similarity(ans_text, q.question_text)
                # Check against question options if available
                if q.options:
                    for opt in q.options:
                        opt_sim = calculate_text_similarity(ans_text, str(opt))
                        sim = max(sim, opt_sim)
                if sim > best_sim:
                    best_sim = sim
                    best_q = q

            if best_sim >= 0.70 and best_q is not None:
                return best_q, round(best_sim, 2), None
            else:
                reason = (
                    f"Question number {ans_q_num} not found in document questions, "
                    f"and maximum text similarity is below threshold ({best_sim:.2f} < 0.70)."
                )
                return None, round(best_sim, 2), reason

    # 2. If question_number is absent or ambiguous, fall back to text similarity
    best_q = None
    best_sim = 0.0
    for q in questions:
        sim = calculate_text_similarity(ans_text, q.question_text)
        if q.options:
            for opt in q.options:
                opt_sim = calculate_text_similarity(ans_text, str(opt))
                sim = max(sim, opt_sim)
        if sim > best_sim:
            best_sim = sim
            best_q = q

    if best_sim >= 0.70 and best_q is not None:
        return best_q, round(best_sim, 2), None
    else:
        reason = (
            f"Question number is absent/ambiguous, and maximum text similarity "
            f"to any question is below threshold ({best_sim:.2f} < 0.70)."
        )
        return None, round(best_sim, 2), reason


def match_and_store_answers(
    raw_answers: List[Dict[str, Any]],
    questions: List[Question],
    source_document_id: int,
    db: Session,
) -> List[Answer]:
    """
    Iterates through parsed answer items, matches them to questions,
    and inserts Answer rows with matched status and reason.
    """
    # Clear any previous answers for this source document to avoid duplicates
    db.query(Answer).filter(Answer.source_document_id == source_document_id).delete()
    db.commit()

    created_answers = []

    for item in raw_answers:
        raw_text = item.get("raw_answer_text", "")
        if not raw_text.strip():
            continue

        matched_q, confidence, reason = find_best_question_match(item, questions)

        if matched_q is not None:
            answer_row = Answer(
                question_id=matched_q.id,
                raw_answer_text=raw_text,
                matched=True,
                confidence_score=confidence,
                source_document_id=source_document_id,
                unmatched_reason=None,
            )
        else:
            answer_row = Answer(
                question_id=None,
                raw_answer_text=raw_text,
                matched=False,
                confidence_score=confidence,
                source_document_id=source_document_id,
                unmatched_reason=reason,
            )

        db.add(answer_row)
        created_answers.append(answer_row)

    db.commit()
    for ans in created_answers:
        db.refresh(ans)

    return created_answers


def process_answer_matching_for_document(document: Document, db: Session) -> List[Answer]:
    """
    Processes answer matching for a given document:
    1. Checks if the document itself contains an answer key.
    2. If the document belongs to a group, cross-matches with other documents in the same group.
    """
    # Collect all text from document pages
    pages = db.query(Page).filter(Page.document_id == document.id).order_by(Page.page_number.asc()).all()
    combined_text = "\n".join([p.raw_text or "" for p in pages])

    is_answer_key = detect_answer_key_content(combined_text)
    if is_answer_key and document.doc_role == DocumentRole.UNKNOWN:
        # Determine if document has primarily questions or answers
        doc_questions = db.query(Question).filter(Question.document_id == document.id).all()
        if len(doc_questions) == 0:
            document.doc_role = DocumentRole.ANSWER_KEY
            db.commit()

    created_answers = []

    # Case A: Separate Document in the same group
    if document.group_id:
        # Find sibling documents in the group
        sibling_docs = (
            db.query(Document)
            .filter(Document.group_id == document.group_id, Document.id != document.id)
            .all()
        )

        for sibling in sibling_docs:
            sibling_pages = (
                db.query(Page).filter(Page.document_id == sibling.id).order_by(Page.page_number.asc()).all()
            )
            sibling_text = "\n".join([p.raw_text or "" for p in sibling_pages])

            # If current document has answer key content, match its answers to sibling's questions
            if is_answer_key or document.doc_role == DocumentRole.ANSWER_KEY:
                sibling_questions = (
                    db.query(Question).filter(Question.document_id == sibling.id).all()
                )
                if sibling_questions:
                    parsed = parse_answers_with_llm(combined_text) or parse_answers_rule_based(combined_text)
                    if parsed:
                        ans_rows = match_and_store_answers(
                            parsed, sibling_questions, document.id, db
                        )
                        created_answers.extend(ans_rows)

            # If sibling has answer key content, match sibling's answers to current document's questions
            if detect_answer_key_content(sibling_text) or sibling.doc_role == DocumentRole.ANSWER_KEY:
                current_questions = (
                    db.query(Question).filter(Question.document_id == document.id).all()
                )
                if current_questions:
                    parsed = parse_answers_with_llm(sibling_text) or parse_answers_rule_based(sibling_text)
                    if parsed:
                        ans_rows = match_and_store_answers(
                            parsed, current_questions, sibling.id, db
                        )
                        created_answers.extend(ans_rows)

    # Case B: Answer key within the same document (only if not a dedicated separate answer key)
    if is_answer_key and (not document.group_id or document.doc_role != DocumentRole.ANSWER_KEY):
        doc_questions = db.query(Question).filter(Question.document_id == document.id).all()
        if doc_questions:
            parsed = parse_answers_with_llm(combined_text) or parse_answers_rule_based(combined_text)
            if parsed:
                ans_rows = match_and_store_answers(parsed, doc_questions, document.id, db)
                created_answers.extend(ans_rows)

    return created_answers


def match_answers_for_group(group_id: int, db: Session) -> List[Answer]:
    """
    Runs cross-document answer matching across all documents in a group.
    Useful when a document is added to an existing group.
    """
    docs = db.query(Document).filter(Document.group_id == group_id).all()
    created = []
    for doc in docs:
        res = process_answer_matching_for_document(doc, db)
        created.extend(res)
    return created
