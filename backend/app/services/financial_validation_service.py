from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.schemas.document import ValidationCheck, ValidationResult
from backend.app.utils.text_helpers import calculate_variance

class FinancialValidationService:
    def __init__(self, tolerance: Optional[float] = None):
        self.tolerance = tolerance if tolerance is not None else settings.FINANCIAL_TOLERANCE

    def validate(self, document_type: str, extracted_data: Dict[str, Any]) -> ValidationResult:
        """
        Executes deterministic Python mathematical checks for the given document type.
        Enforces:
        - Strict formula checks with tolerance
        - NOT_APPLICABLE rule when required operands are None
        - Summary overall_status and issue list
        """
        checks: List[ValidationCheck] = []
        issues: List[str] = []

        if document_type == "invoice":
            checks = self._validate_invoice(extracted_data)
        elif document_type == "balance_sheet":
            checks = self._validate_balance_sheet(extracted_data)
        elif document_type == "profit_and_loss":
            checks = self._validate_profit_and_loss(extracted_data)
        elif document_type == "cash_flow_statement":
            checks = self._validate_cash_flow(extracted_data)

        # Determine overall status and collect issues
        has_fail = False
        has_pass = False

        for c in checks:
            if c.status == "FAIL":
                has_fail = True
                issues.append(
                    f"Check '{c.name}' FAILED: Reported {c.reported_value} vs Calculated {c.calculated_value} (Variance: {c.variance})"
                )
            elif c.status == "PASS":
                has_pass = True

        if has_fail:
            overall = "FAIL"
        elif has_pass:
            overall = "PASS"
        else:
            overall = "NOT_APPLICABLE"

        return ValidationResult(
            checks=checks,
            overall_status=overall,
            issues=issues
        )

    # -------------------------------------------------------------
    # 1. INVOICE VALIDATIONS
    # -------------------------------------------------------------
    def _validate_invoice(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        # A. Line item multiplication: qty * unit_price ≈ line_total
        line_items = data.get("line_items") or []
        for idx, item in enumerate(line_items):
            qty = item.get("quantity")
            price = item.get("unit_price")
            line_tot = item.get("amount")
            name = f"line_item_{idx+1}_multiplication"
            formula = "quantity * unit_price"
            operands = {"quantity": qty, "unit_price": price}

            if qty is None or price is None or line_tot is None:
                checks.append(ValidationCheck(
                    name=name,
                    formula=formula,
                    operands=operands,
                    calculated_value=None,
                    reported_value=line_tot,
                    variance=None,
                    status="NOT_APPLICABLE",
                    message="Missing quantity, unit_price, or line_total"
                ))
            else:
                calc = round(qty * price, 2)
                var = calculate_variance(calc, line_tot)
                status = "PASS" if var <= self.tolerance else "FAIL"
                checks.append(ValidationCheck(
                    name=name,
                    formula=formula,
                    operands=operands,
                    calculated_value=calc,
                    reported_value=line_tot,
                    variance=var,
                    status=status,
                    message="Line total calculation matches" if status == "PASS" else "Line total mismatch"
                ))

        # B. Line items sum ≈ subtotal
        subtotal = data.get("subtotal")
        if line_items:
            valid_amounts = [it.get("amount") for it in line_items if it.get("amount") is not None]
            operands = {"line_totals": valid_amounts}
            if len(valid_amounts) == len(line_items) and subtotal is not None:
                calc = round(sum(valid_amounts), 2)
                var = calculate_variance(calc, subtotal)
                status = "PASS" if var <= self.tolerance else "FAIL"
                checks.append(ValidationCheck(
                    name="line_items_subtotal_check",
                    formula="sum(line_totals)",
                    operands=operands,
                    calculated_value=calc,
                    reported_value=subtotal,
                    variance=var,
                    status=status,
                    message="Line items sum matches subtotal" if status == "PASS" else "Line items sum does not match subtotal"
                ))
            else:
                checks.append(ValidationCheck(
                    name="line_items_subtotal_check",
                    formula="sum(line_totals)",
                    operands=operands,
                    calculated_value=None,
                    reported_value=subtotal,
                    variance=None,
                    status="NOT_APPLICABLE",
                    message="Missing line totals or subtotal operand"
                ))

        # C. Subtotal + Tax - Discount ≈ Total Amount
        tax = data.get("tax_amount")
        discount = data.get("discount") if data.get("discount") is not None else 0.0
        total = data.get("total_amount")

        formula_name = "invoice_total_check"
        formula_str = "subtotal + tax_amount - discount"
        operands = {"subtotal": subtotal, "tax_amount": tax, "discount": discount}

        # Mandatory NOT_APPLICABLE rule: if subtotal or total is null, or tax is null when required
        if subtotal is None or total is None or tax is None:
            checks.append(ValidationCheck(
                name=formula_name,
                formula=formula_str,
                operands=operands,
                calculated_value=None,
                reported_value=total,
                variance=None,
                status="NOT_APPLICABLE",
                message="Cannot perform check: required operand(s) are null."
            ))
        else:
            calc = round(subtotal + tax - discount, 2)
            var = calculate_variance(calc, total)
            status = "PASS" if var <= self.tolerance else "FAIL"
            checks.append(ValidationCheck(
                name=formula_name,
                formula=formula_str,
                operands=operands,
                calculated_value=calc,
                reported_value=total,
                variance=var,
                status=status,
                message="Invoice total satisfies subtotal + tax - discount" if status == "PASS" else "Invoice total mismatch"
            ))

        # D. Cash Paid - Total Amount ≈ Change
        cash_paid = data.get("cash_paid")
        change = data.get("change")
        if cash_paid is not None or change is not None:
            operands = {"cash_paid": cash_paid, "total_amount": total}
            if cash_paid is not None and total is not None and change is not None:
                calc = round(cash_paid - total, 2)
                var = calculate_variance(calc, change)
                status = "PASS" if var <= self.tolerance else "FAIL"
                checks.append(ValidationCheck(
                    name="cash_change_check",
                    formula="cash_paid - total_amount",
                    operands=operands,
                    calculated_value=calc,
                    reported_value=change,
                    variance=var,
                    status=status
                ))
            else:
                checks.append(ValidationCheck(
                    name="cash_change_check",
                    formula="cash_paid - total_amount",
                    operands=operands,
                    calculated_value=None,
                    reported_value=change,
                    variance=None,
                    status="NOT_APPLICABLE",
                    message="Missing cash_paid, total_amount, or change"
                ))

        return checks

    # -------------------------------------------------------------
    # 2. BALANCE SHEET VALIDATIONS
    # -------------------------------------------------------------
    def _validate_balance_sheet(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        total_assets = data.get("total_assets")
        total_liabilities = data.get("total_liabilities")
        total_equity = data.get("total_equity")
        total_cap_liab = data.get("total_capital_and_liabilities")

        # Check A: Total Capital & Liabilities ≈ Total Assets
        if total_cap_liab is not None or (total_liabilities is not None and total_equity is not None):
            rep_cap_liab = total_cap_liab if total_cap_liab is not None else (total_liabilities + total_equity)
            operands = {
                "total_capital_and_liabilities": rep_cap_liab,
                "total_assets": total_assets
            }
            if total_assets is not None and rep_cap_liab is not None:
                var = calculate_variance(rep_cap_liab, total_assets)
                status = "PASS" if var <= self.tolerance else "FAIL"
                checks.append(ValidationCheck(
                    name="balance_sheet_equation",
                    formula="Total Capital & Liabilities ≈ Total Assets",
                    operands=operands,
                    calculated_value=rep_cap_liab,
                    reported_value=total_assets,
                    variance=var,
                    status=status,
                    message="Balance Sheet equation holds" if status == "PASS" else "Balance sheet equation imbalance"
                ))
            else:
                checks.append(ValidationCheck(
                    name="balance_sheet_equation",
                    formula="Total Capital & Liabilities ≈ Total Assets",
                    operands=operands,
                    calculated_value=None,
                    reported_value=total_assets,
                    variance=None,
                    status="NOT_APPLICABLE",
                    message="Missing total_assets or total_capital_and_liabilities"
                ))

        # Check B: Sum of asset components ≈ Total Assets
        asset_items = data.get("asset_line_items") or []
        if asset_items:
            valid_assets = [it.get("amount") for it in asset_items if it.get("amount") is not None]
            operands = {"asset_components": valid_assets}
            if valid_assets and total_assets is not None and len(valid_assets) == len(asset_items):
                calc = round(sum(valid_assets), 2)
                var = calculate_variance(calc, total_assets)
                status = "PASS" if var <= self.tolerance else "FAIL"
                checks.append(ValidationCheck(
                    name="asset_components_sum",
                    formula="sum(asset_components)",
                    operands=operands,
                    calculated_value=calc,
                    reported_value=total_assets,
                    variance=var,
                    status=status
                ))
            else:
                checks.append(ValidationCheck(
                    name="asset_components_sum",
                    formula="sum(asset_components)",
                    operands=operands,
                    calculated_value=None,
                    reported_value=total_assets,
                    variance=None,
                    status="NOT_APPLICABLE",
                    message="Missing asset line item amounts or total_assets"
                ))

        # Check C: Sum of liability and equity components ≈ Total Capital & Liabilities
        liab_items = data.get("liability_line_items") or []
        equity_items = data.get("equity_line_items") or []
        if liab_items or equity_items:
            combined_items = liab_items + equity_items
            valid_items = [it.get("amount") for it in combined_items if it.get("amount") is not None]
            target = total_cap_liab if total_cap_liab is not None else total_assets
            operands = {"liability_and_equity_components": valid_items}
            if valid_items and target is not None and len(valid_items) == len(combined_items):
                calc = round(sum(valid_items), 2)
                var = calculate_variance(calc, target)
                status = "PASS" if var <= self.tolerance else "FAIL"
                checks.append(ValidationCheck(
                    name="liability_equity_components_sum",
                    formula="sum(capital_and_liability_components)",
                    operands=operands,
                    calculated_value=calc,
                    reported_value=target,
                    variance=var,
                    status=status
                ))
            else:
                checks.append(ValidationCheck(
                    name="liability_equity_components_sum",
                    formula="sum(capital_and_liability_components)",
                    operands=operands,
                    calculated_value=None,
                    reported_value=target,
                    variance=None,
                    status="NOT_APPLICABLE",
                    message="Missing liability/equity line item amounts or target total"
                ))

        return checks

    # -------------------------------------------------------------
    # 3. PROFIT AND LOSS VALIDATIONS
    # -------------------------------------------------------------
    def _validate_profit_and_loss(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        # Check A: Interest Earned + Other Income ≈ Total Income
        interest_earned = data.get("interest_earned")
        other_income = data.get("other_income")
        total_income = data.get("total_income")
        if total_income is None:
            total_income = data.get("revenue")

        operands = {"interest_earned": interest_earned, "other_income": other_income}
        if interest_earned is not None and other_income is not None and total_income is not None:
            calc = round(interest_earned + other_income, 2)
            var = calculate_variance(calc, total_income)
            status = "PASS" if var <= self.tolerance else "FAIL"
            checks.append(ValidationCheck(
                name="total_income_check",
                formula="interest_earned + other_income",
                operands=operands,
                calculated_value=calc,
                reported_value=total_income,
                variance=var,
                status=status
            ))
        else:
            checks.append(ValidationCheck(
                name="total_income_check",
                formula="interest_earned + other_income",
                operands=operands,
                calculated_value=None,
                reported_value=total_income,
                variance=None,
                status="NOT_APPLICABLE",
                message="Missing interest_earned or other_income"
            ))

        # Check B: Interest Expended + Operating Expenses + Provisions ≈ Total Expenditure
        int_expended = data.get("interest_expended")
        opex = data.get("operating_expenses")
        provisions = data.get("provisions")
        total_exp = data.get("total_expenditure")

        operands = {
            "interest_expended": int_expended,
            "operating_expenses": opex,
            "provisions": provisions
        }
        if int_expended is not None and opex is not None and provisions is not None and total_exp is not None:
            calc = round(int_expended + opex + provisions, 2)
            var = calculate_variance(calc, total_exp)
            status = "PASS" if var <= self.tolerance else "FAIL"
            checks.append(ValidationCheck(
                name="total_expenditure_check",
                formula="interest_expended + operating_expenses + provisions",
                operands=operands,
                calculated_value=calc,
                reported_value=total_exp,
                variance=var,
                status=status
            ))
        else:
            checks.append(ValidationCheck(
                name="total_expenditure_check",
                formula="interest_expended + operating_expenses + provisions",
                operands=operands,
                calculated_value=None,
                reported_value=total_exp,
                variance=None,
                status="NOT_APPLICABLE",
                message="Missing expenditure components or total_expenditure"
            ))

        # Check C: Total Income - Total Expenditure ≈ Net Profit before Minority Interest
        np_before_mi = data.get("net_profit_before_minority_interest")
        operands = {"total_income": total_income, "total_expenditure": total_exp}
        if total_income is not None and total_exp is not None and np_before_mi is not None:
            calc = round(total_income - total_exp, 2)
            var = calculate_variance(calc, np_before_mi)
            status = "PASS" if var <= self.tolerance else "FAIL"
            checks.append(ValidationCheck(
                name="net_profit_before_minority_interest_check",
                formula="total_income - total_expenditure",
                operands=operands,
                calculated_value=calc,
                reported_value=np_before_mi,
                variance=var,
                status=status
            ))
        else:
            checks.append(ValidationCheck(
                name="net_profit_before_minority_interest_check",
                formula="total_income - total_expenditure",
                operands=operands,
                calculated_value=None,
                reported_value=np_before_mi,
                variance=None,
                status="NOT_APPLICABLE",
                message="Missing total_income, total_expenditure, or profit before MI"
            ))

        # Check D: Profit before Minority Interest - Minority Interest ≈ Consolidated Net Profit
        mi = data.get("minority_interest")
        net_profit = data.get("net_profit")
        operands = {
            "net_profit_before_minority_interest": np_before_mi,
            "minority_interest": mi
        }
        if np_before_mi is not None and mi is not None and net_profit is not None:
            calc = round(np_before_mi - mi, 2)
            var = calculate_variance(calc, net_profit)
            status = "PASS" if var <= self.tolerance else "FAIL"
            checks.append(ValidationCheck(
                name="net_profit_attributable_check",
                formula="profit_before_minority_interest - minority_interest",
                operands=operands,
                calculated_value=calc,
                reported_value=net_profit,
                variance=var,
                status=status
            ))
        else:
            checks.append(ValidationCheck(
                name="net_profit_attributable_check",
                formula="profit_before_minority_interest - minority_interest",
                operands=operands,
                calculated_value=None,
                reported_value=net_profit,
                variance=None,
                status="NOT_APPLICABLE",
                message="Missing profit before MI, minority_interest, or net_profit"
            ))

        # Check E: Current Profit + Brought Forward Profit ≈ Total Available for Appropriation
        bf_profit = data.get("brought_forward_profit")
        appropriations = data.get("total_appropriations")
        if bf_profit is not None or appropriations is not None:
            operands = {"current_profit": net_profit, "brought_forward_profit": bf_profit}
            if net_profit is not None and bf_profit is not None and appropriations is not None:
                calc = round(net_profit + bf_profit, 2)
                var = calculate_variance(calc, appropriations)
                status = "PASS" if var <= self.tolerance else "FAIL"
                checks.append(ValidationCheck(
                    name="appropriations_check",
                    formula="current_profit + brought_forward_profit",
                    operands=operands,
                    calculated_value=calc,
                    reported_value=appropriations,
                    variance=var,
                    status=status
                ))
            else:
                checks.append(ValidationCheck(
                    name="appropriations_check",
                    formula="current_profit + brought_forward_profit",
                    operands=operands,
                    calculated_value=None,
                    reported_value=appropriations,
                    variance=None,
                    status="NOT_APPLICABLE",
                    message="Missing brought_forward_profit or total_appropriations"
                ))

        return checks

    # -------------------------------------------------------------
    # 4. CASH FLOW STATEMENT VALIDATIONS
    # -------------------------------------------------------------
    def _validate_cash_flow(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        # Check A: Operating + Investing + Financing + FX ≈ Net Change in Cash
        # (Remember: negative values in parentheses are already represented as negative floats)
        ocf = data.get("operating_cash_flow")
        icf = data.get("investing_cash_flow")
        fcf = data.get("financing_cash_flow")
        fx = data.get("fx_adjustment") if data.get("fx_adjustment") is not None else 0.0
        net_change = data.get("net_change_in_cash")

        operands = {
            "operating_cash_flow": ocf,
            "investing_cash_flow": icf,
            "financing_cash_flow": fcf,
            "fx_adjustment": fx
        }

        if ocf is not None and icf is not None and fcf is not None and net_change is not None:
            calc = round(ocf + icf + fcf + fx, 2)
            var = calculate_variance(calc, net_change)
            status = "PASS" if var <= self.tolerance else "FAIL"
            checks.append(ValidationCheck(
                name="net_change_in_cash_check",
                formula="operating_cash_flow + investing_cash_flow + financing_cash_flow + fx_adjustment",
                operands=operands,
                calculated_value=calc,
                reported_value=net_change,
                variance=var,
                status=status,
                message="Net change in cash matches sum of activities" if status == "PASS" else "Net change in cash mismatch"
            ))
        else:
            checks.append(ValidationCheck(
                name="net_change_in_cash_check",
                formula="operating_cash_flow + investing_cash_flow + financing_cash_flow + fx_adjustment",
                operands=operands,
                calculated_value=None,
                reported_value=net_change,
                variance=None,
                status="NOT_APPLICABLE",
                message="Missing cash flow activity components or reported net_change_in_cash"
            ))

        # Check B: Opening Cash + Net Change + Cash Acquired ≈ Closing Cash
        opening = data.get("opening_cash")
        acquired = data.get("cash_acquired_adjustments") if data.get("cash_acquired_adjustments") is not None else 0.0
        closing = data.get("closing_cash")

        operands = {
            "opening_cash": opening,
            "net_change_in_cash": net_change,
            "cash_acquired_adjustments": acquired
        }

        if opening is not None and net_change is not None and closing is not None:
            calc = round(opening + net_change + acquired, 2)
            var = calculate_variance(calc, closing)
            status = "PASS" if var <= self.tolerance else "FAIL"
            checks.append(ValidationCheck(
                name="closing_cash_check",
                formula="opening_cash + net_change_in_cash + cash_acquired_adjustments",
                operands=operands,
                calculated_value=calc,
                reported_value=closing,
                variance=var,
                status=status,
                message="Closing cash equals opening cash + net change" if status == "PASS" else "Closing cash mismatch"
            ))
        else:
            checks.append(ValidationCheck(
                name="closing_cash_check",
                formula="opening_cash + net_change_in_cash + cash_acquired_adjustments",
                operands=operands,
                calculated_value=None,
                reported_value=closing,
                variance=None,
                status="NOT_APPLICABLE",
                message="Missing opening_cash, net_change_in_cash, or closing_cash"
            ))

        return checks

financial_validation_service = FinancialValidationService()
