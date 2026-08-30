"""Use case to project teacher salaries dynamically based on active designations by CUIT."""

import calendar
from datetime import date

from src.application.dtos.simulation_dto import (
    ProyeccionEscenarioDTO,
    SimulacionSueldoCuitResponseDTO,
)
from src.application.mappers.proyeccion_sueldo_mapper import ProyeccionSueldoMapper
from src.application.mappers.simulation_mapper import SimulationMapper
from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import normalizar_cuit
from src.domain.liquidacion.entities import (
    DesignacionDocente as LiquidacionDesignacion,
)
from src.domain.liquidacion.exceptions import DocenteSinDesignacionesException
from src.domain.liquidacion.ports import ParitariaRepositoryPort
from src.domain.liquidacion.services import MotorLiquidacionDocenteService
from src.domain.recibos.ports import ReciboRepositoryPort


class ProyectarSueldoDocenteVigenteUseCase:
    """Orchestrates salary simulation by querying teacher designations and history."""

    def __init__(
        self,
        designacion_repository: DesignacionDocenteRepositoryPort,
        recibo_repository: ReciboRepositoryPort,
        paritaria_repo: ParitariaRepositoryPort,
        motor: MotorLiquidacionDocenteService | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        self._designacion_repository = designacion_repository
        self._recibo_repository = recibo_repository
        self._paritaria_repo = paritaria_repo
        self._motor = motor or MotorLiquidacionDocenteService()
        self._logger = logger or NullLogger()

    def execute(self, cuit: str, periodo: str) -> SimulacionSueldoCuitResponseDTO:
        """Executes salary projection for a given teacher's CUIT and paritary period."""
        self._logger.info(
            "Iniciando proyección salarial para CUIT %s y período %s", cuit, periodo
        )
        clean_cuit = normalizar_cuit(cuit)

        # 1. Resolver período y fechas de corte
        year = int(periodo[:4])
        month = int(periodo[4:])
        last_day = calendar.monthrange(year, month)[1]
        first_day_of_month = date(year, month, 1)
        last_day_of_month = date(year, month, last_day)

        # 2. Obtener historial de designaciones del docente
        historial = self._designacion_repository.obtener_historial(clean_cuit)

        # 3. Filtrar las designaciones activas/vigentes en el período solicitado
        cargos_activos_dominio: list[LiquidacionDesignacion] = []
        for desig in historial:
            f_desde = desig.vigencia.fecha_desde
            f_hasta = desig.vigencia.fecha_hasta

            # Activa en el mes si inicio <= fin_mes y (fin es indefinido o fin >= inicio_mes)
            if f_desde <= last_day_of_month and (
                f_hasta is None or f_hasta >= first_day_of_month
            ):
                cargo_dom = ProyeccionSueldoMapper.designacion_a_dominio(
                    designacion=desig,
                    anio=year,
                    mes=month,
                    periodo=periodo,
                )
                cargos_activos_dominio.append(cargo_dom)

        if not cargos_activos_dominio:
            self._logger.warning(
                "No se encontraron designaciones activas para el CUIT %s en el período %s",
                cuit,
                periodo,
            )
            raise DocenteSinDesignacionesException(
                f"El docente con CUIT {cuit} no posee designaciones activas en el periodo {periodo}"
            )

        # 4. Inferir antigüedad y nombre a partir del último recibo
        recibos = self._recibo_repository.listar(cuit=clean_cuit, limit=1)
        if recibos:
            ultimo = recibos[0]
            docente_nombre = ultimo.agente.nombre_completo
            anios_antiguedad = 0
            for liq in ultimo.liquidaciones:
                if (
                    liq.cargo
                    and liq.cargo.antiguedad_anios is not None
                    and liq.cargo.antiguedad_anios > anios_antiguedad
                ):
                    anios_antiguedad = liq.cargo.antiguedad_anios
        else:
            docente_nombre = f"Docente CUIT {clean_cuit}"
            anios_antiguedad = 0

        # 5. Obtener parámetros paritarios
        paritaria = self._paritaria_repo.obtener_por_periodo(periodo)

        # 6. Escenario Devengado Total (todas las altas/bajas con días proporcionales)
        res_total_dom = self._motor.liquidar_consolidado(
            designaciones=cargos_activos_dominio,
            anios_antiguedad=anios_antiguedad,
            paritaria=paritaria,
        )
        res_total_dto = SimulationMapper.to_dto(res_total_dom)

        # 7. Escenario Base Asegurado (cargos regulares de mes completo)
        cargos_base = [
            c
            for c in cargos_activos_dominio
            if c.dias_trabajados == 30.0 and not c.es_retroactivo
        ]
        if cargos_base:
            res_base_dom = self._motor.liquidar_consolidado(
                designaciones=cargos_base,
                anios_antiguedad=anios_antiguedad,
                paritaria=paritaria,
            )
            res_base_dto = SimulationMapper.to_dto(res_base_dom)
        else:
            from src.application.dtos.simulation_dto import SimulacionSueldoResponseDTO

            res_base_dto = SimulacionSueldoResponseDTO(
                periodo_proyectado=periodo,
                anios_antiguedad=anios_antiguedad,
                cargos_liquidados=[],
                total_haberes_remunerativos=0.0,
                total_haberes_no_remunerativos=0.0,
                total_haberes=0.0,
                total_descuentos=0.0,
                total_liquido=0.0,
                total_liquido_regular=0.0,
                total_liquido_retroactivos=0.0,
            )

        # 8. Consolidar la respuesta
        retroactivo = round(res_total_dto.total_liquido - res_base_dto.total_liquido, 2)

        return SimulacionSueldoCuitResponseDTO(
            cuit=clean_cuit,
            docente_nombre=docente_nombre,
            periodo_proyectado=periodo,
            anios_antiguedad=anios_antiguedad,
            modulos_totales=sum(c.carga_horaria for c in cargos_activos_dominio),
            escenario_base_asegurado=ProyeccionEscenarioDTO(
                total_haberes=res_base_dto.total_haberes,
                total_descuentos=res_base_dto.total_descuentos,
                total_liquido=res_base_dto.total_liquido,
            ),
            escenario_devengado_total=ProyeccionEscenarioDTO(
                total_haberes=res_total_dto.total_haberes,
                total_descuentos=res_total_dto.total_descuentos,
                total_liquido=res_total_dto.total_liquido,
            ),
            retroactivo_estimado=retroactivo,
            cargos_liquidados=res_total_dto.cargos_liquidados,
        )
