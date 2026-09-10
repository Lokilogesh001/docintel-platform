import pytest
from backend.app.services.document_validation_service import DocumentValidationService
from backend.app.services.financial_validation_service import financial_validation_service
from backend.app.utils.text_helpers import parse_financial_number, floats_approx_equal

# =============================================================
# 1. FILE & DOCUMENT VALIDATION TESTS
# =============================================================

def test_supported_pdf(sample_pdf_bytes):
    """Test 1: Supported PDF passes validation."""
    res, err = DocumentValidationService.validate_file("invoice.pdf", sample_pdf_bytes)
    assert err is None
    assert res.status == "PASS"
    assert res.is_supported is True
    assert res.is_readable is True
    assert res.page_count == 1
    assert res.file_type == "application/pdf"

def test_supported_jpg(sample_jpg_bytes):
    """Test 2: Supported JPG passes validation."""
    res, err = DocumentValidationService.validate_file("receipt.jpg", sample_jpg_bytes)
    assert err is None
    assert res.status == "PASS"
    assert res.is_supported is True
    assert res.file_type == "image/jpeg"
    assert res.page_count == 1

def test_supported_png(sample_png_bytes):
    """Test 3: Supported PNG passes validation."""
    res, err = DocumentValidationService.validate_file("bill.png", sample_png_bytes)
    assert err is None
    assert res.status == "PASS"
    assert res.is_supported is True
    assert res.file_type == "image/png"
    assert res.page_count == 1

def test_unsupported_file():
    """Test 4: Unsupported extension (.docx / .exe) is rejected with UNSUPPORTED_FILE_TYPE."""
    content = b"Mock Microsoft Word or executable binary"
    res, err = DocumentValidationService.validate_file("malicious.exe", content)
    assert err is not None
    assert err.code == "UNSUPPORTED_FILE_TYPE"
    assert res.status == "FAIL"
    assert res.is_supported is False

def test_corrupted_file(corrupted_pdf_bytes):
    """Test 5: Corrupted PDF document is rejected with CORRUPTED_PDF."""
    res, err = DocumentValidationService.validate_file("corrupt.pdf", corrupted_pdf_bytes)
    assert err is not None
    assert err.code == "CORRUPTED_PDF"
    assert res.status == "FAIL"

def test_empty_file(empty_file_bytes):
    """Test 6: 0-byte file is rejected with EMPTY_FILE."""
    res, err = DocumentValidationService.validate_file("empty.pdf", empty_file_bytes)
    assert err is not None
    assert err.code == "EMPTY_FILE"
    assert res.status == "FAIL"

def test_page_limit_exceeded(four_page_pdf_bytes):
    """Test 7: PDF exceeding 3 pages is rejected with PAGE_LIMIT_EXCEEDED."""
    res, err = DocumentValidationService.validate_file("long_doc.pdf", four_page_pdf_bytes)
    assert err is not None
    assert err.code == "PAGE_LIMIT_EXCEEDED"
    assert res.status == "FAIL"
    assert res.page_count == 4

# =============================================================
# 2. FINANCIAL VALIDATION TESTS
# =============================================================

def test_invoice_validation():
    """Test 8: Invoice financial validation passes when calculations match."""
    data = {
        "subtotal": 12500.00,
        "tax_amount": 625.00,
        "discount": 0.00,
        "total_amount": 13125.00,
        "line_items": [
            {"description": "Item 1", "quantity": 10, "unit_price": 1000.00, "amount": 10000.00},
            {"description": "Item 2", "quantity": 5, "unit_price": 500.00, "amount": 2500.00}
        ]
    }
    result = financial_validation_service.validate("invoice", data)
    assert result.overall_status == "PASS"
    assert len(result.issues) == 0

    # Verify individual checks
    total_check = next(c for c in result.checks if c.name == "invoice_total_check")
    assert total_check.status == "PASS"
    assert total_check.calculated_value == 13125.00
    assert total_check.variance == 0.00

def test_balance_sheet_validation():
    """Test 9: Balance sheet validation: Assets == Liabilities + Equity."""
    data = {
        "total_assets": 500000.00,
        "total_liabilities": 300000.00,
        "total_equity": 200000.00,
        "total_capital_and_liabilities": 500000.00,
        "asset_line_items": [
            {"name": "Current Assets", "amount": 200000.00},
            {"name": "Fixed Assets", "amount": 300000.00}
        ]
    }
    result = financial_validation_service.validate("balance_sheet", data)
    assert result.overall_status == "PASS"
    eq_check = next(c for c in result.checks if c.name == "balance_sheet_equation")
    assert eq_check.status == "PASS"

def test_profit_and_loss_validation():
    """Test 10: P&L validation: Income, Expenditure, and Net Profit."""
    data = {
        "interest_earned": 50000.00,
        "other_income": 10000.00,
        "total_income": 60000.00,
        "interest_expended": 20000.00,
        "operating_expenses": 15000.00,
        "provisions": 5000.00,
        "total_expenditure": 40000.00,
        "net_profit_before_minority_interest": 20000.00,
        "minority_interest": 2000.00,
        "net_profit": 18000.00
    }
    result = financial_validation_service.validate("profit_and_loss", data)
    assert result.overall_status == "PASS"

def test_cash_flow_validation():
    """Test 11: Cash flow validation: Activities sum == Net change in cash."""
    data = {
        "operating_cash_flow": 150000.00,
        "investing_cash_flow": -50000.00,
        "financing_cash_flow": -20000.00,
        "fx_adjustment": 0.00,
        "net_change_in_cash": 80000.00,
        "opening_cash": 20000.00,
        "cash_acquired_adjustments": 0.00,
        "closing_cash": 100000.00
    }
    result = financial_validation_service.validate("cash_flow_statement", data)
    assert result.overall_status == "PASS"

def test_parentheses_as_negative_values():
    """Test 12: Parentheses/brackets must be parsed as negative numbers."""
    assert parse_financial_number("(5,000)") == -5000.0
    assert parse_financial_number("(12,345.67)") == -12345.67
    assert parse_financial_number("[$4,500.00]") == -4500.0
    assert parse_financial_number(" -2,500 ") == -2500.0
    assert parse_financial_number("3,450.50") == 3450.50

def test_not_applicable_validation():
    """
    Test 13: Mandatory NOT_APPLICABLE rule.
    If required operand is null in source document:
    DO NOT assume zero. Return NOT_APPLICABLE.
    """
    data = {
        "subtotal": 12500.00,
        "tax_amount": None,  # Missing field!
        "discount": 0.00,
        "total_amount": 13125.00
    }
    result = financial_validation_service.validate("invoice", data)
    total_check = next(c for c in result.checks if c.name == "invoice_total_check")
    assert total_check.status == "NOT_APPLICABLE"
    assert total_check.calculated_value is None
    assert total_check.variance is None
    assert result.overall_status == "NOT_APPLICABLE"

def test_financial_validation_failure():
    """Test financial calculation failure when numbers do not balance."""
    data = {
        "subtotal": 1000.00,
        "tax_amount": 100.00,
        "discount": 0.00,
        "total_amount": 2000.00  # Deliberate mismatch: 1000 + 100 != 2000
    }
    result = financial_validation_service.validate("invoice", data)
    assert result.overall_status == "FAIL"
    assert len(result.issues) > 0
    fail_check = next(c for c in result.checks if c.name == "invoice_total_check")
    assert fail_check.status == "FAIL"
    assert fail_check.variance == 900.00
