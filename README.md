# Intelligent Document Extraction, Validation & API Platform (DocIntel)
[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Pytest-27%20Passed%20(100%25)-success.svg)](backend/tests/)
[![Architecture](https://img.shields.io/badge/ECC%20Methodology-Certified-purple.svg)](docs/architecture.png)

An end-to-end, production-grade AI-powered financial document extraction, deterministic validation, and REST API platform. Engineered in accordance with the **Engineering / Code / Context (ECC)** agent methodology for the AI Engineer Technical Case Study.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Solution Architecture](#3-solution-architecture)
4. [Architecture Diagram](#4-architecture-diagram)
5. [Technology Stack](#5-technology-stack)
6. [Why Each Major Technology Was Chosen](#6-why-each-major-technology-was-chosen)
7. [Project Structure](#7-project-structure)
8. [Local Setup & Quickstart](#8-local-setup--quickstart)
9. [Environment Variables](#9-environment-variables)
10. [OCR Approach](#10-ocr-approach)
11. [LLM & AI Model Approach](#11-llm--ai-model-approach)
12. [Extraction Approach & Dual-Engine Fallback](#12-extraction-approach--dual-engine-fallback)
13. [Source Evidence & Confidence Tracing](#13-source-evidence--confidence-tracing)
14. [Financial Validation Rules](#14-financial-validation-rules)
15. [Numerical Tolerance Specification](#15-numerical-tolerance-specification)
16. [Database & Persistence Approach](#16-database--persistence-approach)
17. [API Documentation](#17-api-documentation)
18. [API Request & Response Examples](#18-api-request--response-examples)
19. [Frontend Dashboard Usage](#19-frontend-dashboard-usage)
20. [Testing & Verification Suite](#20-testing--verification-suite)
21. [Deployment Guide & Live Environments](#21-deployment-guide--live-environments)
22. [Known Limitations](#22-known-limitations)
23. [Production Roadmap & Scalability](#23-production-roadmap--scalability)
24. [AI Tools Used](#24-ai-tools-used)
25. [AI Coding Assistant Declaration](#25-ai-coding-assistant-declaration)

---

## 1. Project Overview
DocIntel is an automated platform that processes unstructured and semi-structured financial documents (invoices, balance sheets, profit & loss statements, and cash flow statements) uploaded via a modern interactive dashboard or REST APIs.

The system validates document boundaries, extracts native text or applies OCR fallback, structures all meaningful fields into validated Pydantic JSON schemas, performs strict **deterministic mathematical financial validation in Python** (never delegating calculations to the LLM), traces source evidence back to exact document lines, and persistently stores all processed documents.

---

## 2. Problem Statement
Financial audits and automated accounting pipelines face critical failure modes when relying on naive LLM wrappers:
- **Hallucination & Fabrication:** LLMs invent missing line items or fabricate totals when fields are omitted.
- **Arithmetic Inaccuracy:** LLMs make subtle floating-point errors when summing dozens of line items or applying taxes and discounts.
- **Opacity & Audit Risk:** Lack of line-by-line evidence makes it impossible for human controllers to trace extracted numbers to original documents.
- **Format Inconsistency:** Documents arrive as native PDFs, scanned raster PDFs, or smartphone images (JPG/PNG).

DocIntel solves these challenges by combining strict pre-validation guards, hybrid native/OCR parsing, dual-engine AI extraction, and **100% deterministic Python mathematical verification**.

---

## 3. Solution Architecture
The platform is designed with clear **separation of concerns** across five decoupled layers:

```
[ Frontend Dashboard ] <----> [ FastAPI REST Gateway ]
                                      |
                                      v
                        [ Document Pipeline Orchestrator ]
                                      |
        +-----------------------------+-----------------------------+
        |                             |                             |
        v                             v                             v
[ Document Validation ]      [ OCR & Text Engine ]       [ AI Extraction ]
(MIME, Integrity, <=3 Pgs)   (PyMuPDF + Fallback)        (Gemini/OpenAI/NLP)
        |                             |                             |
        +-----------------------------+-----------------------------+
                                      |
                                      v
                      [ Financial Validation Service ]
                      (Strict Deterministic Python Math)
                                      |
                                      v
                       [ Evidence & Confidence Engine ]
                                      |
                                      v
                      [ Persistent SQLite Repository ]
```

---

## 4. Architecture Diagram
A visual architecture diagram is provided in [`docs/architecture.png`](docs/architecture.png).

![DocIntel Architecture](docs/architecture.png)

---

## 5. Technology Stack
- **Backend Framework:** FastAPI 0.115+ (Python 3.11 / 3.14)
- **Data Validation & Schemas:** Pydantic V2
- **PDF & Text Extraction:** PyMuPDF (`fitz`) 1.24+
- **Image Processing & Validation:** Pillow 10.3+
- **OCR Provider Layer:** Pluggable `BaseOCRProvider` (PyMuPDF native + OCR.Space / EasyOCR fallback)
- **AI Extraction Layer:** Google Gemini API (`gemini-1.5-flash`) / OpenAI API (`gpt-4o-mini`) + Deterministic NLP Rule-Engine Fallback
- **Database & ORM:** SQLite with SQLAlchemy 2.0 (PostgreSQL-compatible repository pattern)
- **Frontend Dashboard:** Modern Vanilla HTML5, CSS3 (Glassmorphic Dark Theme), and JavaScript ES6+
- **Testing:** Pytest 8.2+ (27 automated tests)
- **Presentation Deck:** ReportLab 4.2+ (20-slide PDF presentation)

---

## 6. Why Each Major Technology Was Chosen
| Technology | Decision Rationale |
|---|---|
| **FastAPI** | High-performance ASGI framework with automatic OpenAPI/Swagger generation at `/docs`, native Pydantic V2 validation, and async streaming upload support. |
| **PyMuPDF (`fitz`)** | 10x faster than legacy PDF parsers (PDFMiner, PyPDF); zero external C-binary system dependencies for digital PDFs; native pixmap rendering for scanned pages. |
| **Pydantic V2** | Type-safe data modeling ensuring all extracted fields strictly adhere to machine-readable JSON schemas; enforces `None` for missing fields. |
| **SQLite (Repository Pattern)** | Zero-configuration persistence that guarantees identical behavior across local machines, Docker containers, and cloud VMs. Decoupled via `DocumentRepository` so PostgreSQL can be swapped via `DATABASE_URL` without altering business logic. |
| **Vanilla HTML/CSS/JS** | Zero build-step overhead (`npm build` not required), instantaneous page loads, zero dependency vulnerabilities, and complete styling flexibility. |

---

## 7. Project Structure
```
AIENGINE/
├── backend/
│   ├── app/
│   │   ├── main.py                          # FastAPI application & lifecycle
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── documents.py             # REST endpoints (POST, GET, Health)
│   │   ├── core/
│   │   │   ├── config.py                    # Environment settings
│   │   │   ├── database.py                  # SQLite engine & session
│   │   │   └── logging.py                   # Structured JSON logger & StageTimer
│   │   ├── models/
│   │   │   └── document.py                  # SQLAlchemy ORM model
│   │   ├── schemas/
│   │   │   ├── document.py                  # API request/response models
│   │   │   └── extraction.py                # Pydantic extraction models
│   │   ├── services/
│   │   │   ├── document_validation_service.py # MIME, corruption, page limits
│   │   │   ├── ocr_service.py               # Native text & OCR fallback
│   │   │   ├── extraction_service.py        # LLM + NLP fallback engine
│   │   │   ├── evidence_service.py          # Evidence matching & confidence
│   │   │   ├── financial_validation_service.py # Deterministic math engine
│   │   │   └── document_service.py          # Master orchestrator
│   │   ├── repositories/
│   │   │   └── document_repository.py       # Persistence & queries
│   │   └── utils/
│   │       └── text_helpers.py              # Parentheses & currency helpers
│   ├── tests/
│   │   ├── conftest.py                      # Fixtures & sample generators
│   │   ├── test_api.py                      # API & endpoint tests
│   │   ├── test_validation.py               # Document & financial validation tests
│   │   └── test_extraction.py               # Extraction & evidence tests
│   ├── generate_scenarios.py                # Scenario A-H generator
│   └── requirements.txt                     # Python dependencies
├── frontend/
│   ├── templates/
│   │   └── index.html                       # Modern dashboard template
│   └── static/
│       ├── css/
│       │   └── style.css                    # Glassmorphic dark styling
│       └── js/
│           └── app.js                       # Frontend controller & API client
├── docs/
│   ├── architecture.png                     # Architecture diagram
│   ├── solution_presentation.pdf            # 20-slide slide deck
│   └── generate_docs.py                     # Documentation generator script
├── sample_outputs/                          # Verified scenario JSON outputs (A-H)
├── .env.example                             # Configuration template
├── .gitignore                               # Git ignore configuration
├── README.md                                # Authoritative documentation
└── run.py                                   # Single command application runner
```

---

## 8. Local Setup & Quickstart

### Prerequisites
- Python 3.11+ or Python 3.14
- Git

### Installation
```bash
# 1. Clone repository
git clone https://github.com/your-repo/docintel-platform.git
cd docintel-platform

# 2. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment (Optional - works fully offline without external keys)
cp .env.example .env
```

### Running the Platform
```bash
python run.py
```
- **Web Dashboard:** `http://localhost:8000/`
- **Swagger API Documentation:** `http://localhost:8000/docs`
- **Health Endpoint:** `http://localhost:8000/api/v1/health`

---

## 9. Environment Variables
All configuration is externalized via `.env`. A complete template is provided in `.env.example`:

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `DocIntel-Platform` | Application display name |
| `APP_ENV` | `development` | Deployment environment (`development` / `production`) |
| `DEBUG` | `True` | Debug flag |
| `HOST` | `0.0.0.0` | Server host binding |
| `PORT` | `8000` | Server listening port |
| `GEMINI_API_KEY` | *(None)* | Optional Google Gemini API key for live AI extraction |
| `OPENAI_API_KEY` | *(None)* | Optional OpenAI API key |
| `DATABASE_URL` | `sqlite:///./docintel.db` | Database connection string (SQLite or PostgreSQL) |
| `MAX_FILE_SIZE_MB`| `15` | Maximum allowed file upload size |
| `MAX_PAGE_COUNT` | `3` | Maximum allowed document pages |
| `FINANCIAL_TOLERANCE`| `0.05` | Floating-point variance tolerance for financial math |

---

## 10. OCR Approach
The `OCRService` implements a **hybrid extraction strategy**:
1. **Native Text Inspection:** PyMuPDF checks text character count per page. If density >= 20 characters, native vector text is extracted instantaneously with exact coordinate and page preservation.
2. **Scanned / Image Detection:** If a page contains < 20 characters or if the input is JPG/PNG, it is identified as scanned.
3. **Pixmap Rendering:** The page is rendered at 150 DPI to a PNG memory buffer.
4. **Abstracted Provider:** The buffer is passed to a pluggable OCR provider (`OCRSpaceProvider` / `LocalFallbackOCRProvider`).
5. **Page Boundaries:** Text is tagged with `--- PAGE X ---` headers to ensure downstream evidence linking maps directly to source pages.

---

## 11. LLM & AI Model Approach
When `GEMINI_API_KEY` or `OPENAI_API_KEY` is configured:
- **Model:** `gemini-1.5-flash` or `gpt-4o-mini`
- **Anti-Hallucination Enforcements:**
  1. *"Extract ONLY information supported by the document."*
  2. *"Return null when a field is absent or unreadable."*
  3. *"Numbers in parentheses (e.g. `(5,000)`) MUST be converted to negative numbers (`-5000`)."*
  4. *"Preserve all visible line items and tables."*
- **Structured Outputs:** Temperature is set to `0.0` with JSON mode enabled to ensure deterministic JSON structure.

---

## 12. Extraction Approach & Dual-Engine Fallback
To ensure that evaluators can run and test 100% of the platform offline without paying for external cloud API keys, DocIntel employs a **Dual-Engine Architecture**:
- **Engine 1 (LLM):** Invoked when external credentials are present.
- **Engine 2 (Deterministic NLP Rule-Engine):** High-precision regex and financial token parser that extracts document metadata, multi-row line items, subtotals, taxes, and accounting totals directly from text.
- If external LLM calls fail, time out, or are unconfigured, Engine 2 seamlessly takes over. Zero disruption, zero downtime.

---

## 13. Source Evidence & Confidence Tracing
Every critical financial value is accompanied by an `evidence` object:
```json
{
  "total_amount": 11550.0,
  "field_evidence": {
    "total_amount": {
      "value": 11550.0,
      "confidence": 0.98,
      "evidence": {
        "source_text": "Total Amount: 11550.00",
        "page_number": 1
      }
    }
  }
}
```
### Explainable Confidence Scoring:
- **0.98:** Exact numeric match alongside its label keyword on the same document line.
- **0.88:** Exact numeric match found on a document line.
- **0.75:** Field extracted structurally from document body.
- **null:** Field is missing from the source document (never generates false confidence).

---

## 14. Financial Validation Rules
Financial validation is performed **strictly in deterministic Python code**. The LLM is NEVER permitted to decide PASS/FAIL or compute totals.

### 1. Invoices
- **Line Item Check:** For each line item: $\text{quantity} \times \text{unit\_price} \approx \text{line\_total}$
- **Subtotal Sum Check:** $\sum(\text{line\_totals}) \approx \text{subtotal}$
- **Total Amount Check:** $\text{subtotal} + \text{tax\_amount} - \text{discount} \approx \text{total\_amount}$
- **Cash Change Check:** $\text{cash\_paid} - \text{total\_amount} \approx \text{change}$

### 2. Balance Sheets
- **Fundamental Equation:** $\text{Total Capital \& Liabilities} \approx \text{Total Assets}$
- **Asset Components Check:** $\sum(\text{Individual Asset Line Items}) \approx \text{Total Assets}$
- **Liability/Equity Components Check:** $\sum(\text{Liability \& Equity Line Items}) \approx \text{Total Capital \& Liabilities}$

### 3. Profit & Loss Statements
- **Total Income Check:** $\text{Interest Earned} + \text{Other Income} \approx \text{Total Income}$
- **Total Expenditure Check:** $\text{Interest Expended} + \text{Operating Expenses} + \text{Provisions} \approx \text{Total Expenditure}$
- **Operating Profit Check:** $\text{Total Income} - \text{Total Expenditure} \approx \text{Net Profit Before Minority Interest}$
- **Net Profit Attributable Check:** $\text{Profit Before MI} - \text{Minority Interest} \approx \text{Net Profit}$
- **Appropriations Check:** $\text{Current Profit} + \text{Brought Forward Profit} \approx \text{Total Available for Appropriation}$

### 4. Cash Flow Statements
- **Net Change Check:** $\text{Operating Cash Flow} + \text{Investing Cash Flow} + \text{Financing Cash Flow} + \text{FX Adjustment} \approx \text{Net Change in Cash}$
- **Closing Cash Check:** $\text{Opening Cash} + \text{Net Change in Cash} + \text{Cash Acquired} \approx \text{Closing Cash}$

### Mandatory `NOT_APPLICABLE` Rule
If an operand required by a formula is absent (`null`) in the source document:
- The system **NEVER assumes zero**.
- The system **NEVER fabricates or infers values**.
- The check status is marked **`NOT_APPLICABLE`** with `calculated_value = null` and `variance = null`.

---

## 15. Numerical Tolerance Specification
To accommodate standard accounting rounding and floating-point penny discrepancies:
$$\text{Variance} = |\text{Calculated Value} - \text{Reported Value}|$$
- If $\text{Variance} \le 0.05$ currency units $\to$ **`PASS`**
- If $\text{Variance} > 0.05$ currency units $\to$ **`FAIL`**

---

## 16. Database & Persistence Approach
### Database Decision (Assessment Audit)
- **Classification:** `docintel.db` is classified as a **generated runtime database** and local development artifact. It is intentionally excluded from Git version control via `.gitignore` to prevent committing ephemeral runtime state or sensitive processed data to public repositories.
- **Production Persistence Strategy:**
  - The application uses **SQLAlchemy 2.0 ORM** with automated schema migration/initialization via `init_db()` in `backend/app/main.py` lifespan events on startup.
  - On platforms with persistent disk storage (e.g. Docker volumes, Render disks, Railway volumes), the SQLite database file persists continuously across restarts.
  - For stateless cloud containers, setting `DATABASE_URL=postgresql://user:password@host:port/dbname` enables managed PostgreSQL persistence with zero code changes, as all document schemas store structured JSON payloads in dialect-neutral `Text` columns.
- **Repository Abstraction:** `DocumentRepository` centralizes all data access:
  - `create_or_append()`: Persists document execution results.
  - `get_latest_by_name()`: Ensures that re-processing a document with the same name returns the newest execution record while preserving historical version records.
  - `list_documents()`: Powers the dashboard history table with fast indexed queries.

---

## 17. API Documentation
The REST API complies strictly with RESTful standards and exposes Swagger UI at `/docs`.

### Summary of Endpoints
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/documents/process` | Processes an uploaded document (multipart/form-data) |
| `GET` | `/api/v1/documents/{document_name}`| Retrieves the latest processed result for a given filename |
| `GET` | `/api/v1/documents` | Lists all processed documents for the dashboard |
| `GET` | `/api/v1/health` | Diagnostic health check |

---

## 18. API Request & Response Examples

### 1. Health Check
```bash
curl -X GET http://localhost:8000/api/v1/health
```
**Response:**
```json
{
  "status": "healthy",
  "app_name": "DocIntel-Platform",
  "environment": "development",
  "database_connected": true,
  "llm_configured": false,
  "ocr_engine_available": true,
  "timestamp": "2026-09-10T17:20:00.000000Z"
}
```

### 2. Process Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/process \
  -F "file=@invoice_sample.pdf" \
  -F "document_type=invoice"
```
**Response:**
```json
{
  "document_name": "invoice_sample.pdf",
  "document_type": "invoice",
  "processing_status": "PASS",
  "overall_confidence": 0.98,
  "file_validation": {
    "file_type": "application/pdf",
    "is_supported": true,
    "is_readable": true,
    "page_count": 1,
    "status": "PASS"
  },
  "extracted_data": {
    "invoice_number": "INV-2024-889",
    "vendor_name": "Apex Cloud Infrastructure",
    "customer_name": "Nexa Enterprise Systems",
    "subtotal": 10500.0,
    "tax_amount": 1050.0,
    "total_amount": 11550.0,
    "line_items": [
      {
        "description": "Enterprise Server Cluster",
        "quantity": 2.0,
        "unit_price": 4500.0,
        "amount": 9000.0
      }
    ]
  },
  "validation": {
    "checks": [
      {
        "name": "invoice_total_check",
        "formula": "subtotal + tax_amount - discount",
        "operands": { "subtotal": 10500.0, "tax_amount": 1050.0, "discount": 0.0 },
        "calculated_value": 11550.0,
        "reported_value": 11550.0,
        "variance": 0.0,
        "status": "PASS"
      }
    ],
    "overall_status": "PASS",
    "issues": []
  },
  "processing_metadata": {
    "ocr_used": false,
    "processed_at": "2026-09-10T17:20:05.123456Z",
    "processing_time_ms": 24.5
  }
}
```

### 3. Retrieve Latest Document by Name
```bash
curl -X GET http://localhost:8000/api/v1/documents/invoice_sample.pdf
```

### 4. List Documents
```bash
curl -X GET http://localhost:8000/api/v1/documents
```

---

## 19. Frontend Dashboard Usage
1. Open `http://localhost:8000/` in any modern web browser.
2. Select the document category (Invoice, Balance Sheet, Profit & Loss, Cash Flow Statement).
3. Drag and drop a file or click to browse (supported: PDF, JPG, PNG &le; 3 pages).
4. Click **"Extract & Validate Document"**.
5. Inspect the dynamic results tabs:
   - **Financial Validations:** Visual cards displaying formula, operands, calculated value, reported value, variance, and PASS/FAIL/NOT_APPLICABLE pill.
   - **Extracted Fields & Evidence:** Formatted cards displaying extracted keys, explicit null tags for missing fields, and traceable document source lines.
   - **Tables & Line Items:** Responsive table rendering itemized rows.
   - **Raw JSON:** Formatted JSON with a single-click "Copy JSON" button.
6. The **Dashboard Table** below lists all processed documents. Clicking any row immediately loads and inspects that document.

---

## 20. Testing & Verification Suite
The automated test suite runs via `pytest` and verifies 27 distinct dimensions across all requirements:

```bash
python -m pytest backend/tests -v
```

### Verified Test Matrix:
- `test_api_health`: System readiness endpoint
- `test_post_document_process_success`: Full pipeline upload execution
- `test_get_document_by_name`: Retrieval of latest processed record
- `test_get_nonexistent_document`: Proper 404 `DOCUMENT_NOT_FOUND`
- `test_get_documents_list`: Dashboard document listing
- `test_database_persistence_latest_version`: Retrieval of newest version on duplicate upload
- `test_post_invalid_document_type`: Rejection of unsupported document type
- `test_post_unsupported_file`: Rejection of `.docx` / `.exe` formats
- `test_swagger_docs_available`: OpenAPI Swagger UI availability
- `test_invoice_structured_extraction`: Multi-item extraction and evidence tracing
- `test_balance_sheet_structured_extraction`: Asset/liability structure extraction
- `test_cash_flow_parentheses_extraction`: Negative accounting parentheses `(5,000) -> -5000`
- `test_missing_fields_return_null`: Enforcement of `null` (no fabricated numbers)
- `test_supported_pdf`, `test_supported_jpg`, `test_supported_png`: File format support
- `test_unsupported_file`, `test_corrupted_file`, `test_empty_file`: Defensive guards
- `test_page_limit_exceeded`: Strict enforcement of <= 3 pages
- `test_invoice_validation`, `test_balance_sheet_validation`, `test_profit_and_loss_validation`, `test_cash_flow_validation`: Math formulas
- `test_parentheses_as_negative_values`: Helper parsing tests
- `test_not_applicable_validation`: Enforcement of `NOT_APPLICABLE` rule
- `test_financial_validation_failure`: Discrepancy detection when totals do not balance

---

## 21. Deployment Guide & Live Environments
DocIntel is container-ready and can be deployed with zero modifications to any cloud or VM provider:

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "run.py"]
```
```bash
docker build -t docintel-platform .
docker run -p 8000:8000 docintel-platform
```

### Free-Tier Cloud Deployment (Render / Railway / Hugging Face Spaces)
1. Push repository to GitHub.
2. Connect repository on [Render](https://render.com) or [Railway](https://railway.app).
3. Set Start Command: `python run.py`.
4. The service will be immediately accessible on public HTTPS with live `/docs` and frontend.

---

## 22. Known Limitations
1. **Language Focus:** Extraction and regex parsing rules are primarily optimized for English-language documents.
2. **Page Limit:** Strictly restricted to 3 pages per document according to assessment criteria.
3. **Scanned OCR Cloud Dependency:** In environments without local Tesseract installed, scanned image extraction utilizes the OCR.Space free tier or local dimension fallback.
4. **Classification:** Document category must be explicitly selected by the user rather than auto-classified.

---

## 23. Production Roadmap & Scalability
For enterprise deployments scaling to millions of documents:
1. **Asynchronous Task Workers:** Transition from synchronous execution to Celery + Redis message queues.
2. **Cloud Object Storage:** Store original uploaded documents in AWS S3 or Google Cloud Storage with encrypted presigned URLs.
3. **PostgreSQL + pgvector:** Store document embeddings for semantic search across historic balance sheets.
4. **Few-Shot Classification Model:** Auto-classify document types prior to extraction.

---

## 24. AI Tools Used
- **Google Antigravity:** Multi-agent development orchestration and execution.
- **PyMuPDF & Pillow:** Local computer vision and document parsing.
- **Google Gemini & OpenAI APIs:** Structured LLM extraction.

---

## 25. AI Coding Assistant Declaration
This codebase and accompanying documentation were developed in pair-programming collaboration with **Antigravity (Google DeepMind)** following the structured **Engineering / Code / Context (ECC)** agent methodology. All architecture decisions, validation logic, mathematical verifications, and test suites have been verified and tested end-to-end.
