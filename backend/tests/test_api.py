import pytest
from fastapi.testclient import TestClient

def test_api_health(client: TestClient):
    """Test 14: GET /api/v1/health returns 200 with system diagnostics."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["database_connected"] is True
    assert "timestamp" in data

def test_post_document_process_success(client: TestClient, sample_pdf_bytes):
    """Test 15: POST /api/v1/documents/process succeeds with valid document."""
    files = {"file": ("test_invoice.pdf", sample_pdf_bytes, "application/pdf")}
    data = {"document_type": "invoice"}

    res = client.post("/api/v1/documents/process", files=files, data=data)
    assert res.status_code == 200
    json_resp = res.json()
    assert json_resp["document_name"] == "test_invoice.pdf"
    assert json_resp["document_type"] == "invoice"
    assert json_resp["file_validation"]["status"] == "PASS"
    assert json_resp["processing_status"] in ("PASS", "NOT_APPLICABLE")
    assert "extracted_data" in json_resp
    assert "validation" in json_resp
    assert "processing_metadata" in json_resp

def test_get_document_by_name(client: TestClient, sample_pdf_bytes):
    """Test 16: GET /api/v1/documents/{document_name} retrieves latest stored result."""
    # Process document first
    files = {"file": ("unique_invoice_name.pdf", sample_pdf_bytes, "application/pdf")}
    res_post = client.post("/api/v1/documents/process", files=files, data={"document_type": "invoice"})
    assert res_post.status_code == 200

    # Retrieve by name
    res_get = client.get("/api/v1/documents/unique_invoice_name.pdf")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["document_name"] == "unique_invoice_name.pdf"
    assert data["document_type"] == "invoice"

def test_get_nonexistent_document(client: TestClient):
    """Test nonexistent document returns 404 DOCUMENT_NOT_FOUND."""
    res = client.get("/api/v1/documents/does_not_exist_12345.pdf")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "DOCUMENT_NOT_FOUND"

def test_get_documents_list(client: TestClient, sample_pdf_bytes):
    """Test 17: GET /api/v1/documents returns list of records."""
    # Ensure at least one is present
    files = {"file": ("list_test.pdf", sample_pdf_bytes, "application/pdf")}
    client.post("/api/v1/documents/process", files=files, data={"document_type": "invoice"})

    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) > 0
    assert "document_name" in items[0]
    assert "processing_status" in items[0]

def test_database_persistence_latest_version(client: TestClient, sample_pdf_bytes):
    """Test 18: Database persistence returns latest result when same document is uploaded twice."""
    # Upload first time
    files1 = {"file": ("version_test.pdf", sample_pdf_bytes, "application/pdf")}
    client.post("/api/v1/documents/process", files=files1, data={"document_type": "invoice"})

    # Upload second time
    files2 = {"file": ("version_test.pdf", sample_pdf_bytes, "application/pdf")}
    res2 = client.post("/api/v1/documents/process", files=files2, data={"document_type": "invoice"})
    assert res2.status_code == 200

    # GET must return latest result
    res_get = client.get("/api/v1/documents/version_test.pdf")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["document_name"] == "version_test.pdf"

def test_post_invalid_document_type(client: TestClient, sample_pdf_bytes):
    """Test invalid document type fails with 400 INVALID_DOCUMENT_TYPE."""
    files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
    res = client.post("/api/v1/documents/process", files=files, data={"document_type": "unsupported_type"})
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "INVALID_DOCUMENT_TYPE"

def test_post_unsupported_file(client: TestClient):
    """Test unsupported extension fails with 400 UNSUPPORTED_FILE_TYPE."""
    files = {"file": ("test.docx", b"Microsoft Word Doc Content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = client.post("/api/v1/documents/process", files=files, data={"document_type": "invoice"})
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

def test_swagger_docs_available(client: TestClient):
    """Test OpenAPI /docs is accessible."""
    res = client.get("/docs")
    assert res.status_code == 200
    assert "Swagger UI" in res.text
