import re
from typing import Dict, List, Optional, Any
from backend.app.schemas.extraction import ExtractedField, FieldEvidence
from backend.app.services.ocr_service import DocumentTextResult

class EvidenceService:
    @staticmethod
    def find_evidence_for_field(
        field_name: str,
        value: Any,
        doc_text: DocumentTextResult,
        label_keywords: Optional[List[str]] = None
    ) -> ExtractedField:
        """
        Searches doc_text pages for traceable source evidence and calculates explainable confidence:
        - If field is None/empty: returns ExtractedField(value=None, confidence=None, evidence=None)
        - If exact value string and a label keyword appear on a line: confidence = 0.98 (Strong evidence)
        - If exact value string appears on a line: confidence = 0.88 (Moderate evidence)
        - If field is present but value text not directly matched: confidence = 0.75 (Extracted via structure)
        """
        if value is None or value == "":
            return ExtractedField(value=None, confidence=None, evidence=None)

        val_str = str(value).strip()
        # For floating numbers, also search with commas and decimals (e.g. 13125.0 -> 13,125.00 or 13,125)
        search_terms = [val_str]
        if isinstance(value, (int, float)):
            num_val = float(value)
            formatted_commas = f"{num_val:,.2f}"
            search_terms.extend([
                formatted_commas,
                f"{num_val:,.0f}",
                f"{num_val:.2f}",
                f"{num_val:g}"
            ])
            # If negative, also check (1,234.56)
            if num_val < 0:
                abs_val = abs(num_val)
                search_terms.extend([
                    f"({abs_val:,.2f})",
                    f"({abs_val:,.0f})",
                    f"({abs_val:.2f})",
                    f"[{abs_val:,.2f}]"
                ])

        label_keywords = label_keywords or [field_name.replace("_", " ")]

        best_evidence: Optional[FieldEvidence] = None
        best_confidence: float = 0.75

        for page in doc_text.pages:
            lines = page.text.split("\n")
            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                line_lower = line_str.lower()
                for term in search_terms:
                    if term.lower() in line_lower:
                        # Check if any label keyword is also in the line
                        has_keyword = any(kw.lower() in line_lower for kw in label_keywords)
                        if has_keyword:
                            return ExtractedField(
                                value=value,
                                confidence=0.98,
                                evidence=FieldEvidence(
                                    source_text=line_str,
                                    page_number=page.page_number
                                )
                            )
                        elif best_confidence < 0.88:
                            best_confidence = 0.88
                            best_evidence = FieldEvidence(
                                source_text=line_str,
                                page_number=page.page_number
                            )

        if best_evidence:
            return ExtractedField(
                value=value,
                confidence=best_confidence,
                evidence=best_evidence
            )

        # Value was extracted but specific line wasn't isolated
        first_page = doc_text.pages[0].page_number if doc_text.pages else 1
        return ExtractedField(
            value=value,
            confidence=0.75,
            evidence=FieldEvidence(
                source_text=f"[Extracted from document body]",
                page_number=first_page
            )
        )

    @classmethod
    def enrich_extraction_with_evidence(
        cls,
        doc_type: str,
        extracted_dict: Dict[str, Any],
        doc_text: DocumentTextResult
    ) -> Dict[str, ExtractedField]:
        """Maps key financial fields to traceable evidence."""
        evidence_map: Dict[str, ExtractedField] = {}

        field_keyword_map = {
            # Invoices
            "invoice_number": ["invoice #", "inv no", "invoice no", "number"],
            "invoice_date": ["date", "invoice date", "dated"],
            "subtotal": ["subtotal", "sub total", "amount"],
            "tax_amount": ["tax", "vat", "gst", "sales tax"],
            "discount": ["discount", "disc"],
            "total_amount": ["total", "total amount", "amount due", "balance due"],
            "cash_paid": ["cash", "paid", "amount paid"],
            "change": ["change", "change due"],

            # Balance Sheet
            "total_assets": ["total assets", "assets total"],
            "total_liabilities": ["total liabilities", "liabilities total"],
            "total_equity": ["total equity", "shareholders equity", "total capital"],
            "total_capital_and_liabilities": ["total capital and liabilities", "total equity and liabilities"],

            # Profit & Loss
            "revenue": ["revenue", "turnover", "total sales", "total revenue"],
            "gross_profit": ["gross profit", "gross margin"],
            "operating_expenses": ["operating expenses", "total opex"],
            "operating_profit": ["operating profit", "operating income"],
            "net_profit": ["net profit", "net income", "profit for the period"],

            # Cash Flow
            "operating_cash_flow": ["operating activities", "cash from operations", "operating cash flow"],
            "investing_cash_flow": ["investing activities", "cash from investing"],
            "financing_cash_flow": ["financing activities", "cash from financing"],
            "net_change_in_cash": ["net increase in cash", "net change in cash"],
            "opening_cash": ["opening cash", "beginning of year", "cash at beginning"],
            "closing_cash": ["closing cash", "end of year", "cash at end"]
        }

        for field_name, keywords in field_keyword_map.items():
            if field_name in extracted_dict and extracted_dict[field_name] is not None:
                val = extracted_dict[field_name]
                evidence_map[field_name] = cls.find_evidence_for_field(
                    field_name=field_name,
                    value=val,
                    doc_text=doc_text,
                    label_keywords=keywords
                )

        return evidence_map

    @staticmethod
    def calculate_overall_confidence(evidence_map: Dict[str, ExtractedField]) -> Optional[float]:
        """Computes deterministic average confidence across all tracked fields."""
        scores = [ef.confidence for ef in evidence_map.values() if ef.confidence is not None]
        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)

evidence_service = EvidenceService()
