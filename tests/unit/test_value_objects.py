"""Unit tests for domain value objects."""

import pytest

from src.domain.recibos.exceptions import InvalidIdentifierError
from src.domain.recibos.value_objects import (
    CUIT,
    DNI,
    ImporteMonetario,
    TipoConcepto,
    TipoRecibo,
)


def test_cuit_validation():
    c1 = CUIT("20-36528392-4")
    assert c1.value == "20-36528392-4"
    assert c1.unformatted == "20365283924"

    c2 = CUIT("30627393713")
    assert c2.value == "30-62739371-3"

    assert CUIT.from_string("20-36528392-4") is not None
    assert CUIT.from_string("invalid") is None
    assert CUIT.from_string("") is None

    with pytest.raises(InvalidIdentifierError):
        CUIT("20-36528392-9")


def test_dni_validation():
    d1 = DNI("36528392")
    assert d1.value == "36528392"

    d2 = DNI("12.345.678")
    assert d2.value == "12345678"

    assert DNI.from_string("36528392") is not None
    assert DNI.from_string("123") is None

    with pytest.raises(InvalidIdentifierError):
        DNI("12345")


def test_importe_monetario():
    m1 = ImporteMonetario.from_raw("2.585.423,32")
    assert float(m1) == 2585423.32

    m2 = ImporteMonetario.from_raw("1450.50")
    assert float(m2) == 1450.50

    m3 = ImporteMonetario.from_raw("$ 1.200,00")
    assert float(m3) == 1200.00

    m_neg = ImporteMonetario.from_raw("-500.00")
    assert float(m_neg) == -500.00

    m_sum = m2 + 100
    assert float(m_sum) == 1550.50

    m_sub = m2 - 50.50
    assert float(m_sub) == 1400.00

    assert float(ImporteMonetario.zero()) == 0.0
    assert float(ImporteMonetario.from_raw(None)) == 0.0


def test_tipos_enum():
    assert TipoConcepto.REMUNERATIVO.value == "remunerativo"
    assert TipoConcepto.NO_REMUNERATIVO.value == "no_remunerativo"
    assert TipoConcepto.DESCUENTO.value == "descuento"
    assert TipoRecibo.DGCYE_PBA.value == "DGCYE_PBA"
    assert TipoRecibo.GENERICO.value == "GENERICO"
