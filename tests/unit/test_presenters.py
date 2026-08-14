"""Unit tests for presenters."""

from src.adapters.presenters.error_presenter import ErrorPresenter
from src.adapters.presenters.receipt_presenter import ReceiptPresenter
from src.adapters.presenters.simulation_presenter import SimulationPresenter
from src.application.dtos.receipt_dto import (
    AgenteDTO,
    EmpleadorDTO,
    ReceiptResponseDTO,
    TotalesConsolidadosDTO,
)
from src.application.dtos.simulation_dto import SimulacionSueldoResponseDTO
from src.domain.liquidacion.exceptions import LiquidacionDomainException
from src.domain.recibos.exceptions import InvalidPDFError, ReceiptParsingError
from src.domain.recibos.value_objects import TipoRecibo


def test_receipt_presenter():
    dto = ReceiptResponseDTO(
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=EmpleadorDTO(organismo_o_empresa="DGCyE"),
        agente=AgenteDTO(
            nombre_completo="BUSTOS AGUSTÍN",
            tipo_documento="DNI",
            numero_documento="36528392",
            cuil="20-36528392-4",
            mes_pago="07/2026",
        ),
        totales=TotalesConsolidadosDTO(
            total_haberes_remunerativos=100.0,
            total_haberes_no_remunerativos=0.0,
            total_haberes=100.0,
            total_descuentos=0.0,
            total_liquido=100.0,
        ),
    )

    response = ReceiptPresenter.present(dto)
    assert response.success is True
    assert response.data.agente.nombre_completo == "BUSTOS AGUSTÍN"


def test_simulation_presenter():
    dto = SimulacionSueldoResponseDTO(
        periodo_proyectado="202608",
        anios_antiguedad=4,
        cargos_liquidados=[],
        total_haberes_remunerativos=1000.0,
        total_haberes_no_remunerativos=100.0,
        total_haberes=1100.0,
        total_descuentos=200.0,
        total_liquido=900.0,
        total_liquido_regular=900.0,
        total_liquido_retroactivos=0.0,
    )
    response = SimulationPresenter.present(dto)
    assert response.success is True
    assert response.data.total_liquido == 900.0


def test_error_presenter():
    payload_pdf, status_pdf = ErrorPresenter.format_domain_error(
        InvalidPDFError("Corrupt PDF")
    )
    assert status_pdf == 400
    assert payload_pdf.success is False
    assert payload_pdf.error.code == "INVALID_PDF_ERROR"

    payload_parse, status_parse = ErrorPresenter.format_domain_error(
        ReceiptParsingError("Failed parse")
    )
    assert status_parse == 422
    assert payload_parse.error.code == "RECEIPT_PARSING_ERROR"

    payload_liq, status_liq = ErrorPresenter.format_domain_error(
        LiquidacionDomainException("Error liquidacion")
    )
    assert status_liq == 422
    assert payload_liq.error.code == "LIQUIDACION_DOMAIN_ERROR"
