import re
from typing import Optional, Union

def parse_financial_number(val: Union[str, int, float, None]) -> Optional[float]:
    """
    Parses financial strings into float:
    - Interprets parenthesized/bracketed values as negative: (5,000) -> -5000.0, [1,200.50] -> -1200.50
    - Strips currency symbols ($, EUR, GBP, USD, INR, etc.), spaces, and commas
    - Handles explicit negative signs: -5000 -> -5000.0
    - Returns None if empty or unparseable.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return None

    # Check for negative in parentheses or brackets: e.g. (1,234.56) or [1,234.56]
    is_negative = False
    paren_match = re.search(r'^\s*[\(\[]\s*(.*?)\s*[\)\]]\s*$', s)
    if paren_match:
        is_negative = True
        s = paren_match.group(1).strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()

    # Remove currency symbols, commas, quotes, and whitespace
    clean_str = re.sub(r'[^\d\.]', '', s)
    if not clean_str:
        return None

    # Handle multiple decimals if OCR introduced an artifact
    parts = clean_str.split('.')
    if len(parts) > 2:
        clean_str = "".join(parts[:-1]) + "." + parts[-1]

    try:
        num = float(clean_str)
        return -num if is_negative else num
    except ValueError:
        return None

def floats_approx_equal(a: Optional[float], b: Optional[float], tolerance: float = 0.05) -> bool:
    """
    Returns True if |a - b| <= tolerance. Returns False if either is None.
    """
    if a is None or b is None:
        return False
    return abs(a - b) <= tolerance

def calculate_variance(calculated: Optional[float], reported: Optional[float]) -> Optional[float]:
    """
    Returns rounded variance |calculated - reported|, or None if either is None.
    """
    if calculated is None or reported is None:
        return None
    return round(abs(calculated - reported), 4)
