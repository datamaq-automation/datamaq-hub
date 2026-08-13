"""Unit tests for presenters."""

import json

from src.adapters.presenters.error_presenter import ErrorPresenter
from src.adapters.presenters.receipt_presenter import ReceiptPresenter
from src.application.dtos.receipt_dto import (
    AgenteDTO,
    EmpleadorDTO,
    ReceiptResponseDTO,
    TotalesConsolidadosDTO,
)
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


def test_error_presenter():
    res_pdf = ErrorPresenter.format_domain_error(InvalidPDFError("Corrupt PDF"))
    assert res_pdf.status_code == 400
    body_pdf = json.loads(res_pdf.body.decode())
    assert body_pdf["success"] is False
    assert body_pdf["error"]["code"] == "INVALID_PDF_ERROR"

    res_parse = ErrorPresenter.format_domain_error(ReceiptParsingError("Failed parse"))
    assert res_parse.status_code == 422
    body_parse = json.loads(res_parse.body.decode())
    assert body_parse["error"]["code"] == "RECEIPT_PARSING_ERROR"
