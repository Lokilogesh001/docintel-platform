from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class FieldEvidence(BaseModel):
    source_text: Optional[str] = None
    page_number: Optional[int] = 1

class ExtractedField(BaseModel):
    value: Any = None
    confidence: Optional[float] = None
    evidence: Optional[FieldEvidence] = None

class InvoiceLineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    discount: Optional[float] = 0.0
    tax: Optional[float] = None
    amount: Optional[float] = None  # line_total
    page_number: Optional[int] = 1

class InvoiceExtraction(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    currency: Optional[str] = "USD"
    purchase_order_number: Optional[str] = None
    payment_terms: Optional[str] = None

    line_items: List[InvoiceLineItem] = Field(default_factory=list)

    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    tax_rate: Optional[float] = None
    discount: Optional[float] = 0.0
    shipping_amount: Optional[float] = None
    total_amount: Optional[float] = None
    cash_paid: Optional[float] = None
    change: Optional[float] = None

    # Evidence traces for major fields
    field_evidence: Dict[str, ExtractedField] = Field(default_factory=dict)
    additional_fields: Dict[str, Any] = Field(default_factory=dict)

class FinancialLineItem(BaseModel):
    name: str
    category: Optional[str] = None
    amount: Optional[float] = None
    comparative_amount: Optional[float] = None
    page_number: Optional[int] = 1

class BalanceSheetExtraction(BaseModel):
    statement_title: Optional[str] = "Balance Sheet"
    entity_name: Optional[str] = None
    reporting_period: Optional[str] = None
    currency: Optional[str] = "USD"

    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    total_capital_and_liabilities: Optional[float] = None

    # Line item arrays
    asset_line_items: List[FinancialLineItem] = Field(default_factory=list)
    liability_line_items: List[FinancialLineItem] = Field(default_factory=list)
    equity_line_items: List[FinancialLineItem] = Field(default_factory=list)

    # Comparative values
    comparative_period: Optional[str] = None
    comparative_total_assets: Optional[float] = None
    comparative_total_liabilities: Optional[float] = None
    comparative_total_equity: Optional[float] = None

    field_evidence: Dict[str, ExtractedField] = Field(default_factory=dict)
    additional_fields: Dict[str, Any] = Field(default_factory=dict)

class ProfitAndLossExtraction(BaseModel):
    statement_title: Optional[str] = "Profit and Loss Statement"
    entity_name: Optional[str] = None
    reporting_period: Optional[str] = None
    currency: Optional[str] = "USD"

    # Core required fields
    revenue: Optional[float] = None
    interest_earned: Optional[float] = None
    other_income: Optional[float] = None
    total_income: Optional[float] = None

    cost_of_sales: Optional[float] = None
    cogs: Optional[float] = None
    gross_profit: Optional[float] = None

    operating_expenses: Optional[float] = None
    interest_expended: Optional[float] = None
    provisions: Optional[float] = None
    total_expenditure: Optional[float] = None

    operating_profit: Optional[float] = None
    tax: Optional[float] = None
    net_profit_before_minority_interest: Optional[float] = None
    minority_interest: Optional[float] = None
    net_profit: Optional[float] = None

    brought_forward_profit: Optional[float] = None
    total_appropriations: Optional[float] = None

    income_line_items: List[FinancialLineItem] = Field(default_factory=list)
    expense_line_items: List[FinancialLineItem] = Field(default_factory=list)

    comparative_period: Optional[str] = None
    comparative_net_profit: Optional[float] = None

    field_evidence: Dict[str, ExtractedField] = Field(default_factory=dict)
    additional_fields: Dict[str, Any] = Field(default_factory=dict)

class CashFlowExtraction(BaseModel):
    statement_title: Optional[str] = "Cash Flow Statement"
    entity_name: Optional[str] = None
    reporting_period: Optional[str] = None
    currency: Optional[str] = "USD"

    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    fx_adjustment: Optional[float] = 0.0
    net_change_in_cash: Optional[float] = None

    opening_cash: Optional[float] = None
    cash_acquired_adjustments: Optional[float] = 0.0
    closing_cash: Optional[float] = None

    operating_activities: List[FinancialLineItem] = Field(default_factory=list)
    investing_activities: List[FinancialLineItem] = Field(default_factory=list)
    financing_activities: List[FinancialLineItem] = Field(default_factory=list)

    comparative_period: Optional[str] = None
    comparative_net_change_in_cash: Optional[float] = None

    field_evidence: Dict[str, ExtractedField] = Field(default_factory=dict)
    additional_fields: Dict[str, Any] = Field(default_factory=dict)
