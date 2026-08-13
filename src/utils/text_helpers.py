"""Text normalization and numerical parsing utilities."""

import re
import unicodedata


def parse_currency_amount(val_str: str | float | None) -> float:
    """Parse string representation of currency/number into float.

    Handles formats:
    - Standard decimal: "446146.21" -> 446146.21
    - Latin/Argentinian format: "2.585.423,32" -> 2585423.32
    - Comma decimal without thousand dots: "1450,50" -> 1450.50
    - Negative amounts: "-1200.50" or "(1200.50)" -> -1200.50
    """
    if val_str is None:
        return 0.0

    if isinstance(val_str, (int, float)):
        return round(float(val_str), 2)

    raw = str(val_str).strip()
    if not raw:
        return 0.0

    is_negative = False
    if raw.startswith("(") and raw.endswith(")"):
        is_negative = True
        raw = raw[1:-1].strip()
    elif raw.startswith("-"):
        is_negative = True
        raw = raw[1:].strip()

    # Remove currency symbols and spaces
    raw = re.sub(r"[^\d.,]", "", raw)

    if not raw:
        return 0.0

    # Determine format:
    # If both '.' and ',' are present:
    # Check which one comes last
    last_dot = raw.rfind(".")
    last_comma = raw.rfind(",")

    if last_dot != -1 and last_comma != -1:
        if last_comma > last_dot:
            # Format: 1.234.567,89
            raw = raw.replace(".", "").replace(",", ".")
        else:
            # Format: 1,234,567.89
            raw = raw.replace(",", "")
    elif last_comma != -1:
        # Only comma exists: format: 1234,56
        raw = raw.replace(",", ".")
    else:
        # Only dot or digits: format: 1234.56 or 123456
        pass

    try:
        amount = float(raw)
        if is_negative:
            amount = -amount
        return round(amount, 2)
    except ValueError:
        return 0.0


def normalize_text(text: str) -> str:
    """Normalize unicode characters, fixes OCR encoding artifacts, and collapses spaces."""
    if not text:
        return ""

    # Replace common OCR mis-encodings in Latin text
    t = text.replace("AGUSTÁN", "AGUSTÍN")
    t = re.sub(r"EDUCACI\?N", "EDUCACIÓN", t)
    t = re.sub(r"\bEDUCACIÓ\b", "EDUCACIÓN", t)

    # Normalize unicode
    t = unicodedata.normalize("NFKC", t)
    # Collapse multiple spaces
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def extract_cuil(text: str) -> str | None:
    """Extract a 20/27/30/33/34-XXXXXXXX-X formatted or 11-digit CUIL/CUIT from text."""
    # Formatted CUIL: 20-36528392-4
    m = re.search(r"\b(20|23|24|27|30|33|34)-?(\d{8})-?(\d)\b", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def extract_dni(text: str) -> str | None:
    """Extract standard DNI number (7-8 digits) from text."""
    m = re.search(r"\b(DNI|DOC|DOCUMENTO)?\s*(\d{7,8})\b", text, re.IGNORECASE)
    if m:
        return m.group(2)
    return None
