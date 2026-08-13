"""Unit tests for validators and text helpers."""

from src.utils.text_helpers import (
    extract_cuil,
    extract_dni,
    normalize_text,
    parse_currency_amount,
)
from src.utils.validators import (
    format_cuit_cuil,
    validate_cuit_cuil,
    validate_dni,
)


def test_validate_cuit_cuil():
    # Valid CUILs
    assert validate_cuit_cuil("20-36528392-4") is True
    assert validate_cuit_cuil("20365283924") is True
    assert validate_cuit_cuil("30-62739371-3") is True

    # Invalid CUILs
    assert validate_cuit_cuil("20-36528392-9") is False
    assert validate_cuit_cuil("123") is False
    assert validate_cuit_cuil("") is False


def test_validate_dni():
    assert validate_dni("36528392") is True
    assert validate_dni("1234567") is True
    assert validate_dni("12345") is False
    assert validate_dni("123456789") is False


def test_format_cuit_cuil():
    assert format_cuit_cuil("20365283924") == "20-36528392-4"
    assert format_cuit_cuil("20-36528392-4") == "20-36528392-4"


def test_parse_currency_amount():
    assert parse_currency_amount("446146.21") == 446146.21
    assert parse_currency_amount("2.585.423,32") == 2585423.32
    assert parse_currency_amount("1450,50") == 1450.50
    assert parse_currency_amount("$ 1.200,00") == 1200.00
    assert parse_currency_amount(150.75) == 150.75
    assert parse_currency_amount(None) == 0.0
    assert parse_currency_amount("") == 0.0


def test_normalize_text():
    assert normalize_text("  BUSTOS  AGUSTÁN  ") == "BUSTOS AGUSTÍN"
    assert (
        normalize_text("ESCUELA DE EDUCACI?N SECUNDARI")
        == "ESCUELA DE EDUCACIÓN SECUNDARI"
    )
    assert normalize_text("ESCUELA DE EDUCACIÓ") == "ESCUELA DE EDUCACIÓN"


def test_extract_cuil_and_dni():
    sample_text = "Agente BUSTOS AGUSTIN DNI 36528392 CUIL 20-36528392-4 mes 07/2026"
    assert extract_cuil(sample_text) == "20-36528392-4"
    assert extract_dni(sample_text) == "36528392"
