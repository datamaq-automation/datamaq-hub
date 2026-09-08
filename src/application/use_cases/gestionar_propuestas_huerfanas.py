"""Caso de uso para generar propuestas revisables de líneas huérfanas y alta confirmada en bulk."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from src.application.dtos.conciliacion_dto import (
    ConfirmarPropuestasDTO,
    PropuestaDesignacionDTO,
)
from src.application.dtos.horarios_docencia_dto import DesignacionDocenteDTO
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import PeriodoVigencia, SituacionRevista
from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.recibos.ports import ReciboRepositoryPort
from src.domain.recibos.services import ConciliadorReciboDocenteService


def _map_revista(raw_revista: str) -> SituacionRevista:
    upper = (raw_revista or "").upper()
    if "TIT" in upper:
        return SituacionRevista.TITULAR
    if "SUP" in upper:
        return SituacionRevista.SUPLENTE
    return SituacionRevista.PROVISIONAL


class GestionarPropuestasHuerfanasUseCase:
    """Genera borradores estructurados de designaciones desde líneas huérfanas y procesa altas confirmadas."""

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

    def obtener_propuestas(self, id_recibo: str) -> list[PropuestaDesignacionDTO]:
        """Devuelve propuestas revisables para las líneas huérfanas del recibo."""
        recibo = self._recibo_repository.obtener_por_id(id_recibo)
        if not recibo:
            raise ReciboNotFoundError(f"Recibo '{id_recibo}' no encontrado.")

        cuit_normalizado = recibo.agente.cuil.replace("-", "").strip()
        designaciones = self._designacion_repository.obtener_historial(cuit_normalizado)
        resultado = self._conciliador.conciliar(
            recibo=recibo, designaciones=list(designaciones)
        )

        # Determinar fecha base (primer día del mes de pago)
        try:
            partes = recibo.agente.mes_pago.split("-")
            fecha_inicio = f"{partes[0]}-{partes[1]}-01"
        except (IndexError, AttributeError, ValueError):
            today = datetime.now(timezone.utc).date()
            fecha_inicio = f"{today.year}-{today.month:02d}-01"

        propuestas: list[PropuestaDesignacionDTO] = []
        for h in resultado.lineas_huerfanas_recibo:
            escuela_codigo = h.escuela_codigo
            distrito = h.escuela_codigo[:3] if len(h.escuela_codigo) >= 3 else ""
            tipo_nivel = h.escuela_codigo[3:5] if len(h.escuela_codigo) >= 5 else ""
            escuela_num = h.escuela_codigo[5:] if len(h.escuela_codigo) > 5 else ""
            propuestas.append(
                PropuestaDesignacionDTO(
                    secuencia=h.secuencia,
                    escuela_codigo=escuela_codigo,
                    distrito=distrito,
                    tipo_nivel=tipo_nivel,
                    escuela_numero=escuela_num,
                    cargo_codigo="DOCENTE",
                    situacion_revista=_map_revista(h.revista_recibo).value,
                    modulos_horas=h.modulos_recibo,
                    fecha_desde=fecha_inicio,
                    observaciones=f"Propuesta generada automáticamente desde línea huérfana Sec {h.secuencia} recibo {id_recibo}",
                )
            )

        return propuestas

    def confirmar_propuestas(
        self, id_recibo: str, solicitud: ConfirmarPropuestasDTO
    ) -> list[DesignacionDocenteDTO]:
        """Persiste únicamente las designaciones huérfanas explícitamente confirmadas por el usuario."""
        recibo = self._recibo_repository.obtener_por_id(id_recibo)
        if not recibo:
            raise ReciboNotFoundError(f"Recibo '{id_recibo}' no encontrado.")

        cuit_normalizado = recibo.agente.cuil.replace("-", "").strip()
        creadas_dto: list[DesignacionDocenteDTO] = []

        for prop in solicitud.propuestas:
            try:
                sec_num = int(prop.secuencia)
            except ValueError:
                sec_num = None

            try:
                f_desde = date.fromisoformat(prop.fecha_desde)
            except ValueError:
                f_desde = datetime.now(timezone.utc).date()

            revista_enum = _map_revista(prop.situacion_revista)
            nueva = DesignacionDocente(
                id_designacion=f"desig_{uuid.uuid4().hex[:12]}",
                docente_cuit=cuit_normalizado,
                establecimiento=prop.escuela_codigo,
                distrito=prop.distrito or prop.escuela_codigo[:3],
                cargo_asignatura=prop.cargo_codigo or "DOCENTE",
                revista=revista_enum,
                vigencia=PeriodoVigencia(fecha_desde=f_desde),
                modulos=int(prop.modulos_horas),
                secuencia=sec_num,
                observaciones=prop.observaciones,
                escuela_numero=prop.escuela_numero,
            )
            guardada = self._designacion_repository.guardar(nueva)
            creadas_dto.append(HorariosDocenciaMapper.designacion_to_dto(guardada))

        return creadas_dto
