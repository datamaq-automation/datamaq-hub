"""Unit tests for application mappers."""

from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    ConceptoItem,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoConcepto, TipoRecibo


def test_receipt_mapper():
    entity = ReciboSueldo(
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(
            organismo_o_empresa="DGCyE PBA",
            dependencia="Administracion",
            cuit="30-62739371-3",
        ),
        agente=Agente(
            nombre_completo="DOCENTE EJEMPLO",
            tipo_documento="DNI",
            numero_documento="12345678",
            sexo="M",
            cuil="20-12345678-9",
            mes_pago="07 / 2026",
        ),
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="055 IS 0199",
                secuencia="016",
                periodo_liquidado="07 / 2026",
                fecha_pago="07/08/2026",
                orden_pago_codigo="00769",
                orden_pago_descripcion="SUELDO",
                liquido_pesos=446146.21,
            )
        ],
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="IS-0199", distrito="05-TIGRE"
                ),
                cargo=CargoDetalle(secuencia="016", situacion_revista="PROV."),
                conceptos=[
                    ConceptoItem(
                        codigo="0510",
                        descripcion="BASICO",
                        haberes=300000.0,
                        tipo=TipoConcepto.REMUNERATIVO,
                    )
                ],
                subtotal_haberes=300000.0,
                subtotal_descuentos=0.0,
                liquido_calculado=300000.0,
            )
        ],
        totales=TotalesConsolidados(
            total_haberes_remunerativos=300000.0,
            total_haberes_no_remunerativos=0.0,
            total_haberes=300000.0,
            total_descuentos=0.0,
            total_liquido=300000.0,
        ),
        metadata={"filename": "test.pdf"},
    )

    dto = ReceiptMapper.to_dto(entity)
    assert isinstance(dto, ReceiptResponseDTO)
    assert dto.agente.nombre_completo == "DOCENTE EJEMPLO"
    assert dto.empleador.cuit == "30-62739371-3"
    assert len(dto.resumen_liquidos) == 1
    assert len(dto.liquidaciones) == 1
    assert dto.totales.total_liquido == 300000.0


def test_simulation_mapper():
    from src.application.dtos.simulation_dto import DesignacionInputDTO
    from src.application.mappers.simulation_mapper import SimulationMapper
    from src.domain.liquidacion.entities import (
        ConceptoLiquidado,
        LiquidacionCargoResultado,
        LiquidacionConsolidadaResultado,
    )
    from src.domain.liquidacion.value_objects import (
        NivelCargo,
        SituacionRevista,
        TipoConceptoLiquidacion,
    )

    dto = DesignacionInputDTO(
        secuencia="016",
        escuela_codigo="IS-0199",
        escuela_nombre="ISFDyT 199",
        cargo_nivel=NivelCargo.SM,
        carga_horaria=7.0,
        situacion_revista=SituacionRevista.PROVISIONAL,
    )
    # When periodo_liquidado is None, it inherits default period
    domain = SimulationMapper.to_domain_designacion(dto, periodo_por_defecto="202608")
    assert domain.periodo_liquidado == "202608"
    assert domain.cargo_nivel == NivelCargo.SM
    assert domain.carga_horaria == 7.0

    resultado = LiquidacionConsolidadaResultado(
        periodo_proyectado="202608",
        anios_antiguedad=4,
        cargos_liquidados=(
            LiquidacionCargoResultado(
                secuencia="016",
                escuela_codigo="IS-0199",
                escuela_nombre="ISFDyT 199",
                cargo_nivel=NivelCargo.SM,
                carga_horaria=7.0,
                situacion_revista=SituacionRevista.PROVISIONAL,
                periodo_liquidado="202608",
                dias_trabajados=30.0,
                es_retroactivo=False,
                conceptos=(
                    ConceptoLiquidado(
                        codigo="0510",
                        descripcion="BASICO",
                        tipo=TipoConceptoLiquidacion.REMUNERATIVO,
                        haberes=300000.0,
                    ),
                ),
                subtotal_haberes=300000.0,
                subtotal_descuentos=0.0,
                liquido=300000.0,
            ),
        ),
        total_haberes_remunerativos=300000.0,
        total_haberes=300000.0,
        total_liquido=300000.0,
        total_liquido_regular=300000.0,
    )

    resp_dto = SimulationMapper.to_dto(resultado)
    assert resp_dto.periodo_proyectado == "202608"
    assert resp_dto.total_liquido == 300000.0
    assert len(resp_dto.cargos_liquidados) == 1
    assert resp_dto.cargos_liquidados[0].secuencia == "016"
