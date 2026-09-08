"""Caso de uso para generar propuestas revisables de líneas huérfanas y alta confirmada en bulk."""

from __future__ import annotations

import re
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


def _parse_escuela_codigo(escuela_raw: str) -> tuple[str, str, str, str]:
    """Parsea una cadena de establecimiento (ej. '11-ESCOBAR MT-0001', '055IS0199', '116 MT 0001')
    en (escuela_codigo_limpio, distrito, tipo_nivel, escuela_numero).
    """
    raw = (escuela_raw or "").strip()
    if not raw:
        return "", "", "", ""

    # Caso compacto estándar DGCyE: 3 dígitos distrito + 2 letras nivel + 4 dígitos escuela (ej. 055IS0199)
    m_compact = re.match(r"^(\d{3})([A-Za-z]{2})(\d{4})$", raw)
    if m_compact:
        dist, niv, num = m_compact.groups()
        return raw, dist, niv.upper(), num

    # Caso con guiones o espacios (ej. '11-ESCOBAR MT-0001', '116 MT 0001', '055 IS 0199')
    # Buscar patrón de nivel (MT, IS, EP, EEST, EEE, EES, JI, CEC, etc.) y número de escuela al final
    m_complex = re.match(
        r"^(\d{1,3})(?:-[^\s]+)?\s+([A-Za-z]{2,4})[\s-]*(\d{1,4})$", raw
    )
    if m_complex:
        dist_num, niv, num = m_complex.groups()
        dist = dist_num.zfill(3)
        num_str = num.zfill(4)
        codigo_normalizado = f"{dist}{niv.upper()}{num_str}"
        return codigo_normalizado, dist, niv.upper(), num_str

    # Fallback genérico si no coincide con los patrones exactos
    dist = raw[:3] if len(raw) >= 3 and raw[:3].isdigit() else ""
    return raw, dist, "", ""


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

        # Determinar fecha base por defecto (primer día del mes de pago)
        try:
            partes = recibo.agente.mes_pago.split("-")
            fecha_inicio_defecto = f"{partes[0]}-{partes[1]}-01"
        except (IndexError, AttributeError, ValueError):
            today = datetime.now(timezone.utc).date()
            fecha_inicio_defecto = f"{today.year}-{today.month:02d}-01"

        propuestas: list[PropuestaDesignacionDTO] = []
        for h in resultado.lineas_huerfanas_recibo:
            cod_norm, distrito, tipo_nivel, escuela_num = _parse_escuela_codigo(
                h.escuela_codigo
            )

            # Bug 3: Usar periodo_liquidado si está disponible (ej. "2026-06" -> "2026-06-01")
            if (
                h.periodo_liquidado
                and len(h.periodo_liquidado) == 7
                and "-" in h.periodo_liquidado
            ):
                fecha_desde = f"{h.periodo_liquidado}-01"
            else:
                fecha_desde = fecha_inicio_defecto

            propuestas.append(
                PropuestaDesignacionDTO(
                    secuencia=h.secuencia,
                    escuela_codigo=cod_norm or h.escuela_codigo,
                    distrito=distrito,
                    tipo_nivel=tipo_nivel,
                    escuela_numero=escuela_num,
                    cargo_codigo="DOCENTE",
                    situacion_revista=_map_revista(h.revista_recibo).value,
                    modulos_horas=h.modulos_recibo,
                    fecha_desde=fecha_desde,
                    observaciones=f"Propuesta generada automáticamente desde línea huérfana Sec {h.secuencia} recibo {id_recibo}",
                )
            )

        return propuestas

    def confirmar_propuestas(
        self, id_recibo: str, solicitud: ConfirmarPropuestasDTO
    ) -> list[DesignacionDocenteDTO]:
        """Persiste únicamente las designaciones huérfanas explícitamente confirmadas por el usuario."""
        if not solicitud.propuestas:
            raise ValueError(
                "Debe enviar al menos una propuesta de designación para confirmar."
            )

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
