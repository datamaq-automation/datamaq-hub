"""Tests RED para ReceiptSummaryDTO y ReceiptController.parse_bytes(solo_resumen=...) (R-R1..R-R3)."""

from unittest.mock import MagicMock

from src.adapters.controllers.receipt_controller import ReceiptController
from src.application.dtos.receipt_dto import (
    AgenteDTO,
    CargoDTO,
    EmpleadorDTO,
    EstablecimientoDTO,
    LiquidacionSecuenciaDTO,
    ReceiptResponseDTO,
    ReceiptSummaryDTO,
    TotalesConsolidadosDTO,
)
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.recibos.value_objects import TipoRecibo


def _crear_receipt_dto() -> ReceiptResponseDTO:
    """Construye un ReceiptResponseDTO con 2 liquidaciones y totales conocidos."""
    return ReceiptResponseDTO(
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=EmpleadorDTO(organismo_o_empresa="DGCyE PBA"),
        agente=AgenteDTO(
            nombre_completo="Docente Test",
            tipo_documento="DNI",
            numero_documento="36528392",
            cuil="20-36528392-4",
            mes_pago="2026-07",
        ),
        id_recibo=None,
        resumen_liquidos=[],
        liquidaciones=[
            LiquidacionSecuenciaDTO(
                establecimiento=EstablecimientoDTO(),
                cargo=CargoDTO(secuencia="016", carga_horaria=4.0, antiguedad_anios=10),
                conceptos=[],
                subtotal_haberes=0.0,
                subtotal_descuentos=0.0,
                liquido_calculado=0.0,
            ),
            LiquidacionSecuenciaDTO(
                establecimiento=EstablecimientoDTO(),
                cargo=CargoDTO(secuencia="017", carga_horaria=6.0, antiguedad_anios=15),
                conceptos=[],
                subtotal_haberes=0.0,
                subtotal_descuentos=0.0,
                liquido_calculado=0.0,
            ),
        ],
        totales=TotalesConsolidadosDTO(
            total_haberes_remunerativos=250000.0,
            total_haberes_no_remunerativos=50000.0,
            total_haberes=300000.0,
            total_descuentos=50000.0,
            total_liquido=250000.0,
        ),
        metadata={},
    )


def test_receipt_mapper_to_summary() -> None:
    """R-R1: to_summary consolida totales, horas (Σ), antigüedad (max), período y cargos."""
    dto = _crear_receipt_dto()
    summary = ReceiptMapper.to_summary(dto)

    assert summary.total_haberes == 300000.0
    assert summary.total_descuentos == 50000.0
    assert summary.neto_a_cobrar == 250000.0
    assert summary.periodo == "2026-07"
    assert len(summary.cargos) == 2
    assert summary.horas_totales == 10.0
    assert summary.antiguedad_max_anios == 15


def test_receipt_controller_parse_bytes_solo_resumen() -> None:
    """R-R2: solo_resumen=True retorna envelope con ReceiptSummaryDTO."""
    dto = _crear_receipt_dto()
    mock_use_case = MagicMock()
    mock_use_case.execute_bytes.return_value = dto
    controller = ReceiptController(parse_use_case=mock_use_case)

    result = controller.parse_bytes(
        b"pdf", filename="recibo.pdf", persistir=False, solo_resumen=True
    )

    assert result.success is True
    assert isinstance(result.data, ReceiptSummaryDTO)
    assert result.data.neto_a_cobrar == 250000.0


def test_receipt_controller_parse_bytes_completo() -> None:
    """R-R3: solo_resumen=False mantiene envelope ReceiptResponseDTO completo."""
    dto = _crear_receipt_dto()
    mock_use_case = MagicMock()
    mock_use_case.execute_bytes.return_value = dto
    controller = ReceiptController(parse_use_case=mock_use_case)

    result = controller.parse_bytes(
        b"pdf", filename="recibo.pdf", persistir=False, solo_resumen=False
    )

    assert result.success is True
    assert isinstance(result.data, ReceiptResponseDTO)
    assert result.data.tipo_recibo == TipoRecibo.DGCYE_PBA
