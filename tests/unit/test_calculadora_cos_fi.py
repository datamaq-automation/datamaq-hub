"""Unit tests para el servicio y caso de uso de la calculadora de factor de potencia cos fi."""

import pytest

from src.application.dtos.calculadora_cos_fi_dtos import CalculoCosFiRequestDTO
from src.application.use_cases.calcular_recargo_cos_fi import (
    CalcularRecargoCosFiUseCase,
)
from src.domain.calculadora_cos_fi.entities import SolicitudCalculoCosFi
from src.domain.calculadora_cos_fi.exceptions import (
    FacturaInvalidaException,
    PotenciaInvalidaException,
    ValorCosFiInvalidoException,
)
from src.domain.calculadora_cos_fi.services import CalculadoraCosFiService
from src.domain.calculadora_cos_fi.value_objects import EstadoCosFi


def test_cos_fi_optimo_sin_recargos() -> None:
    """Verifica que un cos fi >= 0.95 no genera multas ni requiere capacitores."""
    solicitud = SolicitudCalculoCosFi(
        potencia_kw=50.0,
        cos_fi_actual=0.96,
        factura_base_ars=500000.0,
    )
    resultado = CalculadoraCosFiService.calcular_penalidad(solicitud)

    assert resultado.estado == EstadoCosFi.OPTIMO
    assert resultado.recargo_porcentaje == 0.0
    assert resultado.recargo_mensual_ars == 0.0
    assert resultado.recargo_anual_ars == 0.0
    assert resultado.potencia_reactiva_kvar == 0.0
    assert resultado.banco_capacitores_recomendado_kvar == 0.0


def test_cos_fi_multa_leve_y_dimensionamiento() -> None:
    """Verifica el cálculo de recargo y selección de escalón de banco comercial."""
    solicitud = SolicitudCalculoCosFi(
        potencia_kw=100.0,
        cos_fi_actual=0.88,
        factura_base_ars=1000000.0,
    )
    resultado = CalculadoraCosFiService.calcular_penalidad(solicitud)

    assert resultado.estado == EstadoCosFi.MULTA_LEVE
    # (0.95 / 0.88 - 1) * 100 = 7.9545 -> 7.95%
    assert resultado.recargo_porcentaje == 7.95
    assert resultado.recargo_mensual_ars == 79500.0
    assert resultado.recargo_anual_ars == 954000.0
    assert resultado.potencia_reactiva_kvar > 15.0
    assert resultado.banco_capacitores_recomendado_kvar == 25.0


def test_cos_fi_multa_critica() -> None:
    """Verifica que cos fi < 0.85 se clasifica como multa crítica."""
    solicitud = SolicitudCalculoCosFi(
        potencia_kw=50.0,
        cos_fi_actual=0.75,
        factura_base_ars=800000.0,
    )
    resultado = CalculadoraCosFiService.calcular_penalidad(solicitud)

    assert resultado.estado == EstadoCosFi.MULTA_CRITICA
    # (0.95 / 0.75 - 1) * 100 = 26.67%
    assert resultado.recargo_porcentaje == 26.67
    assert resultado.recargo_mensual_ars == 213360.0
    assert resultado.banco_capacitores_recomendado_kvar >= 30.0


def test_validaciones_excepciones() -> None:
    """Verifica que valores inválidos lanzan las excepciones de dominio correctas."""
    with pytest.raises(ValorCosFiInvalidoException):
        CalculadoraCosFiService.calcular_penalidad(
            SolicitudCalculoCosFi(potencia_kw=50.0, cos_fi_actual=0.0)
        )

    with pytest.raises(ValorCosFiInvalidoException):
        CalculadoraCosFiService.calcular_penalidad(
            SolicitudCalculoCosFi(potencia_kw=50.0, cos_fi_actual=1.05)
        )

    with pytest.raises(PotenciaInvalidaException):
        CalculadoraCosFiService.calcular_penalidad(
            SolicitudCalculoCosFi(potencia_kw=-10.0, cos_fi_actual=0.8)
        )

    with pytest.raises(FacturaInvalidaException):
        CalculadoraCosFiService.calcular_penalidad(
            SolicitudCalculoCosFi(
                potencia_kw=50.0, cos_fi_actual=0.8, factura_base_ars=-500.0
            )
        )


def test_calcular_recargo_cos_fi_use_case() -> None:
    """Verifica que el caso de uso genera el link de WhatsApp dinámico y los DTOs."""
    use_case = CalcularRecargoCosFiUseCase(whatsapp_phone="5491136528392")
    request = CalculoCosFiRequestDTO(
        potencia_kw=60.0,
        cos_fi_actual=0.78,
        factura_base_ars=1200000.0,
        empresa="Inyección Plástica Pilar",
    )
    response = use_case.execute(request)

    assert response.cos_fi_actual == 0.78
    assert response.cos_fi_objetivo == 0.95
    assert response.recargo_porcentaje == 21.79
    assert response.recargo_mensual_ars == 261480.0
    assert response.banco_capacitores_recomendado_kvar >= 25.0
    assert "https://wa.me/5491136528392?text=" in response.whatsapp_url
    assert (
        "Inyecci%C3%B3n" not in response.whatsapp_url
        or "%C3%B3" in response.whatsapp_url
    )
