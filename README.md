# Document Intelligence Service

An asynchronous, AI-powered document intelligence backend designed for educational and assessment workflows. The service ingests question papers and answer keys (PDFs and images), performs digital text extraction with OCR fallback and orientation correction, parses structured questions using configurable LLM providers, and matches answer keys to questions with confidence scoring and human-in-the-loop review queues.

---

## 1. Prerequisites

Before running the application, ensure you have the following installed:
- **Docker** (version 24.0 or higher)
- **Docker Compose** (v2.20 or higher)
- **curl** or **Postman** (for interacting with the API)
- Optional for local non-container development: Python 3.12+, Tesseract OCR, and PostgreSQL 16+.

---

## 2. Environment Configuration (`.env`)

Copy the provided `.env.example` to create your local `.env` configuration:

```bash
cp .env.example .env
```

### Key Environment Variables

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `PROJECT_NAME` | Name of the FastAPI application | `"document-intelligence-service"` |
| `ENVIRONMENT` | Deployment environment (`development` / `production`) | `development` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@postgres:5432/document_intelligence` |
| `REDIS_URL` | Redis broker and backend URL for Celery | `redis://redis:6379/0` |
| `JWT_SECRET` | Secret key used for signing JWT auth tokens | `your_super_secret_jwt_key_change_me_in_production` |
| `JWT_ALGORITHM` | Cryptographic algorithm for JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiration time for access tokens | `1440` (24 hours) |
| `LLM_PROVIDER` | LLM service provider (`openai`, `azure`, or compatible) | `openai` |
| `LLM_BASE_URL` | Base API endpoint for chat completions | `https://api.openai.com/v1` |
| `LLM_MODEL` | Target language model name | `gpt-4o-mini` |
| `OPENAI_API_KEY` | OpenAI API Key (falls back to rule-based parser if omitted) | `your_openai_api_key_here` |
| `UPLOAD_DIR` | Local filesystem storage path for uploaded files | `uploads/` |

---

## 3. Starting the Service with Docker Compose

Start all four microservices (PostgreSQL database, Redis broker, FastAPI application, and Celery asynchronous worker):

```bash
docker compose up -d --build
```

### Verify Service Health

1. Check running containers:
   ```bash
   docker compose ps
   ```
   You should see:
   - `docintel_postgres` (healthy on port 5432)
   - `docintel_redis` (healthy on port 6379)
   - `docintel_api` (up on port 8000)
   - `docintel_worker` (up, running Celery)

2. Perform a health check:
   ```bash
   curl -s http://localhost:8000/health
   ```
   **Expected Response:**
   ```json
   {
     "status": "ok",
     "service": "document-intelligence-service",
     "environment": "development"
   }
   ```

3. Interactive API Documentation (Swagger UI):
   Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

---

## 4. Running Automated Tests

Run the complete 27-test pytest suite directly inside the API container:

```bash
docker compose exec -T api pytest -v
```

The test suite covers:
- User registration, duplicate rejection, and JWT authentication.
- File upload restrictions (20MB limit, valid PDF/PNG/JPG magic byte verification, wrong extension rejection).
- Document ownership and multi-tenant security isolation.
- OCR page extraction and orientation detection.
- Question extraction confidence rules and LLM JSON parsing (with mocked responses and retries).
- Answer matcher heuristics, text similarity fallback, and review items endpoint.

---

## 5. Hitting the API (cURL Examples)

### Step 1: Register and Authenticate

**1. Register a User:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@example.com",
    "password": "SecurePassword123!"
  }'
```

**2. Login to Obtain Access Token:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@example.com",
    "password": "SecurePassword123!"
  }' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Bearer Token: $TOKEN"
```

---

### Step 2: Upload Documents

**1. Upload a Question Paper (PDF):**
```bash
curl -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_docs/sample_question_paper.pdf"
```
**Response:**
```json
{
  "id": 1,
  "status": "pending",
  "filename": "sample_question_paper.pdf"
}
```

**2. Upload an Answer Key (PDF or Image):**
```bash
curl -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_docs/sample_answer_key.pdf"
```

---

### Step 3: Check Processing Status

Check whether background OCR and extraction have completed:
```bash
curl -s -X GET http://localhost:8000/documents/1 \
  -H "Authorization: Bearer $TOKEN"
```
**Response:**
```json
{
  "id": 1,
  "status": "done",
  "filename": "sample_question_paper.pdf",
  "doc_role": "question_paper",
  "created_at": "2026-09-19T10:15:30"
}
```

---

### Step 4: Link Question Paper and Answer Key in a Group

**1. Create a Document Group:**
```bash
curl -X POST http://localhost:8000/document-groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "2026 Science Midterm Exam"}'
```

**2. Add Question Paper and Answer Key to the Group:**
```bash
curl -X POST http://localhost:8000/document-groups/1/add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": 1}'

curl -X POST http://localhost:8000/document-groups/1/add \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": 2}'
```

---

### Step 5: Query Extracted Questions and Answers

**1. Get All Extracted Questions for Document:**
```bash
curl -s -X GET http://localhost:8000/documents/1/questions \
  -H "Authorization: Bearer $TOKEN"
```

**2. Get Matched Answer for Question #1:**
```bash
curl -s -X GET http://localhost:8000/questions/1/answer \
  -H "Authorization: Bearer $TOKEN"
```
**Response:**
```json
{
  "status": "matched",
  "question_id": 1,
  "answer": {
    "id": 1,
    "question_id": 1,
    "raw_answer_text": "(B) Paris",
    "matched": true,
    "confidence_score": 1.0,
    "source_document_id": 2,
    "unmatched_reason": null,
    "created_at": "2026-09-19T10:16:00"
  },
  "reason": null
}
```

**3. Get Review Items (Ambiguous Questions & Unmatched Answers):**
```bash
curl -s -X GET http://localhost:8000/documents/1/review-items \
  -H "Authorization: Bearer $TOKEN"
```
**Response:**
```json
{
  "document_id": 1,
  "needs_review_questions": [],
  "unmatched_answers": [
    {
      "id": 2,
      "question_id": null,
      "raw_answer_text": "Photosynthesis produces glucose and oxygen from sunlight and water",
      "matched": false,
      "confidence_score": 0.33,
      "source_document_id": 2,
      "unmatched_reason": "Question number 99 not found in document questions, and maximum text similarity is below threshold (0.33 < 0.70).",
      "created_at": "2026-09-19T10:16:00"
    }
  ]
}
```

---

## 6. Postman Collection

You can also import `postman_collection.json` directly into Postman. It includes pre-configured collection variables (`{{baseUrl}}`, `{{token}}`, `{{documentId}}`, `{{questionId}}`, `{{groupId}}`) and automatic test scripts to handle token passing and resource chaining.
