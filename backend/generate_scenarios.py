import io
import json
import os
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw

from backend.app.core.database import SessionLocal, init_db
from backend.app.services.document_service import document_service
from backend.app.services.document_validation_service import DocumentValidationError

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "sample_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_all_scenarios():
    init_db()
    db = SessionLocal()

    # ---------------------------------------------------------
    # SCENARIO A: Invoice successfully processed
    # ---------------------------------------------------------
    doc_a = fitz.open()
    page_a = doc_a.new_page(width=600, height=800)
    text_a = (
        "INVOICE\n"
        "Invoice #: INV-2024-889\n"
        "Date: 2024-11-12\n"
        "Vendor: Apex Cloud Infrastructure\n"
        "Customer: Nexa Enterprise Systems\n"
        "Enterprise Server Cluster 2 4500.00 9000.00\n"
        "Dedicated Fiber Link     1 1500.00 1500.00\n"
        "Subtotal: 10500.00\n"
        "Tax Amount: 1050.00\n"
        "Discount: 0.00\n"
        "Total Amount: 11550.00\n"
    )
    page_a.insert_text((50, 50), text_a, fontsize=12)
    bytes_a = doc_a.tobytes()
    doc_a.close()

    res_a = document_service.process_document(db, "scenario_a_invoice.pdf", bytes_a, "invoice")
    with open(OUTPUT_DIR / "scenario_a_invoice_success.json", "w", encoding="utf-8") as f:
        json.dump(res_a.model_dump(), f, indent=2)
    print("Scenario A generated.")

    # ---------------------------------------------------------
    # SCENARIO B: Balance Sheet successfully processed
    # ---------------------------------------------------------
    doc_b = fitz.open()
    page_b = doc_b.new_page(width=600, height=800)
    text_b = (
        "BALANCE SHEET\n"
        "Entity: Quantum Dynamics Corporation\n"
        "As at 31 December 2024\n"
        "Cash and Cash Equivalents 250000.00\n"
        "Accounts Receivable 150000.00\n"
        "Property and Equipment 400000.00\n"
        "Total Assets: 800000.00\n"
        "Current Liabilities 300000.00\n"
        "Long Term Debt 200000.00\n"
        "Total Liabilities: 500000.00\n"
        "Retained Earnings 300000.00\n"
        "Total Equity: 300000.00\n"
        "Total Capital and Liabilities: 800000.00\n"
    )
    page_b.insert_text((50, 50), text_b, fontsize=12)
    bytes_b = doc_b.tobytes()
    doc_b.close()

    res_b = document_service.process_document(db, "scenario_b_balance_sheet.pdf", bytes_b, "balance_sheet")
    with open(OUTPUT_DIR / "scenario_b_balance_sheet_success.json", "w", encoding="utf-8") as f:
        json.dump(res_b.model_dump(), f, indent=2)
    print("Scenario B generated.")

    # ---------------------------------------------------------
    # SCENARIO C: Profit & Loss successfully processed
    # ---------------------------------------------------------
    doc_c = fitz.open()
    page_c = doc_c.new_page(width=600, height=800)
    text_c = (
        "PROFIT AND LOSS STATEMENT\n"
        "Entity: Horizon Financial Holdings\n"
        "For the Year Ended 31 December 2024\n"
        "Interest Earned: 120000.00\n"
        "Other Income: 30000.00\n"
        "Total Income: 150000.00\n"
        "Interest Expended: 40000.00\n"
        "Operating Expenses: 35000.00\n"
        "Provisions: 15000.00\n"
        "Total Expenditure: 90000.00\n"
        "Profit Before Minority Interest: 60000.00\n"
        "Minority Interest: 5000.00\n"
        "Net Profit: 55000.00\n"
    )
    page_c.insert_text((50, 50), text_c, fontsize=12)
    bytes_c = doc_c.tobytes()
    doc_c.close()

    res_c = document_service.process_document(db, "scenario_c_pnl.pdf", bytes_c, "profit_and_loss")
    with open(OUTPUT_DIR / "scenario_c_pnl_success.json", "w", encoding="utf-8") as f:
        json.dump(res_c.model_dump(), f, indent=2)
    print("Scenario C generated.")

    # ---------------------------------------------------------
    # SCENARIO D: Cash Flow Statement successfully processed (Parentheses negative)
    # ---------------------------------------------------------
    doc_d = fitz.open()
    page_d = doc_d.new_page(width=600, height=800)
    text_d = (
        "CASH FLOW STATEMENT\n"
        "Entity: Vanguard Maritime Group\n"
        "For Year 2024\n"
        "Operating Activities: 95000.00\n"
        "Investing Activities: (45,000.00)\n"
        "Financing Activities: (20,000.00)\n"
        "FX Adjustment: 0.00\n"
        "Net Increase in Cash: 30000.00\n"
        "Opening Cash: 50000.00\n"
        "Closing Cash: 80000.00\n"
    )
    page_d.insert_text((50, 50), text_d, fontsize=12)
    bytes_d = doc_d.tobytes()
    doc_d.close()

    res_d = document_service.process_document(db, "scenario_d_cash_flow.pdf", bytes_d, "cash_flow_statement")
    with open(OUTPUT_DIR / "scenario_d_cash_flow_success.json", "w", encoding="utf-8") as f:
        json.dump(res_d.model_dump(), f, indent=2)
    print("Scenario D generated.")

    # ---------------------------------------------------------
    # SCENARIO E: Scanned/image-based PNG processed
    # ---------------------------------------------------------
    img_e = Image.new("RGB", (700, 300), color=(255, 255, 255))
    buf_e = io.BytesIO()
    img_e.save(buf_e, format="PNG")
    bytes_e = buf_e.getvalue()

    res_e = document_service.process_document(db, "scenario_e_scanned_receipt.png", bytes_e, "invoice")
    with open(OUTPUT_DIR / "scenario_e_scanned_ocr_success.json", "w", encoding="utf-8") as f:
        json.dump(res_e.model_dump(), f, indent=2)
    print("Scenario E generated.")

    # ---------------------------------------------------------
    # SCENARIO F: Financial validation failure
    # ---------------------------------------------------------
    doc_f = fitz.open()
    page_f = doc_f.new_page(width=600, height=800)
    text_f = (
        "INVOICE\n"
        "Invoice #: INV-FAIL-01\n"
        "Subtotal: 1000.00\n"
        "Tax Amount: 100.00\n"
        "Discount: 0.00\n"
        "Total Amount: 2500.00\n"  # Mathematical mismatch: 1000 + 100 != 2500
    )
    page_f.insert_text((50, 50), text_f, fontsize=12)
    bytes_f = doc_f.tobytes()
    doc_f.close()

    res_f = document_service.process_document(db, "scenario_f_validation_failure.pdf", bytes_f, "invoice")
    with open(OUTPUT_DIR / "scenario_f_validation_failure.json", "w", encoding="utf-8") as f:
        json.dump(res_f.model_dump(), f, indent=2)
    print("Scenario F generated.")

    # ---------------------------------------------------------
    # SCENARIO G: Missing/unreadable field (NOT_APPLICABLE)
    # ---------------------------------------------------------
    doc_g = fitz.open()
    page_g = doc_g.new_page(width=600, height=800)
    text_g = (
        "INVOICE\n"
        "Invoice #: INV-PARTIAL-99\n"
        "Vendor: Partial Data Services\n"
        "Subtotal: 5000.00\n"
        "Total Amount: 5500.00\n"  # Tax Amount is absent from source!
    )
    page_g.insert_text((50, 50), text_g, fontsize=12)
    bytes_g = doc_g.tobytes()
    doc_g.close()

    res_g = document_service.process_document(db, "scenario_g_missing_field.pdf", bytes_g, "invoice")
    with open(OUTPUT_DIR / "scenario_g_missing_field_na.json", "w", encoding="utf-8") as f:
        json.dump(res_g.model_dump(), f, indent=2)
    print("Scenario G generated.")

    # ---------------------------------------------------------
    # SCENARIO H: Unsupported/invalid file
    # ---------------------------------------------------------
    try:
        document_service.process_document(db, "scenario_h_invalid.exe", b"Executable binary content", "invoice")
    except DocumentValidationError as dve:
        res_h = {
            "error": {
                "code": dve.code,
                "message": dve.message
            }
        }
        with open(OUTPUT_DIR / "scenario_h_invalid_file_error.json", "w", encoding="utf-8") as f:
            json.dump(res_h, f, indent=2)
        print("Scenario H generated.")

    db.close()
    print("All 8 demonstration scenarios successfully generated in sample_outputs/!")

if __name__ == "__main__":
    generate_all_scenarios()
