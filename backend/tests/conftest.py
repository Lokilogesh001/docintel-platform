import io
import pytest
from fastapi.testclient import TestClient
import fitz  # PyMuPDF
from PIL import Image, ImageDraw

from backend.app.main import app
from backend.app.core.database import Base, engine, SessionLocal

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup if needed

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper fixtures for document generation
@pytest.fixture
def sample_pdf_bytes():
    """Generates a valid 1-page PDF invoice."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    text = (
        "INVOICE\n"
        "Invoice #: INV-2024-001\n"
        "Date: 2024-10-15\n"
        "Vendor: Acme Cloud Solutions LLC\n"
        "Customer: Global Logistics Corp\n"
        "Item: Cloud Hosting Tier 3  Qty: 2  Unit Price: 500.00  Total: 1000.00\n"
        "Item: Managed Support       Qty: 1  Unit Price: 250.00  Total: 250.00\n"
        "Subtotal: 1250.00\n"
        "Tax Amount: 125.00\n"
        "Discount: 0.00\n"
        "Total Amount: 1375.00\n"
    )
    page.insert_text((50, 50), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

@pytest.fixture
def sample_png_bytes():
    """Generates a valid PNG image invoice."""
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@pytest.fixture
def sample_jpg_bytes():
    """Generates a valid JPG image."""
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

@pytest.fixture
def four_page_pdf_bytes():
    """Generates an invalid 4-page PDF violating the maximum 3-page rule."""
    doc = fitz.open()
    for i in range(4):
        p = doc.new_page(width=600, height=800)
        p.insert_text((50, 50), f"Page {i+1} Content", fontsize=14)
    b = doc.tobytes()
    doc.close()
    return b

@pytest.fixture
def corrupted_pdf_bytes():
    """Returns corrupted PDF header with invalid body."""
    return b"%PDF-1.5 CORRUPTED GARBAGE DATA THAT CRASHES STRICT PARSERS"

@pytest.fixture
def empty_file_bytes():
    """Returns 0-byte content."""
    return b""
