import pytest
from backend.app.services.ocr_service import DocumentTextResult, PageTextResult
from backend.app.services.extraction_service import extraction_service
from backend.app.services.evidence_service import evidence_service
from backend.app.schemas.extraction import InvoiceExtraction, BalanceSheetExtraction

def test_invoice_structured_extraction():
    """Test extraction of invoice fields, line items, and totals."""
    text = (
        "INVOICE\n"
        "Invoice #: INV-9901\n"
        "Date: 2024-11-01\n"
        "Vendor: TechCorp Global\n"
        "Customer: Alpha Holdings\n"
        "Software License 2 1500.00 3000.00\n"
        "Consulting Hours 10 200.00 2000.00\n"
        "Subtotal: 5000.00\n"
        "Tax Amount: 500.00\n"
        "Discount: 0.00\n"
        "Total Amount: 5500.00\n"
    )
    doc_text = DocumentTextResult(
        pages=[PageTextResult(page_number=1, text=text, word_count=len(text.split()))],
        combined_text=text,
        page_count=1
    )
    res = extraction_service.extract("invoice", doc_text)

    assert res["invoice_number"] == "INV-9901"
    assert res["vendor_name"] == "TechCorp Global"
    assert res["customer_name"] == "Alpha Holdings"
    assert res["subtotal"] == 5000.00
    assert res["tax_amount"] == 500.00
    assert res["total_amount"] == 5500.00
    assert len(res["line_items"]) >= 2
    assert "field_evidence" in res
    assert "total_amount" in res["field_evidence"]
    assert res["field_evidence"]["total_amount"]["evidence"]["source_text"] is not None

def test_balance_sheet_structured_extraction():
    """Test balance sheet extraction with assets, liabilities, and equity."""
    text = (
        "Consolidated Balance Sheet\n"
        "Entity: Acme Enterprises Inc.\n"
        "As at 31 December 2024\n"
        "Cash and Equivalents 100000.00\n"
        "Accounts Receivable 50000.00\n"
        "Total Assets: 150000.00\n"
        "Accounts Payable 60000.00\n"
        "Total Liabilities: 60000.00\n"
        "Common Stock 90000.00\n"
        "Total Equity: 90000.00\n"
        "Total Capital and Liabilities: 150000.00\n"
    )
    doc_text = DocumentTextResult(
        pages=[PageTextResult(page_number=1, text=text, word_count=len(text.split()))],
        combined_text=text,
        page_count=1
    )
    res = extraction_service.extract("balance_sheet", doc_text)

    assert res["total_assets"] == 150000.00
    assert res["total_liabilities"] == 60000.00
    assert res["total_equity"] == 90000.00
    assert res["total_capital_and_liabilities"] == 150000.00

def test_cash_flow_parentheses_extraction():
    """Test negative numbers in parentheses in cash flow statements."""
    text = (
        "Statement of Cash Flows\n"
        "Operating Activities: 85000.00\n"
        "Investing Activities: (35,000.00)\n"
        "Financing Activities: (10,000.00)\n"
        "Net Increase in Cash: 40000.00\n"
        "Opening Cash: 15000.00\n"
        "Closing Cash: 55000.00\n"
    )
    doc_text = DocumentTextResult(
        pages=[PageTextResult(page_number=1, text=text, word_count=len(text.split()))],
        combined_text=text,
        page_count=1
    )
    res = extraction_service.extract("cash_flow_statement", doc_text)

    assert res["operating_cash_flow"] == 85000.00
    assert res["investing_cash_flow"] == -35000.00
    assert res["financing_cash_flow"] == -10000.00
    assert res["net_change_in_cash"] == 40000.00
    assert res["opening_cash"] == 15000.00
    assert res["closing_cash"] == 55000.00

def test_missing_fields_return_null():
    """Verify that absent fields return None/null rather than fabricated values."""
    text = "Basic Note with no invoice number or totals."
    doc_text = DocumentTextResult(
        pages=[PageTextResult(page_number=1, text=text, word_count=len(text.split()))],
        combined_text=text,
        page_count=1
    )
    res = extraction_service.extract("invoice", doc_text)
    assert res["invoice_number"] is None
    assert res["subtotal"] is None
    assert res["tax_amount"] is None
    assert res["total_amount"] is None
