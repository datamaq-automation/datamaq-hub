"""Caso de uso para auto-generar designaciones históricas a partir de líneas huérfanas de un recibo."""

import uuid
from datetime import date

from src.application.dtos.horarios_docencia_dto import DesignacionDocenteDTO
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import (
    MotivoCese,
    PeriodoVigencia,
    SituacionRevista,
)
from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.recibos.ports import ReciboRepositoryPort
from src.domain.recibos.services import ConciliadorReciboDocenteService


class CrearDesignacionesDesdeReciboUseCase:
    """Auto-crea y persiste designaciones históricas a partir de pagos en recibo sin cargo registrado."""

    def __init__(
        self,
        recibo_repository: ReciboRepositoryPort,
        designacion_repository: DesignacionDocenteRepositoryPort,
        conciliador: ConciliadorReciboDocenteService | None = None,
    ) -> None:
        self._recibo_repository = recibo_repository
        self._designacion_repository = designacion_repository
        self._conciliador = (
            conciliador
            if conciliador is not None
            else ConciliadorReciboDocenteService()
        )

    def execute(
        self,
        id_recibo: str,
        secuencias: list[str] | None = None,
    ) -> list[DesignacionDocenteDTO]:
        recibo = self._recibo_repository.obtener_por_id(id_recibo)
        if not recibo:
            raise ReciboNotFoundError(
                f"Recibo de sueldo con ID '{id_recibo}' no encontrado."
            )

        cuit_normalizado = recibo.agente.cuil.replace("-", "").strip()
        historial = self._designacion_repository.obtener_historial(cuit_normalizado)

        resultado = self._conciliador.conciliar(
            recibo=recibo, designaciones=list(historial)
        )

        huerfanas = resultado.lineas_huerfanas_recibo
        if secuencias:
            sec_set = {s.strip() for s in secuencias}
            huerfanas = [h for h in huerfanas if h.secuencia in sec_set]

        # Mapear liquidaciones detalladas para obtener datos adicionales
        liq_map = {
            f"{l.establecimiento.codigo or ''}-{l.cargo.secuencia}": l
            for l in recibo.liquidaciones
        }

        creadas: list[DesignacionDocenteDTO] = []
        for h in huerfanas:
            liq = liq_map.get(f"{h.escuela_codigo}-{h.secuencia}")
            cargo_nombre = (
                liq.cargo.cargo_real
                if liq and liq.cargo.cargo_real
                else f"Cargo Secuencia {h.secuencia}"
            )
            establecimiento_nombre = (
                liq.establecimiento.nombre
                if liq and liq.establecimiento.nombre
                else f"Establecimiento {h.escuela_codigo}"
            )
            distrito = (
                liq.establecimiento.distrito
                if liq and liq.establecimiento.distrito
                else ""
            )

            # Determinar fechas de vigencia a partir del período liquidado (YYYY-MM)
            anio, mes = [int(p) for p in h.periodo_liquidado.split("-")]
            fecha_desde = date(anio, mes, 1)

            # Fin de mes
            if mes in (1, 3, 5, 7, 8, 10, 12):
                ultimo_dia = 31
            elif mes in (4, 6, 9, 11):
                ultimo_dia = 30
            else:
                ultimo_dia = (
                    29
                    if (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0))
                    else 28
                )
            fecha_hasta = date(anio, mes, ultimo_dia) if h.es_retroactivo else None

            # Situación de revista
            revista_str = (h.revista_recibo or "SUPLENTE").upper()
            revista_enum = SituacionRevista.SUPLENTE
            if "TIT" in revista_str:
                revista_enum = SituacionRevista.TITULAR
            elif "PROV" in revista_str:
                revista_enum = SituacionRevista.PROVISIONAL

            nueva_desig = DesignacionDocente(
                id_designacion=str(uuid.uuid4()),
                docente_cuit=cuit_normalizado,
                ige="",
                establecimiento=establecimiento_nombre,
                distrito=distrito,
                cargo_asignatura=cargo_nombre,
                revista=revista_enum,
                modulos=int(h.modulos_recibo) if h.modulos_recibo else 0,
                es_cargo_base=False,
                vigencia=PeriodoVigencia(
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                ),
                motivo_cese=None if fecha_hasta is None else MotivoCese.FIN_LICENCIA,
                observaciones=f"Auto-creada desde recibo {recibo.agente.mes_pago} (período devengado {h.periodo_liquidado})",
                cupof="",
                secuencia=int(h.secuencia) if h.secuencia.isdigit() else None,
                codigo_acto="",
                escuela_numero=h.escuela_codigo,
                reemplaza_a="",
                articulo_licencia="",
                horarios=(),
            )

            guardada = self._designacion_repository.guardar(nueva_desig)
            creadas.append(HorariosDocenciaMapper.designacion_to_dto(guardada))

        return creadas
