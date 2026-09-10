import json
import re
from typing import Dict, Any, Optional, List
import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.extraction import (
    InvoiceExtraction, InvoiceLineItem,
    BalanceSheetExtraction, FinancialLineItem,
    ProfitAndLossExtraction, CashFlowExtraction
)
from backend.app.services.ocr_service import DocumentTextResult
from backend.app.services.evidence_service import evidence_service
from backend.app.utils.text_helpers import parse_financial_number

class ExtractionService:
    def extract(self, document_type: str, doc_text: DocumentTextResult) -> Dict[str, Any]:
        """
        Main extraction entry point.
        Attempts LLM extraction if an API key is configured.
        Falls back to deterministic rule-based NLP extraction if no API key is set or on failure.
        """
        extracted_dict: Optional[Dict[str, Any]] = None
        self.last_llm_engine: Optional[str] = None

        if settings.GEMINI_API_KEY:
            extracted_dict = self._extract_with_gemini(document_type, doc_text)
            if extracted_dict:
                self.last_llm_engine = "gemini-1.5-flash"
        elif settings.OPENAI_API_KEY:
            extracted_dict = self._extract_with_openai(document_type, doc_text)
            if extracted_dict:
                self.last_llm_engine = settings.OPENAI_MODEL_NAME

        if not extracted_dict:
            logger.info(f"Using rule-based NLP extractor fallback for {document_type}")
            extracted_dict = self._extract_with_nlp_rules(document_type, doc_text)

        # Ensure parenthesized negative values and numeric types are cleaned
        extracted_dict = self._clean_numeric_fields(document_type, extracted_dict)

        # Attach evidence traces for key fields
        evidence_map = evidence_service.enrich_extraction_with_evidence(
            doc_type=document_type,
            extracted_dict=extracted_dict,
            doc_text=doc_text
        )

        # Convert evidence map to serializable dict
        extracted_dict["field_evidence"] = {
            k: v.model_dump() for k, v in evidence_map.items()
        }

        # Validate with target Pydantic schema
        try:
            if document_type == "invoice":
                validated = InvoiceExtraction(**extracted_dict)
                return validated.model_dump()
            elif document_type == "balance_sheet":
                validated = BalanceSheetExtraction(**extracted_dict)
                return validated.model_dump()
            elif document_type == "profit_and_loss":
                validated = ProfitAndLossExtraction(**extracted_dict)
                return validated.model_dump()
            elif document_type == "cash_flow_statement":
                validated = CashFlowExtraction(**extracted_dict)
                return validated.model_dump()
        except Exception as e:
            logger.warning(f"Schema validation warning: {e}. Returning raw extracted dictionary.")

        return extracted_dict

    def _get_extraction_prompt(self, document_type: str) -> str:
        base_prompt = (
            "You are an expert financial document intelligence system. "
            "Extract ALL meaningful visible information from the document text provided into strict JSON.\n"
            "STRICT RULES:\n"
            "1. Extract ONLY information directly supported by the document.\n"
            "2. DO NOT invent, hallucinate, or assume missing values.\n"
            "3. Return null when a field is absent or unreadable.\n"
            "4. Numbers shown in parentheses or brackets like (5,000) or [1,200] MUST be interpreted as negative numbers (-5000, -1200).\n"
            "5. Preserve source values accurately.\n"
            "6. Extract all visible line items, tables, and comparative periods.\n"
        )
        if document_type == "invoice":
            return base_prompt + (
                "Return JSON with fields: invoice_number, invoice_date, due_date, vendor_name, vendor_address, "
                "vendor_tax_id, customer_name, customer_address, currency, purchase_order_number, payment_terms, "
                "subtotal (number), tax_amount (number), tax_rate (number), discount (number), shipping_amount (number), "
                "total_amount (number), cash_paid (number), change (number), "
                "line_items: list of objects with {description, quantity, unit_price, discount, tax, amount}, "
                "additional_fields: object."
            )
        elif document_type == "balance_sheet":
            return base_prompt + (
                "Return JSON with fields: statement_title, entity_name, reporting_period, currency, "
                "total_assets (number), total_liabilities (number), total_equity (number), "
                "total_capital_and_liabilities (number), "
                "asset_line_items: list of {name, category, amount, comparative_amount}, "
                "liability_line_items: list of {name, category, amount, comparative_amount}, "
                "equity_line_items: list of {name, amount, comparative_amount}, "
                "comparative_period, comparative_total_assets, comparative_total_liabilities, comparative_total_equity, "
                "additional_fields: object."
            )
        elif document_type == "profit_and_loss":
            return base_prompt + (
                "Return JSON with fields: statement_title, entity_name, reporting_period, currency, "
                "revenue (number), interest_earned (number), other_income (number), total_income (number), "
                "cost_of_sales (number), cogs (number), gross_profit (number), "
                "operating_expenses (number), interest_expended (number), provisions (number), total_expenditure (number), "
                "operating_profit (number), tax (number), net_profit_before_minority_interest (number), "
                "minority_interest (number), net_profit (number), brought_forward_profit (number), total_appropriations (number), "
                "income_line_items: list of {name, amount, comparative_amount}, "
                "expense_line_items: list of {name, amount, comparative_amount}, "
                "comparative_period, comparative_net_profit, additional_fields: object."
            )
        elif document_type == "cash_flow_statement":
            return base_prompt + (
                "Return JSON with fields: statement_title, entity_name, reporting_period, currency, "
                "operating_cash_flow (number), investing_cash_flow (number), financing_cash_flow (number), "
                "fx_adjustment (number), net_change_in_cash (number), opening_cash (number), "
                "cash_acquired_adjustments (number), closing_cash (number), "
                "operating_activities: list of {name, amount, comparative_amount}, "
                "investing_activities: list of {name, amount, comparative_amount}, "
                "financing_activities: list of {name, amount, comparative_amount}, "
                "comparative_period, comparative_net_change_in_cash, additional_fields: object."
            )
        return base_prompt

    def _extract_with_gemini(self, document_type: str, doc_text: DocumentTextResult) -> Optional[Dict[str, Any]]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            prompt = self._get_extraction_prompt(document_type)
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"text": f"DOCUMENT TEXT:\n{doc_text.combined_text}"}
                    ]
                }],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.0
                }
            }
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    resp_json = res.json()
                    raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(raw_text)
                else:
                    logger.warning(f"Gemini API error ({res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"Gemini API invocation failed: {e}")
        return None

    def _extract_with_openai(self, document_type: str, doc_text: DocumentTextResult) -> Optional[Dict[str, Any]]:
        try:
            url = f"{settings.OPENAI_BASE_URL}/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            prompt = self._get_extraction_prompt(document_type)
            payload = {
                "model": settings.OPENAI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"DOCUMENT TEXT:\n{doc_text.combined_text}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0
            }
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
        except Exception as e:
            logger.warning(f"OpenAI API invocation failed: {e}")
        return None

    def _extract_with_nlp_rules(self, document_type: str, doc_text: DocumentTextResult) -> Dict[str, Any]:
        """
        High-precision deterministic rule-based extractor.
        Parses keys, numbers, parenthesized negatives, and tabular line items from document text.
        """
        text = doc_text.combined_text
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if document_type == "invoice":
            return self._extract_invoice_nlp(lines, text)
        elif document_type == "balance_sheet":
            return self._extract_balance_sheet_nlp(lines, text)
        elif document_type == "profit_and_loss":
            return self._extract_pnl_nlp(lines, text)
        elif document_type == "cash_flow_statement":
            return self._extract_cash_flow_nlp(lines, text)
        return {}

    def _extract_invoice_nlp(self, lines: List[str], full_text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "invoice_number": None,
            "invoice_date": None,
            "vendor_name": None,
            "customer_name": None,
            "currency": "USD",
            "line_items": [],
            "subtotal": None,
            "tax_amount": None,
            "discount": 0.0,
            "total_amount": None,
            "cash_paid": None,
            "change": None,
            "additional_fields": {}
        }

        # Detect currency
        if "$" in full_text or "USD" in full_text:
            result["currency"] = "USD"
        elif "EUR" in full_text or "€" in full_text:
            result["currency"] = "EUR"
        elif "GBP" in full_text or "£" in full_text:
            result["currency"] = "GBP"
        elif "INR" in full_text or "₹" in full_text:
            result["currency"] = "INR"

        line_items = []

        for line in lines:
            lower = line.lower()

            # Invoice number
            if not result["invoice_number"]:
                inv_match = re.search(r'(?:invoice|inv)\s*(?:#|no\.?|num\.?|number)?\s*[:\-\#]\s*([A-Za-z0-9\-_]+)', line, re.IGNORECASE)
                if not inv_match:
                    inv_match = re.search(r'(?:invoice|inv)\s*(?:#|no\.?|num\.?)\s+([A-Za-z0-9\-_]+)', line, re.IGNORECASE)
                if inv_match and inv_match.group(1).lower() in ["or", "and", "is", "for", "to", "the", "of", "totals", "total", "number"]:
                    inv_match = None
                if inv_match:
                    result["invoice_number"] = inv_match.group(1).strip()

            # Invoice date
            if not result["invoice_date"]:
                date_match = re.search(r'(?:invoice\s*date|date)[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})', line, re.IGNORECASE)
                if date_match:
                    result["invoice_date"] = date_match.group(1).strip()

            # Vendor / Customer
            if not result["vendor_name"]:
                vendor_match = re.search(r'(?:from|vendor|seller)[:\s]+([A-Za-z0-9\s,\.\&]+)', line, re.IGNORECASE)
                if vendor_match:
                    result["vendor_name"] = vendor_match.group(1).strip()

            if not result["customer_name"]:
                cust_match = re.search(r'(?:to|bill\s*to|customer|client)[:\s]+([A-Za-z0-9\s,\.\&]+)', line, re.IGNORECASE)
                if cust_match:
                    result["customer_name"] = cust_match.group(1).strip()

            # Totals
            if "subtotal" in lower or "sub total" in lower or "net amount" in lower:
                num = self._find_trailing_number(line)
                if num is not None:
                    result["subtotal"] = num
            elif "tax" in lower or "vat" in lower or "gst" in lower:
                if "tax rate" not in lower and "tax id" not in lower:
                    num = self._find_trailing_number(line)
                    if num is not None:
                        result["tax_amount"] = num
            elif "discount" in lower:
                num = self._find_trailing_number(line)
                if num is not None:
                    result["discount"] = abs(num)
            elif "total" in lower and "subtotal" not in lower:
                num = self._find_trailing_number(line)
                if num is not None:
                    result["total_amount"] = num
            elif "cash paid" in lower or "amount paid" in lower:
                num = self._find_trailing_number(line)
                if num is not None:
                    result["cash_paid"] = num
            elif "change" in lower or "change due" in lower:
                num = self._find_trailing_number(line)
                if num is not None:
                    result["change"] = num

            # Line item detection: look for pattern like: Description | Qty | Unit Price | Total
            # e.g.: "Consulting Services 10 150.00 1500.00" or "Widget A 2 $50.00 $100.00"
            line_item = self._parse_line_item(line)
            if line_item:
                line_items.append(line_item)

        if line_items:
            result["line_items"] = line_items

        return result

    def _extract_balance_sheet_nlp(self, lines: List[str], full_text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "statement_title": "Balance Sheet",
            "entity_name": None,
            "reporting_period": None,
            "currency": "USD",
            "total_assets": None,
            "total_liabilities": None,
            "total_equity": None,
            "total_capital_and_liabilities": None,
            "asset_line_items": [],
            "liability_line_items": [],
            "equity_line_items": [],
            "additional_fields": {}
        }

        current_section = "assets"
        for line in lines:
            lower = line.lower()

            if "period" in lower or "as of" in lower or "as at" in lower or "31 december" in lower:
                if not result["reporting_period"]:
                    result["reporting_period"] = line

            if "assets" in lower and "total" not in lower:
                current_section = "assets"
            elif "liabilities" in lower and "total" not in lower:
                current_section = "liabilities"
            elif "equity" in lower or "capital" in lower and "total" not in lower:
                current_section = "equity"

            # Check totals
            if "total assets" in lower:
                result["total_assets"] = self._find_trailing_number(line)
            elif "total liabilities" in lower and "equity" not in lower:
                result["total_liabilities"] = self._find_trailing_number(line)
            elif "total equity" in lower or "total shareholders" in lower:
                result["total_equity"] = self._find_trailing_number(line)
            elif "total capital and liabilities" in lower or "total liabilities and equity" in lower:
                result["total_capital_and_liabilities"] = self._find_trailing_number(line)
            else:
                # Individual item line
                item = self._parse_financial_line_item(line)
                if item and item["amount"] is not None:
                    if current_section == "assets":
                        result["asset_line_items"].append(item)
                    elif current_section == "liabilities":
                        result["liability_line_items"].append(item)
                    elif current_section == "equity":
                        result["equity_line_items"].append(item)

        return result

    def _extract_pnl_nlp(self, lines: List[str], full_text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "statement_title": "Profit and Loss Statement",
            "entity_name": None,
            "reporting_period": None,
            "currency": "USD",
            "revenue": None,
            "interest_earned": None,
            "other_income": None,
            "total_income": None,
            "cost_of_sales": None,
            "cogs": None,
            "gross_profit": None,
            "operating_expenses": None,
            "interest_expended": None,
            "provisions": None,
            "total_expenditure": None,
            "operating_profit": None,
            "tax": None,
            "net_profit_before_minority_interest": None,
            "minority_interest": None,
            "net_profit": None,
            "brought_forward_profit": None,
            "total_appropriations": None,
            "income_line_items": [],
            "expense_line_items": [],
            "additional_fields": {}
        }

        for line in lines:
            lower = line.lower()
            num = self._find_trailing_number(line)

            if "revenue" in lower or "total sales" in lower or "turnover" in lower:
                result["revenue"] = num
            elif "interest earned" in lower:
                result["interest_earned"] = num
            elif "other income" in lower:
                result["other_income"] = num
            elif "total income" in lower:
                result["total_income"] = num
            elif "cost of sales" in lower or "cost of goods" in lower or "cogs" in lower:
                result["cost_of_sales"] = num
                result["cogs"] = num
            elif "gross profit" in lower:
                result["gross_profit"] = num
            elif "operating expenses" in lower or "total opex" in lower:
                result["operating_expenses"] = num
            elif "interest expended" in lower or "finance costs" in lower:
                result["interest_expended"] = num
            elif "provisions" in lower or "contingencies" in lower:
                result["provisions"] = num
            elif "total expenditure" in lower or "total expenses" in lower:
                result["total_expenditure"] = num
            elif "operating profit" in lower:
                result["operating_profit"] = num
            elif "income tax" in lower or "tax expense" in lower or (lower.startswith("tax") and num is not None):
                result["tax"] = num
            elif "profit before minority interest" in lower or "before minority" in lower:
                result["net_profit_before_minority_interest"] = num
            elif "minority interest" in lower:
                result["minority_interest"] = num
            elif "net profit" in lower or "net income" in lower or "profit for the period" in lower:
                result["net_profit"] = num
            elif "brought forward" in lower:
                result["brought_forward_profit"] = num
            elif "appropriation" in lower:
                result["total_appropriations"] = num

        return result

    def _extract_cash_flow_nlp(self, lines: List[str], full_text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "statement_title": "Cash Flow Statement",
            "entity_name": None,
            "reporting_period": None,
            "currency": "USD",
            "operating_cash_flow": None,
            "investing_cash_flow": None,
            "financing_cash_flow": None,
            "fx_adjustment": 0.0,
            "net_change_in_cash": None,
            "opening_cash": None,
            "cash_acquired_adjustments": 0.0,
            "closing_cash": None,
            "operating_activities": [],
            "investing_activities": [],
            "financing_activities": [],
            "additional_fields": {}
        }

        for line in lines:
            lower = line.lower()
            num = self._find_trailing_number(line)

            if "operating" in lower and ("cash" in lower or "activities" in lower or "net" in lower):
                if num is not None and result["operating_cash_flow"] is None:
                    result["operating_cash_flow"] = num
            elif "investing" in lower and ("cash" in lower or "activities" in lower or "net" in lower):
                if num is not None and result["investing_cash_flow"] is None:
                    result["investing_cash_flow"] = num
            elif "financing" in lower and ("cash" in lower or "activities" in lower or "net" in lower):
                if num is not None and result["financing_cash_flow"] is None:
                    result["financing_cash_flow"] = num
            elif "fx" in lower or "foreign exchange" in lower or "translation" in lower:
                if num is not None:
                    result["fx_adjustment"] = num
            elif "net increase" in lower or "net decrease" in lower or "net change in cash" in lower:
                if num is not None:
                    result["net_change_in_cash"] = num
            elif "opening cash" in lower or "cash at beginning" in lower or "beginning of period" in lower:
                if num is not None:
                    result["opening_cash"] = num
            elif "closing cash" in lower or "cash at end" in lower or "end of period" in lower:
                if num is not None:
                    result["closing_cash"] = num

        return result

    def _find_trailing_number(self, line: str) -> Optional[float]:
        """Finds number (including parenthesized (5,000) or -$5000) at or near end of line."""
        # Check parenthesized negative first: (1,234.56)
        matches = re.findall(r'[\(\[]\s*[\$€£₹]?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*[\)\]]', line)
        if matches:
            return parse_financial_number(matches[-1])

        # Otherwise check normal numbers with optional minus sign
        matches = re.findall(r'[-+]?\s*[\$€£₹]?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?', line)
        if matches:
            for m in reversed(matches):
                val = parse_financial_number(m)
                if val is not None:
                    return val
        return None

    def _parse_line_item(self, line: str) -> Optional[Dict[str, Any]]:
        """Parses description, quantity, unit price, total from a table row."""
        tokens = line.split()
        if len(tokens) < 3:
            return None

        # Ignore header rows
        if any(h in line.lower() for h in ["description", "unit price", "quantity", "subtotal", "total amount"]):
            return None

        # Look for numbers at the end of tokens
        numbers = []
        desc_tokens = []
        for t in reversed(tokens):
            num = parse_financial_number(t)
            if num is not None and len(numbers) < 3:
                numbers.append(num)
            else:
                desc_tokens.append(t)

        if len(numbers) >= 2:
            numbers.reverse()
            desc = " ".join(reversed(desc_tokens)).strip()
            if not desc:
                desc = "Item"
            if len(numbers) == 2:
                # Qty, Total
                return {
                    "description": desc,
                    "quantity": numbers[0],
                    "unit_price": round(numbers[1] / numbers[0], 2) if numbers[0] else numbers[1],
                    "amount": numbers[1],
                    "discount": 0.0,
                    "tax": None
                }
            elif len(numbers) >= 3:
                # Qty, Unit Price, Amount
                return {
                    "description": desc,
                    "quantity": numbers[0],
                    "unit_price": numbers[1],
                    "amount": numbers[2],
                    "discount": 0.0,
                    "tax": None
                }
        return None

    def _parse_financial_line_item(self, line: str) -> Optional[Dict[str, Any]]:
        num = self._find_trailing_number(line)
        if num is None:
            return None
        # Name is line minus the number
        name = re.sub(r'[\(\[]?[\$€£₹]?\s*[\d,]+\.?\d*[\)\]]?', '', line).strip()
        if len(name) < 2:
            name = "Line Item"
        return {"name": name, "amount": num, "comparative_amount": None}

    def _clean_numeric_fields(self, document_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures all string numbers are converted with parenthesis negative handling."""
        if not isinstance(data, dict):
            return data

        cleaned = dict(data)
        for k, v in cleaned.items():
            if isinstance(v, str) and k not in ("invoice_number", "invoice_date", "vendor_name", "customer_name", "currency", "statement_title", "entity_name", "reporting_period"):
                parsed = parse_financial_number(v)
                if parsed is not None:
                    cleaned[k] = parsed
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, dict):
                        new_item = dict(item)
                        for ik, iv in new_item.items():
                            if isinstance(iv, str) and ik in ("quantity", "unit_price", "amount", "total", "discount", "tax"):
                                p = parse_financial_number(iv)
                                if p is not None:
                                    new_item[ik] = p
                        new_list.append(new_item)
                    else:
                        new_list.append(item)
                cleaned[k] = new_list
        return cleaned

extraction_service = ExtractionService()
