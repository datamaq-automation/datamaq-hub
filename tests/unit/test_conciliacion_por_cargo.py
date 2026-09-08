from datetime import date

from src.adapters.gateways.pdfplumber_extractor_gateway import (
    PdfPlumberExtractorGateway,
)
from src.adapters.gateways.receipt_parsers.dgcye_parser_gateway import (
    DGCyEParserGateway,
)
from src.application.mappers.conciliacion_mapper import ConciliacionMapper
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.value_objects import PeriodoVigencia, SituacionRevista
from src.domain.recibos.entities import EstadoLineaConciliacion
from src.domain.recibos.services import ConciliadorReciboDocenteService


def test_conciliacion_por_cargo_sec_016_dos_lineas_explicadas() -> None:
    extractor = PdfPlumberExtractorGateway()
    extracted = extractor.extract_from_path("data/36528392-2026-09-07.pdf")
    parser = DGCyEParserGateway()
    recibo = parser.parse(extracted)

    # Designación de Sec 016 en IS-0199
    desig_016 = DesignacionDocente(
        id_designacion="158817a9-93ae-46c7-b7b9-fc7c439c011a",
        docente_cuit="20-36528392-4",
        ige="IGE-016",
        establecimiento="05-TIGRE IS-0199",
        distrito="05-TIGRE",
        cargo_asignatura="SM",
        revista=SituacionRevista.PROVISIONAL,
        modulos=7,
        es_cargo_base=False,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1), fecha_hasta=None),
        secuencia=16,
    )

    resultado = ConciliadorReciboDocenteService.conciliar(recibo, [desig_016])

    # Encontrar cargo 016 en cargos_conciliados
    cargos_016 = [c for c in resultado.cargos_conciliados if c.secuencia == "016"]
    assert len(cargos_016) == 1
    c016 = cargos_016[0]

    assert c016.secuencia == "016"
    assert c016.cantidad_lineas == 2
    assert len(c016.lineas_explicadas) == 2
    assert round(c016.importe_total, 2) == round(457570.43 + 24270.92, 2)
    assert c016.estado == EstadoLineaConciliacion.CONCILIADO_EXACTO
    assert c016.id_designacion == "158817a9-93ae-46c7-b7b9-fc7c439c011a"

    # Verificar que no produjo falsos huérfanos para sec 016
    huerfanas_016 = [
        l for l in resultado.lineas_huerfanas_recibo if l.secuencia == "016"
    ]
    assert len(huerfanas_016) == 0

    # DTO mapping verification
    dto = ConciliacionMapper.to_dto(resultado)
    cargos_dto_016 = [c for c in dto.cargos_conciliados if c.secuencia == "016"]
    assert len(cargos_dto_016) == 1
    assert cargos_dto_016[0].cantidad_lineas == 2
    assert len(cargos_dto_016[0].lineas_explicadas) == 2
