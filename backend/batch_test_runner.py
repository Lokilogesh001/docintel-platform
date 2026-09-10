import os
import sys
import time
import json
from pathlib import Path
import requests

BASE_URL = "http://127.0.0.1:8080/api/v1"
DATASET_DIR = Path(r"C:\Users\loges\Downloads\New Dataset 1\New Dataset")
RESULTS_OUTPUT = Path(r"c:\Users\loges\Downloads\AIENGINE\sample_outputs\batch_test_results.json")
REPORT_OUTPUT = Path(r"c:\Users\loges\Downloads\AIENGINE\sample_outputs\batch_test_report.md")

CATEGORY_MAPPING = {
    "balance sheet": "balance_sheet",
    "balance_sheet": "balance_sheet",
    "cash flows": "cash_flow_statement",
    "cash flow": "cash_flow_statement",
    "cash_flows": "cash_flow_statement",
    "invoices": "invoice",
    "invoice": "invoice",
    "profit & loss": "profit_and_loss",
    "profit and loss": "profit_and_loss",
    "profit_and_loss": "profit_and_loss"
}

def determine_doc_type(folder_name: str, filename: str) -> str:
    folder_clean = folder_name.lower().strip()
    if folder_clean in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[folder_clean]
    
    fn = filename.lower()
    if "balance" in fn:
        return "balance_sheet"
    elif "cash" in fn:
        return "cash_flow_statement"
    elif "profit" in fn or "p&l" in fn or "loss" in fn:
        return "profit_and_loss"
    elif "invoice" in fn or fn.endswith((".jpg", ".png")):
        return "invoice"
    return "invoice"

def update_report(results, all_files, cats):
    RESULTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_OUTPUT, "w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2, ensure_ascii=False)

    passed = [r for r in results if r.get("status_code") == 200]
    total_time = sum(r.get("latency_sec", 0) for r in results)
    avg_latency = round(total_time / max(len(results), 1), 2)

    with open(REPORT_OUTPUT, "w", encoding="utf-8") as rf:
        rf.write("# Automated Dataset Batch Test Report\n\n")
        rf.write(f"- **Dataset Source:** `{DATASET_DIR}`\n")
        rf.write(f"- **Total Target Documents:** {len(all_files)}\n")
        rf.write(f"- **Processed So Far:** {len(results)} / {len(all_files)}\n")
        rf.write(f"- **Successful Ingestions (HTTP 200):** {len(passed)} / {len(results)}\n")
        rf.write(f"- **Average Processing Latency:** {avg_latency}s per document\n\n")
        
        rf.write("## Category Performance Summary\n\n")
        rf.write("| Category | Processed | Succeeded | Pass Status | Avg Latency |\n")
        rf.write("| :--- | :--- | :--- | :--- | :--- |\n")

        for cat in sorted(cats.keys()):
            cat_results = [r for r in results if r["category"] == cat]
            c_cnt = len(cat_results)
            c_succ = sum(1 for r in cat_results if r["status_code"] == 200)
            c_valid = sum(1 for r in cat_results if r.get("is_valid", False))
            c_lat = round(sum(r.get("latency_sec", 0) for r in cat_results) / max(c_cnt, 1), 2)
            rf.write(f"| **{cat}** | {c_cnt} | {c_succ}/{c_cnt} | {c_valid}/{c_cnt} | {c_lat}s |\n")

        rf.write("\n## Ingested Documents & Extracted Highlights\n\n")
        rf.write("| Document | Category | Score | Status | Highlights |\n")
        rf.write("| :--- | :--- | :--- | :--- | :--- |\n")

        for r in results:
            fn = r["filename"]
            cat = r["category"]
            sc = f"{r.get('validation_score', 0)*100:.0f}%"
            st = "PASS" if r.get("is_valid") else ("FAIL" if r.get("error") else "ATTENTION/WARN")
            
            ext = r.get("extracted_data") or {}
            highlights = []
            if "total_amount" in ext and ext["total_amount"] is not None:
                highlights.append(f"Total: ${ext['total_amount']}")
            if "vendor_name" in ext and ext["vendor_name"]:
                highlights.append(f"Vendor: {ext['vendor_name']}")
            if "balance_sheet_equation_holds" in ext:
                highlights.append(f"Eq Holds: {ext['balance_sheet_equation_holds']}")
            if "total_assets" in ext and ext["total_assets"] is not None:
                highlights.append(f"Assets: ${ext['total_assets']:,.0f}" if isinstance(ext['total_assets'], (int, float)) else f"Assets: {ext['total_assets']}")
            if "net_income" in ext and ext["net_income"] is not None:
                highlights.append(f"NetInc: ${ext['net_income']:,.0f}" if isinstance(ext['net_income'], (int, float)) else f"NetInc: {ext['net_income']}")
            if "net_change_in_cash" in ext and ext["net_change_in_cash"] is not None:
                highlights.append(f"NetCash: ${ext['net_change_in_cash']:,.0f}" if isinstance(ext['net_change_in_cash'], (int, float)) else f"NetCash: {ext['net_change_in_cash']}")
            if r.get("error"):
                highlights.append(f"Err: {str(r['error'])[:40]}")

            hl_str = " | ".join(highlights) if highlights else "-"
            rf.write(f"| `{fn}` | {cat} | {sc} | {st} | {hl_str} |\n")

def run_batch_test():
    print(f"==================================================")
    print(f" DocIntel Automated Dataset Batch Testing (Resume Mode)")
    print(f" Source: {DATASET_DIR}")
    print(f" Target API: {BASE_URL}")
    print(f"==================================================\n")

    if not DATASET_DIR.exists():
        print(f"Error: Dataset directory does not exist: {DATASET_DIR}")
        return

    # Check health
    try:
        hr = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"System Health: {hr.status_code} - {hr.json().get('status', 'unknown')}")
    except Exception as e:
        print(f"System Health Check Failed: {e}")
        return

    # Load existing results if any
    existing_results = []
    processed_map = {}
    if RESULTS_OUTPUT.exists():
        try:
            with open(RESULTS_OUTPUT, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
            for r in existing_results:
                if r.get("status_code") == 200:
                    processed_map[r["filename"]] = r
            print(f"Loaded {len(processed_map)} previously successful results.")
        except Exception as e:
            print(f"Could not load previous results: {e}")

    all_files = []
    for root, dirs, files in os.walk(DATASET_DIR):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in [".pdf", ".jpg", ".jpeg", ".png"]:
                folder_name = Path(root).name
                doc_type = determine_doc_type(folder_name, f)
                all_files.append({
                    "path": p,
                    "filename": f,
                    "category": folder_name,
                    "doc_type": doc_type,
                    "size_kb": round(p.stat().st_size / 1024, 2)
                })

    cats = {}
    for item in all_files:
        cats[item["category"]] = cats.get(item["category"], 0) + 1

    print(f"Total files in dataset: {len(all_files)}")
    results = list(existing_results)

    for idx, item in enumerate(all_files, 1):
        fn = item["filename"]
        dtype = item["doc_type"]
        cat = item["category"]
        p = item["path"]

        # Check if already processed
        if fn in processed_map:
            print(f"[{idx}/{len(all_files)}] SKIPPING (Already Ingested): {fn}")
            continue

        print(f"[{idx}/{len(all_files)}] Processing ({cat}) {fn} ... ", end="", flush=True)
        start_t = time.time()

        try:
            with open(p, "rb") as f_obj:
                files = {"file": (fn, f_obj, "application/octet-stream")}
                data = {"document_type": dtype}
                r = requests.post(f"{BASE_URL}/documents/process", files=files, data=data, timeout=90)
            
            elapsed = round(time.time() - start_t, 2)

            if r.status_code == 200:
                res_data = r.json()
                v_res = res_data.get("validation_results", {})
                is_valid = v_res.get("is_valid", False)
                v_score = v_res.get("validation_score", 0.0)
                extracted_data = res_data.get("extracted_data", {})
                rule_breakdown = v_res.get("rule_breakdown", [])

                status_label = "VALID" if is_valid else "ATTENTION/WARN"
                print(f"SUCCESS ({elapsed}s) -> {status_label} (Score: {v_score*100:.0f}%)")

                record = {
                    "filename": fn,
                    "category": cat,
                    "document_type": dtype,
                    "status_code": r.status_code,
                    "latency_sec": elapsed,
                    "is_valid": is_valid,
                    "validation_score": v_score,
                    "extracted_data": extracted_data,
                    "rule_breakdown": rule_breakdown,
                    "error": None
                }
                results.append(record)
                processed_map[fn] = record
            else:
                err_msg = r.text
                try:
                    err_json = r.json()
                    err_msg = err_json.get("error", {}).get("message", err_msg)
                except:
                    pass
                print(f"FAILED ({r.status_code}) in {elapsed}s: {err_msg[:60]}")
                record = {
                    "filename": fn,
                    "category": cat,
                    "document_type": dtype,
                    "status_code": r.status_code,
                    "latency_sec": elapsed,
                    "is_valid": False,
                    "validation_score": 0.0,
                    "extracted_data": None,
                    "rule_breakdown": [],
                    "error": err_msg
                }
                results.append(record)

        except Exception as ex:
            elapsed = round(time.time() - start_t, 2)
            print(f"ERROR ({elapsed}s): {str(ex)[:60]}")
            record = {
                "filename": fn,
                "category": cat,
                "document_type": dtype,
                "status_code": 500,
                "latency_sec": elapsed,
                "is_valid": False,
                "validation_score": 0.0,
                "extracted_data": None,
                "rule_breakdown": [],
                "error": str(ex)
            }
            results.append(record)

        # Incremental save & report update after every document
        update_report(results, all_files, cats)

    print(f"\n==================================================")
    print(f" Batch Test Completed!")
    print(f" Total Processed: {len(results)}")
    print(f" Results saved to: {RESULTS_OUTPUT}")
    print(f" Markdown report: {REPORT_OUTPUT}")
    print(f"==================================================")

if __name__ == "__main__":
    run_batch_test()
