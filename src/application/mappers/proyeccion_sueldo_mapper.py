"""Mapper de proyección salarial: designaciones históricas a cargos liquidables por CUIT."""

from datetime import date

from src.domain.horarios_docencia.entities import (
    DesignacionDocente as DesignacionHoraria,
)
from src.domain.horarios_docencia.value_objects import (
    SituacionRevista as RevistaHoraria,
)
from src.domain.liquidacion.entities import DesignacionDocente
from src.domain.liquidacion.value_objects import NivelCargo, SituacionRevista

DIAS_MES_COMERCIAL: float = 30.0
_TOKENS_NIVEL_SUPERIOR: tuple[str, ...] = ("ISFD", "ISFT", "SUPERIOR", "TERCIAR")


def calcular_dias_trabajados(
    fecha_desde: date,
    fecha_hasta: date | None,
    anio: int,
    mes: int,
) -> float:
    """Calcula los días proporcionales trabajados en el mes evaluado.

    Precedencia: si la designación inicia dentro del mes se aplica la regla de
    alta; en caso contrario, si finaliza dentro del mes se aplica la de baja.
    Si no hay novedades en el mes, se devuelve el mes comercial completo.
    """
    if fecha_desde.year == anio and fecha_desde.month == mes:
        return min(
            DIAS_MES_COMERCIAL,
            max(0.0, DIAS_MES_COMERCIAL - fecha_desde.day + 1),
        )
    if fecha_hasta is not None and fecha_hasta.year == anio and fecha_hasta.month == mes:
        return min(DIAS_MES_COMERCIAL, max(0.0, float(fecha_hasta.day)))
    return DIAS_MES_COMERCIAL


def inferir_nivel_cargo(
    establecimiento: str,
    cargo_asignatura: str,
    escuela_numero: str,
) -> NivelCargo:
    """Infiere el nivel de cargo: SM para Superior, PM para Secundario/Técnico."""
    texto = f"{establecimiento} {cargo_asignatura} {escuela_numero}".upper()
    if any(token in texto for token in _TOKENS_NIVEL_SUPERIOR):
        return NivelCargo.SM
    return NivelCargo.PM


def mapear_revista(revista: RevistaHoraria) -> SituacionRevista:
    """Mapea la situación de revista de horarios docentes a liquidación."""
    if revista == RevistaHoraria.TITULAR:
        return SituacionRevista.TITULAR
    if revista == RevistaHoraria.PROVISIONAL:
        return SituacionRevista.PROVISIONAL
    return SituacionRevista.SUPLENTE


class ProyeccionSueldoMapper:
    """Convierte designaciones históricas en cargos liquidables por el motor de sueldo."""

    @staticmethod
    def designacion_a_dominio(
        designacion: DesignacionHoraria,
        anio: int,
        mes: int,
        periodo: str,
    ) -> DesignacionDocente:
        """Mapea una designación horaria a una designación de liquidación."""
        dias = calcular_dias_trabajados(
            designacion.vigencia.fecha_desde,
            designacion.vigencia.fecha_hasta,
            anio,
            mes,
        )
        secuencia = (
            str(designacion.secuencia).zfill(3)
            if designacion.secuencia is not None
            else ""
        )
        return DesignacionDocente(
            secuencia=secuencia,
            escuela_codigo=designacion.escuela_numero,
            escuela_nombre=designacion.establecimiento,
            cargo_nivel=inferir_nivel_cargo(
                designacion.establecimiento,
                designacion.cargo_asignatura,
                designacion.escuela_numero,
            ),
            carga_horaria=float(designacion.modulos),
            situacion_revista=mapear_revista(designacion.revista),
            dias_trabajados=dias,
            periodo_liquidado=periodo,
            es_retroactivo=dias < DIAS_MES_COMERCIAL,
            fecha_inicio=designacion.vigencia.fecha_desde.isoformat(),
            fecha_fin=(
                designacion.vigencia.fecha_hasta.isoformat()
                if designacion.vigencia.fecha_hasta is not None
                else None
            ),
        )
