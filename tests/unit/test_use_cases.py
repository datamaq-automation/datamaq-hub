"""Unit tests for application use cases."""

from unittest.mock import MagicMock

from src.application.use_cases.parse_receipt import ParseReceiptUseCase
from src.domain.recibos.entities import (
    Agente,
    Empleador,
    ReciboSueldo,
    TotalesConsolidados,
)
from src.domain.recibos.ports import (
    ExtractedPDF,
    PDFExtractorPort,
    ReceiptParserPort,
    ReceiptParserRegistryPort,
)
from src.domain.recibos.value_objects import TipoRecibo


def test_parse_receipt_use_case():
    mock_extractor = MagicMock(spec=PDFExtractorPort)
    mock_parser_registry = MagicMock(spec=ReceiptParserRegistryPort)
    mock_parser = MagicMock(spec=ReceiptParserPort)

    dummy_extracted = ExtractedPDF(
        total_pages=1,
        pages=[],
        raw_full_text="dummy text",
        metadata={},
    )
    dummy_entity = ReciboSueldo(
        tipo_recibo=TipoRecibo.GENERICO,
        empleador=Empleador(organismo_o_empresa="Mock Co"),
        agente=Agente(
            nombre_completo="TEST USER",
            tipo_documento="DNI",
            numero_documento="12345678",
            cuil="20-12345678-9",
            mes_pago="07/2026",
        ),
        resumen_liquidos=[],
        liquidaciones=[],
        totales=TotalesConsolidados(total_liquido=50000.0),
        metadata={},
    )

    mock_extractor.extract_from_bytes.return_value = dummy_extracted
    mock_parser_registry.get_parser.return_value = mock_parser
    mock_parser.parse.return_value = dummy_entity

    use_case = ParseReceiptUseCase(
        extractor=mock_extractor,
        parser_registry=mock_parser_registry,
    )

    dto = use_case.execute_bytes(b"%PDF-mock", filename="sample.pdf")

    assert dto.agente.nombre_completo == "TEST USER"
    assert dto.totales.total_liquido == 50000.0
    assert dto.metadata["filename"] == "sample.pdf"

    mock_extractor.extract_from_bytes.assert_called_once_with(b"%PDF-mock")
    mock_parser_registry.get_parser.assert_called_once_with(dummy_extracted)
    mock_parser.parse.assert_called_once_with(dummy_extracted)


def test_project_salary_use_case():
    from src.application.dtos.simulation_dto import (
        DesignacionInputDTO,
        SimulacionSueldoRequestDTO,
    )
    from src.application.use_cases.project_salary import ProjectSalaryUseCase
    from src.domain.liquidacion.ports import ParitariaRepositoryPort
    from src.domain.liquidacion.value_objects import (
        NivelCargo,
        ParametrosParitaria,
        SituacionRevista,
    )

    mock_repo = MagicMock(spec=ParitariaRepositoryPort)
    mock_paritaria = ParametrosParitaria(
        periodo="202608",
        basico_por_modulo_sm=42894.625,
        basico_por_modulo_pm=22877.1325,
        bonif_0455_sm=14125.9425,
        bonif_0455_pm=9281.9325,
        bonif_0667_sm=14796.8575,
        bonif_0667_pm=9722.7825,
        bonif_2575_sm=3390.187,
        bonif_2575_pm=2009.00,
        alicuota_ips=0.1600,
        alicuota_ioma=0.0480,
        alicuota_suteba_sindicato=0.0155,
        alicuota_suteba_os=0.0464,
        tope_bonificaciones_modulos=30.0,
    )
    mock_repo.obtener_por_periodo.return_value = mock_paritaria

    use_case = ProjectSalaryUseCase(paritaria_repo=mock_repo)
    request = SimulacionSueldoRequestDTO(
        anios_antiguedad=4,
        periodo_proyectado="202608",
        designaciones=[
            DesignacionInputDTO(
                secuencia="016",
                escuela_codigo="IS-0199",
                escuela_nombre="ISFDyT 199",
                cargo_nivel=NivelCargo.SM,
                carga_horaria=7.0,
                situacion_revista=SituacionRevista.PROVISIONAL,
            )
        ],
    )

    response = use_case.execute(request)
    assert response.periodo_proyectado == "202608"
    assert response.anios_antiguedad == 4
    assert len(response.cargos_liquidados) == 1
    assert response.total_liquido > 0
    mock_repo.obtener_por_periodo.assert_called_once_with("202608")
