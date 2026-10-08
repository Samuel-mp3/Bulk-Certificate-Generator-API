# Bulk Certificate Generator Backend API

A simple, robust, and clean asynchronous backend API for generating PDF certificates in bulk. Built with Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, and ReportLab.

---

## Technical Stack

- **Framework**: FastAPI (ASGI web framework) + Uvicorn
- **Database**: SQLAlchemy 2.x ORM with SQLite (swappable to PostgreSQL via `DATABASE_URL` environment variable)
- **Data Validation & Schemas**: Pydantic v2
- **PDF Generation**: ReportLab (Landscape A4 template with dynamic font scaling)
- **Testing**: pytest + FastAPI TestClient

---

## Core Architecture & Key Features

1. **Dual-Tier Validation**:
   - **Request-Level (HTTP 422)**: Rejects malformed requests missing required fields (`title`, `issuer_name`, `recipients`), empty recipient lists, or requests exceeding 1,000 recipients.
   - **Recipient-Level (Partial Failure Handling)**: Invalid emails, blank/whitespace names, and duplicate emails within the payload do **not** fail the entire job. Instead, failed recipients are saved as `FAILED` `Certificate` rows with descriptive error messages, while valid recipients are queued for generation.

2. **Asynchronous Background Processing**:
   - `POST /jobs` returns an immediate `202 Accepted` response with the job UUID.
   - A FastAPI `BackgroundTask` opens its own isolated database session and iterates through pending certificates.
   - **Per-Certificate Error Isolation**: Each PDF rendering step is wrapped in its own `try/except` block. A failure for one recipient (e.g. font rendering error or invalid non-ASCII character) will not stop processing for others.

3. **Granular Polling & Progress Tracking**:
   - DB state is committed per certificate during background processing, allowing clients polling `GET /jobs/{job_id}` to see live `progress_percentage`, `success_count`, and `failure_count`.
   - Final job statuses: `COMPLETED` (100% success), `COMPLETED_WITH_ERRORS` (partial success), or `FAILED` (0% success).

4. **Secure File Storage**:
   - PDF filenames use the `Certificate.id` UUID (e.g., `3f7a1b90-....pdf`) stored under `CERTIFICATES_DIR`, avoiding path traversal vulnerabilities and invalid characters from recipient names.

---

## Project Structure

```
bulk_certificate_generator/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application creation & router setup
│   ├── config.py                   # Pydantic environment configuration
│   ├── database.py                 # SQLAlchemy engine, session maker, get_db dependency
│   ├── models.py                   # Job and Certificate SQLAlchemy models
│   ├── schemas.py                  # Pydantic v2 request/response validation schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── jobs.py                 # Job creation, status polling, list certs, download ZIP
│   │   └── certificates.py         # Single certificate PDF download endpoint
│   └── services/
│       ├── __init__.py
│       ├── certificate_generator.py # ReportLab landscape A4 PDF drawing service
│       └── job_processor.py         # Background worker job execution logic
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest database & environment fixtures
│   ├── test_create_job.py          # Job submission tests
│   ├── test_validation.py          # Request & recipient validation tests
│   ├── test_generation.py          # ReportLab PDF rendering unit tests
│   ├── test_job_status.py          # Job status calculation & progress tests
│   ├── test_failure_handling.py    # Per-recipient error isolation tests
│   └── test_retrieval.py           # Single PDF & ZIP download endpoint tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.11+ installed.

### 2. Create Virtual Environment & Install Dependencies
```bash
# Create a virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

Contents of `.env`:
```env
DATABASE_URL=sqlite:///./certificates.db
CERTIFICATES_DIR=./certificates
HOST=0.0.0.0
PORT=8000
```

---

## Running the Server

Start the Uvicorn ASGI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive API Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **Alternative OpenAPI Docs (ReDoc)**: `http://localhost:8000/redoc`

---

## Running Automated Tests

Run the complete test suite with `pytest`:
```bash
pytest -v
```

All 16 test cases cover:
- Job submission & 202 response
- Request-level validation (422 for empty payload, >1000 recipients, missing title)
- Recipient-level validation (partial failure, invalid emails, blank names, duplicate emails)
- ReportLab PDF generation validation (`%PDF` binary header, font scaling for long names)
- Job status & progress percentage calculations (`COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`)
- Monkeypatched per-recipient failure isolation
- Single PDF stream download and bulk ZIP archive creation (with 404 & 409 conflict checks)

---

## Example `curl` Commands

### 1. Submit a Bulk Job (Demonstrating Partial Recipient Validation Failure)
```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cloud Native Architecture",
    "issuer_name": "DevOps Guild",
    "issue_date": "2026-10-08",
    "recipients": [
      {"name": "Alice Smith", "email": "alice@example.com"},
      {"name": "Bob Jones", "email": "bob@example.com"},
      {"name": "   ", "email": "blank@example.com"},
      {"name": "Charlie Brown", "email": "invalid-email-format"}
    ]
  }'
```

**Response (HTTP 202 Accepted)**:
```json
{
  "id": "b7c2a1e4-8f9d-4e2a-b1c3-5d6e7f8a9b0c",
  "title": "Cloud Native Architecture",
  "issuer_name": "DevOps Guild",
  "issue_date": "2026-10-08",
  "status": "PENDING",
  "total_count": 4,
  "success_count": 0,
  "failure_count": 2,
  "created_at": "2026-10-08T18:00:00",
  "updated_at": "2026-10-08T18:00:00"
}
```

### 2. Poll Job Status & Progress
```bash
curl -X GET "http://localhost:8000/jobs/b7c2a1e4-8f9d-4e2a-b1c3-5d6e7f8a9b0c"
```

**Response**:
```json
{
  "id": "b7c2a1e4-8f9d-4e2a-b1c3-5d6e7f8a9b0c",
  "title": "Cloud Native Architecture",
  "issuer_name": "DevOps Guild",
  "issue_date": "2026-10-08",
  "status": "COMPLETED_WITH_ERRORS",
  "total_count": 4,
  "success_count": 2,
  "failure_count": 2,
  "created_at": "2026-10-08T18:00:00",
  "updated_at": "2026-10-08T18:00:05",
  "progress_percentage": 100.0
}
```

### 3. List Certificates for a Job
```bash
curl -X GET "http://localhost:8000/jobs/b7c2a1e4-8f9d-4e2a-b1c3-5d6e7f8a9b0c/certificates"
```

### 4. Download a Single Certificate PDF
```bash
curl -X GET "http://localhost:8000/certificates/{CERTIFICATE_UUID}/download" --output certificate.pdf
```

### 5. Download Job ZIP Archive
```bash
curl -X GET "http://localhost:8000/jobs/b7c2a1e4-8f9d-4e2a-b1c3-5d6e7f8a9b0c/download" --output certificates.zip
```

---

## Design Decisions & Trade-Offs

1. **FastAPI & Async Architecture**:
   - Chosen for its high performance, automatic OpenAPI documentation, and native support for Pydantic v2 schemas.
2. **Database Engine & ORM Abstraction**:
   - SQLAlchemy 2.x declarative ORM models decoupled via `DATABASE_URL`. Switching from local SQLite to PostgreSQL requires changing only the environment variable without code changes.
3. **Background Processing Trade-Offs (FastAPI `BackgroundTasks` vs Celery/RQ)**:
   - **Trade-Off**: FastAPI `BackgroundTasks` run in-process in worker threads.
   - **Pros**: Zero external dependencies (no Redis/RabbitMQ required), simple codebase, ideal for live code reviews and lightweight workloads.
   - **Cons & Limitations**: Background tasks are tied to the web application process memory. If the server restarts or crashes mid-job, pending tasks in memory are lost.
4. **Validation Split (Request vs Recipient Level)**:
   - Request-level errors (missing required body fields, >1000 items) fail fast with HTTP 422 to protect server resources.
   - Recipient-level errors create explicit `FAILED` `Certificate` rows so users can submit bulk jobs without a single bad email ruining thousands of valid records.
5. **UUID File Names**:
   - Certificates are saved as `{certificate_id}.pdf` under `CERTIFICATES_DIR` rather than using recipient names. This eliminates filesystem injection risks, path traversal bugs, and special character filesystem collisions.
6. **1000-Recipient Request Cap**:
   - Limits payload memory overhead and keeps background worker execution time within reasonable limits for in-process execution.

---

## Known Limitations & Production Roadmap ("What I Would Do Next")

1. **Distributed Task Queue (Celery / RQ + Redis)**:
   - Replace in-process `BackgroundTasks` with Celery or RQ workers and a Redis broker to ensure job persistence across server restarts, support horizontal worker scaling, and enable automatic retries.
2. **Object Storage Integration (AWS S3 / Google Cloud Storage)**:
   - Move PDF storage from local filesystem (`CERTIFICATES_DIR`) to S3/GCS buckets with presigned download URLs for enhanced scale and durability.
3. **Idempotency Keys**:
   - Add an `Idempotency-Key` request header for `POST /jobs` to prevent duplicate job creation from client network retries.
4. **Authentication & Authorization**:
   - Implement OAuth2 / JWT authentication to restrict job creation and certificate downloads to authorized users/tenants.
5. **Unicode & Custom Font Registration**:
   - Register a full TrueType font (e.g. Noto Sans) in ReportLab to support non-Latin scripts (Cyrillic, CJK, Arabic) natively without font substitution errors.
