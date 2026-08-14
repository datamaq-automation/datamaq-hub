"""Mapper to transform between Liquidacion Domain Entities and Simulation DTOs."""

from src.application.dtos.simulation_dto import (
    CargoLiquidadoDTO,
    ConceptoLiquidadoDTO,
    DesignacionInputDTO,
    SimulacionSueldoResponseDTO,
)
from src.domain.liquidacion.entities import (
    DesignacionDocente,
    LiquidacionConsolidadaResultado,
)


class SimulationMapper:
    """Transforms simulation domain entities to and from application DTOs."""

    @staticmethod
    def to_domain_designacion(
        dto: DesignacionInputDTO, periodo_por_defecto: str = ""
    ) -> DesignacionDocente:
        return DesignacionDocente(
            secuencia=dto.secuencia,
            escuela_codigo=dto.escuela_codigo,
            escuela_nombre=dto.escuela_nombre,
            cargo_nivel=dto.cargo_nivel,
            carga_horaria=dto.carga_horaria,
            situacion_revista=dto.situacion_revista,
            dias_trabajados=dto.dias_trabajados,
            inasistencias_paro=dto.inasistencias_paro,
            aplica_suteba=dto.aplica_suteba,
            aplica_bonificaciones_plenas=dto.aplica_bonificaciones_plenas,
            periodo_liquidado=dto.periodo_liquidado or periodo_por_defecto,
            es_retroactivo=dto.es_retroactivo,
        )

    @staticmethod
    def to_dto(entity: LiquidacionConsolidadaResultado) -> SimulacionSueldoResponseDTO:
        return SimulacionSueldoResponseDTO(
            periodo_proyectado=entity.periodo_proyectado,
            anios_antiguedad=entity.anios_antiguedad,
            cargos_liquidados=[
                CargoLiquidadoDTO(
                    secuencia=cargo.secuencia,
                    escuela_codigo=cargo.escuela_codigo,
                    escuela_nombre=cargo.escuela_nombre,
                    cargo_nivel=cargo.cargo_nivel,
                    carga_horaria=cargo.carga_horaria,
                    situacion_revista=cargo.situacion_revista,
                    periodo_liquidado=cargo.periodo_liquidado,
                    dias_trabajados=cargo.dias_trabajados,
                    es_retroactivo=cargo.es_retroactivo,
                    conceptos=[
                        ConceptoLiquidadoDTO(
                            codigo=c.codigo,
                            descripcion=c.descripcion,
                            tipo=c.tipo,
                            haberes=c.haberes,
                            descuentos=c.descuentos,
                        )
                        for c in cargo.conceptos
                    ],
                    subtotal_haberes=cargo.subtotal_haberes,
                    subtotal_descuentos=cargo.subtotal_descuentos,
                    liquido=cargo.liquido,
                )
                for cargo in entity.cargos_liquidados
            ],
            total_haberes_remunerativos=entity.total_haberes_remunerativos,
            total_haberes_no_remunerativos=entity.total_haberes_no_remunerativos,
            total_haberes=entity.total_haberes,
            total_descuentos=entity.total_descuentos,
            total_liquido=entity.total_liquido,
            total_liquido_regular=entity.total_liquido_regular,
            total_liquido_retroactivos=entity.total_liquido_retroactivos,
        )
