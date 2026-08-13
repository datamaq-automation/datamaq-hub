"""Validation utilities for Argentine identification numbers (CUIT, CUIL, DNI)."""

import re


def validate_cuit_cuil(cuit: str) -> bool:
    """Validate an Argentine CUIT/CUIL using the standard Modulo 11 check algorithm.

    Format: XX-XXXXXXXX-X or 11 consecutive digits.
    """
    if not cuit:
        return False

    clean_cuit = re.sub(r"\D", "", cuit)
    if len(clean_cuit) != 11:
        return False

    # Standard multipliers for Argentina Modulo 11
    multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    digits = [int(d) for d in clean_cuit]

    total = sum(d * m for d, m in zip(digits[:10], multipliers))
    mod = 11 - (total % 11)

    if mod == 11:
        expected_check = 0
    elif mod == 10:
        expected_check = 9
    else:
        expected_check = mod

    return digits[10] == expected_check


def validate_dni(dni: str) -> bool:
    """Validate an Argentine DNI format (numeric, between 6 and 8 digits)."""
    if not dni:
        return False
    clean_dni = re.sub(r"\D", "", dni)
    return 6 <= len(clean_dni) <= 8


def format_cuit_cuil(cuit: str) -> str:
    """Format an 11-digit string into XX-XXXXXXXX-X format."""
    clean = re.sub(r"\D", "", cuit)
    if len(clean) == 11:
        return f"{clean[:2]}-{clean[2:10]}-{clean[10]}"
    return cuit
