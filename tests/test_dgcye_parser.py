"""Integration and domain tests for DGCyE PBA receipt parser."""

from pathlib import Path

from src.schemas.recibo import TipoConcepto, TipoRecibo
from src.services.parser_factory import ReceiptParserFactory


def test_dgcye_parser_full_flow(sample_pdf_bytes: bytes, sample_pdf_path: Path):
    """Validate full parsing of real sample DGCyE PBA PDF receipt."""
    factory = ReceiptParserFactory()
    response = factory.parse_pdf_bytes(sample_pdf_bytes, filename=sample_pdf_path.name)

    # 1. Type of receipt
    assert response.tipo_recibo == TipoRecibo.DGCYE_PBA

    # 2. Employer verification
    assert (
        "DIRECCION GENERAL DE CULTURA Y EDUCACION"
        in response.empleador.organismo_o_empresa
    )
    assert response.empleador.cuit == "30-62739371-3"

    # 3. Agent identification verification
    assert response.agente.nombre_completo == "BUSTOS AGUSTÍN"
    assert response.agente.numero_documento == "36528392"
    assert response.agente.tipo_documento == "DNI"
    assert response.agente.cuil == "20-36528392-4"
    assert "07" in response.agente.mes_pago and "2026" in response.agente.mes_pago

    # 4. Summary table (Resumen Líquidos) verification
    assert len(response.resumen_liquidos) == 14
    total_resumen = sum(item.liquido_pesos for item in response.resumen_liquidos)
    assert round(total_resumen, 2) == 2585423.32

    # Verify first and last line in summary table
    first_summary = response.resumen_liquidos[0]
    assert first_summary.secuencia == "016"
    assert first_summary.liquido_pesos == 446146.21
    assert "00769" in first_summary.orden_pago_codigo

    last_summary = response.resumen_liquidos[-1]
    assert last_summary.secuencia == "019"
    assert last_summary.liquido_pesos == 56362.75

    # 5. Liquidaciones sequence breakdowns
    assert len(response.liquidaciones) == 14

    # Check that all sequences have concepts and calculated liquids
    for liq in response.liquidaciones:
        assert len(liq.conceptos) > 0
        assert liq.subtotal_haberes > 0
        assert liq.subtotal_descuentos > 0
        assert (
            round(liq.subtotal_haberes - liq.subtotal_descuentos, 2)
            == liq.liquido_calculado
        )

    # Verify sequence 016 (First sequence detailed on page 1)
    seq_016 = next(
        liq for liq in response.liquidaciones if liq.cargo.secuencia == "016"
    )
    assert seq_016.cargo.situacion_revista == "PROV."
    assert seq_016.cargo.carga_horaria == 7.00
    assert seq_016.establecimiento.categoria == "IS-0199"
    assert seq_016.establecimiento.distrito == "05-TIGRE"
    assert seq_016.liquido_calculado == 446146.21

    # Check concepts classification in sequence 016
    concept_codes = {c.codigo: c for c in seq_016.conceptos}
    assert "0510" in concept_codes  # Básico
    assert concept_codes["0510"].tipo == TipoConcepto.REMUNERATIVO
    assert concept_codes["0510"].haberes == 300262.38

    assert "2575" in concept_codes  # Fonid
    assert concept_codes["2575"].tipo == TipoConcepto.NO_REMUNERATIVO
    assert concept_codes["2575"].haberes == 23731.31

    assert "1060" in concept_codes  # IPS
    assert concept_codes["1060"].tipo == TipoConcepto.DESCUENTO
    assert concept_codes["1060"].descuentos == 93425.16

    assert "1280" in concept_codes  # IOMA
    assert concept_codes["1280"].tipo == TipoConcepto.DESCUENTO
    assert concept_codes["1280"].descuentos == 28027.55

    # 6. Global consolidated totals
    assert response.totales.total_liquido == 2585423.32
    assert response.totales.total_haberes > 0
    assert response.totales.total_descuentos > 0
    assert response.totales.total_haberes_remunerativos > 0
    assert response.totales.total_haberes_no_remunerativos > 0

    # 7. Metadata
    assert response.metadata["total_paginas"] == 4
    assert response.metadata["total_secuencias_liquidadas"] == 14
