# System Architecture & Technical Design

## 1. Overall Architecture Diagram

The **Document Intelligence Service** is architected as an asynchronous, event-driven microservice system composed of a client-facing REST API, an asynchronous distributed task queue, an in-memory message broker, a relational PostgreSQL database, and pluggable storage backends.

```mermaid
flowchart TD
    Client["HTTP Client / Browser (Swagger UI / Postman / Frontend)"]

    subgraph IngestionLayer["Ingestion & Security Layer"]
        API["FastAPI Gateway (Uvicorn)"]
        AuthMiddleware["JWT Authentication & Multi-Tenant Ownership Checks"]
        Validation["Magic Byte & Size Validation (20MB Limit)"]
    end

    subgraph StorageLayer["Storage Backend"]
        LocalStorage["Local Filesystem (UUID-keyed files /uploads)"]
        S3Storage["S3 / Cloud Storage (Interface Extensible)"]
    end

    subgraph MessagingLayer["Distributed Message Broker"]
        Redis["Redis (Broker & Result Backend)"]
    end

    subgraph WorkerLayer["Asynchronous Compute Layer"]
        CeleryWorker["Celery Worker Nodes"]
        PyMuPDF["PyMuPDF (fitz) Direct Digital Extractor"]
        Tesseract["Tesseract OCR + OSD Rotation Engine"]
        LLMEngine["LLM Question Extractor (OpenAI / Azure)"]
        AnswerMatcher["Answer Matcher & Text Similarity Engine"]
    end

    subgraph PersistenceLayer["Relational Data Store"]
        Postgres[("PostgreSQL 16")]
        UsersTable["users"]
        DocsTable["documents & document_groups"]
        PagesTable["pages"]
        QuestionsTable["questions"]
        AnswersTable["answers"]
    end

    Client -->|HTTPS / Multipart Upload| API
    API --> AuthMiddleware
    AuthMiddleware --> Validation
    Validation -->|Persist File| LocalStorage
    Validation -.->|Optional Cloud| S3Storage
    API -->|Insert Document Status=Pending| Postgres
    API -->|Enqueue process_document Task| Redis

    Redis -->|Dispatch Task| CeleryWorker
    CeleryWorker -->|Read Document| LocalStorage
    CeleryWorker --> PyMuPDF
    PyMuPDF -->|Scanned / Sparse Page Fallback| Tesseract
    Tesseract -->|Save Page Rows & Rendered Images| Postgres

    CeleryWorker -->|Concatenate Page Text with [PAGE N]| LLMEngine
    LLMEngine -->|Insert Question Rows & Confidence| Postgres

    CeleryWorker --> AnswerMatcher
    AnswerMatcher -->|Match by Q.No & Similarity| Postgres

    Client -->|Query Status / Questions / Review Items| API
    API -->|Read-Only Queries| Postgres
```

---

## 2. Document Processing Approach

Document ingestion follows a staged, fault-tolerant pipeline designed to process both clean digital documents and low-quality/scanned physical camera captures:

1. **Synchronous Validation & Ingestion**:
   - The user sends a multipart file upload.
   - The API verifies file size ($\le 20\text{ MB}$) using streaming byte limits.
   - File signatures (magic bytes) are inspected against verified MIME signatures (`%PDF`, `\xFF\xD8\xFF`, `\x89PNG`).
   - The file is saved to disk using a non-predictable UUID (`uuid4`).
   - A `Document` record is inserted with `status = "pending"` and the task is dispatched to Celery. The client receives an immediate response ($< 100\text{ ms}$).

2. **Page-Level Extraction**:
   - The Celery worker picks up `process_document(document_id)`.
   - The document status transitions to `"processing"`.
   - For PDFs: `PyMuPDF` (`fitz`) attempts fast, vector-based direct text extraction on every page.
   - If a page yields fewer than 40 characters or direct extraction fails (as is typical with scanned PDFs), or if the file is an image (`.png`, `.jpg`), the worker renders the page to a high-resolution pixmap and routes it to `pytesseract`.
   - Each page is committed as a `Page` row with its `page_number`, `raw_text`, and rendered `image_path` (for human review).

3. **Question Extraction & Classification**:
   - Page texts are assembled using page boundary markers (`[PAGE 1]\n...`).
   - The system categorizes document roles: dedicated answer keys are assigned `doc_role = "answer_key"`, while exam papers are assigned `doc_role = "question_paper"`.
   - For question papers, the structured question extractor parses out `question_number`, `question_text`, `options`, and `source_pages`.

4. **Answer Association & Human Review Queue**:
   - Cross-document or in-document answer key sections are parsed.
   - Answers are matched to questions. Unconfident matches are marked `matched = false` and preserved with explicit reasons.
   - The document status transitions to `"done"`.

---

## 3. OCR and LLM Technology Choices & Rationale

| Technology | Role | Why Chosen & Alternatives Evaluated |
| :--- | :--- | :--- |
| **PyMuPDF (`fitz`)** | Digital Text Extraction & Page Rendering | Extremely fast C-based engine (MuPDF). Up to 10x faster than `pdfplumber` or `pypdf`. Accurately extracts embedded vector text, preserves reading order, and renders high-DPI page images for review. |
| **Tesseract OCR (`pytesseract`)** | Optical Character Recognition Fallback | Open-source, production-proven OCR engine. Handles diverse typefaces. Bundled with Orientation & Script Detection (`OSD`) to automatically correct rotated camera captures before character recognition. |
| **OpenAI / LLM API (`gpt-4o-mini`)** | Semantic Question Structuring | LLMs excel at parsing complex, semi-structured academic layouts, nested options, and multi-line equations that brittle regexes fail on. Configurable via standard OpenAI-compatible base URLs. |
| **Rule-Based Fallback Parser** | Deterministic Extraction Safety Net | Operates completely offline without external network dependencies. Guarantees zero downtime if LLM quota is exhausted or API keys are not provided. |

---

## 4. Storage Design

The file storage subsystem is decoupled from the business logic through an abstract backend interface:

```python
class StorageBackend(ABC):
    @abstractmethod
    def save_file(self, file_content: bytes, original_filename: str) -> str:
        pass

    @abstractmethod
    def get_file(self, storage_path: str) -> bytes:
        pass
```

### Key Highlights:
- **`LocalStorage` Implementation**:
  - Files are organized inside `uploads/{uuid4}.{ext}`.
  - Original filenames are never trusted in paths, preventing directory traversal attacks (`../../etc/passwd`).
  - Rendered review images are saved to `uploads/rendered/{uuid4}_page_{num}.png`.
- **Cloud Readiness**:
  - Because all file interaction uses `storage_path`, swapping `LocalStorage` for an `S3Storage` or `GCSStorage` class requires changing only the dependency injection provider without modifying route handlers or workers.

---

## 5. How Asynchronous Processing Works

The asynchronous processing architecture decouples request ingestion from long-running OCR and AI inference:

1. **Celery Worker Architecture**:
   - The worker runs as an independent OS process in its own container (`docintel_worker`).
   - Work is scheduled via Redis task queues with Redis persistent AOF logging.
2. **Task Atomicity & State Recovery**:
   - Tasks manage database transactions cleanly with dedicated session lifecycles (`try...finally: db.close()`).
   - If an unexpected worker crash occurs, Celery task acknowledgment settings prevent lost jobs.
   - Unhandled processing errors automatically catch exceptions, rollback uncommitted DB transactions, set `Document.status = "failed"`, and log full diagnostic tracebacks.

---

## 6. Extraction Strategy

Academic exam papers vary widely in formatting (e.g., standard numbers `1.`, bracketed `(1)`, nested Roman numerals, or tabular options).

The extraction pipeline uses a **hybrid multi-stage strategy**:
1. **Marker Concatenation**:
   Pages are stitched with clear anchors:
   ```text
   [PAGE 1]
   1. What is the unit of force?
   (A) Joule (B) Newton (C) Pascal (D) Watt
   [PAGE 2]
   2. Explain Archimedes' principle.
   ```
2. **Strict LLM System Prompting**:
   Instructs the LLM to output exclusively a raw JSON array of objects conforming to:
   ```json
   {
     "question_number": 1,
     "question_text": "What is the unit of force?",
     "options": ["(A) Joule", "(B) Newton", "(C) Pascal", "(D) Watt"],
     "question_type": "multiple_choice",
     "source_pages": [1],
     "ambiguous": false
   }
   ```
3. **Resilience & Retry**:
   If the LLM returns invalid JSON or markdown fluff, the service catches the decode error and executes one immediate retry with an explicit error correction prompt. If that fails, it falls back to the deterministic regex engine.

---

## 7. Answer-Key Association Approach

The answer matcher supports two real-world workflows:
1. **Intra-Document**: Exam papers that include an "Answer Key" or "Solutions" section at the end of the document.
2. **Inter-Document (Document Groups)**: A question paper uploaded as one document and an official answer key uploaded as a separate document or scanned photo.

### Matching Algorithm:
```text
For each candidate answer:
  1. Check Question Number:
     - If candidate has Q.No 'N' and Question 'N' exists in question paper:
         -> MATCH (Confidence: 1.0)
  2. Fallback to Text Similarity:
     - If Q.No is absent, ambiguous, or unmatched:
         - Compare answer text against question text and all option strings using:
           max(SequenceMatcher.ratio, JaccardTokenSimilarity)
         - If similarity >= 0.70:
             -> MATCH (Confidence: similarity_score)
         - Else:
             -> UNMATCHED (matched=false, confidence=similarity_score,
                           record explicit reason)
```

By explicitly recording `matched = false` and storing the reasoning rather than guessing, the system guarantees high precision and flags ambiguous items for review.

---

## 8. Confidence & Human-in-the-Loop Review Mechanism

Every question and answer receives an audit-ready confidence score:

### Question Confidence Rules:
- **`1.0`**: Digital direct extraction where `question_number`, `question_text`, and `options` are all cleanly identified. Status: `"extracted"`.
- **`0.7`**: OCR fallback was required on the page, or options were missing for a multiple-choice question. Status: `"extracted"`.
- **`0.4`**: Missing question number or the parser flagged textual ambiguity. Status: `"needs_review"`.

### Human Review Endpoint (`GET /documents/{id}/review-items`):
Aggregates all items requiring human verification into a single payload:
- All questions where `status == "needs_review"`.
- All answers where `matched == false` with the exact explanation of why the match failed.

---

## 9. Security Considerations

1. **Authentication & Multi-Tenant Isolation**:
   - Stateless JWT tokens signed with HMAC-SHA256 (`HS256`).
   - Passwords hashed using industry-standard `bcrypt` with adaptive salt cost.
   - Strict resource ownership checks: A user cannot view, list, or download documents, questions, or answer keys belonging to another user (enforces 404 to avoid leaking resource existence).
2. **File Validation**:
   - Enforces an absolute 20MB payload size limit.
   - Magic byte header inspection ensures uploaded files are genuine PDFs, PNGs, or JPEGs, rejecting disguised executables or scripts.
3. **Secret Management**:
   - Zero hardcoded credentials. All database strings, secrets, and API keys are injected at runtime via environment variables (`.env`).
   - `.env` is ignored by `.gitignore`.

---

## 10. Scalability Considerations

- **Horizontal Worker Scaling**: Celery workers are stateless. As document throughput grows, additional worker containers can be spun up across nodes (`docker compose scale worker=5`).
- **Database Indexing**: Foreign keys (`document_id`, `owner_id`, `group_id`) and lookup identifiers are indexed in PostgreSQL.
- **Connection Pooling**: SQLAlchemy utilizes persistent connection pooling with health recycling to optimize PostgreSQL connection overhead.
- **Chunked File Streaming**: Large file uploads are streamed in chunks rather than buffering entire files in memory.

---

## 11. Known Limitations & Future Roadmap

1. **Complex Mathematical Formatting**: Pure LaTeX equation rendering in OCR fallback pages can occasionally experience character confusion (e.g., distinguishing summation $\sum$ from $E$). Future iterations can integrate specialized vision models (e.g., Nougat or multimodal Gemini).
2. **Multi-Column Layout Disruption**: Non-standard multicolumn newspapers or 3-column exam layouts can lead to interleaved lines if reading order is ambiguous.
3. **Handwritten Exam Processing**: Current Tesseract configuration is optimized for printed exam papers. Handwritten student answer sheets would benefit from fine-tuned HTR (Handwritten Text Recognition) models.
