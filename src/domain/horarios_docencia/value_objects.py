"""Value Objects para el subdominio de horarios y compatibilidad de docencia."""

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum

from src.domain.horarios_docencia.exceptions import (
    FranjaHorariaInvalidaException,
    HorarioDocenciaInvalidoException,
)

_TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class DiaSemana(str, Enum):
    """Días de la semana hábiles para actividad docente."""

    LUNES = "LUNES"
    MARTES = "MARTES"
    MIERCOLES = "MIERCOLES"
    JUEVES = "JUEVES"
    VIERNES = "VIERNES"
    SABADO = "SABADO"


class Turno(str, Enum):
    """Turnos escolares estándar en la Provincia de Buenos Aires."""

    MANANA = "MANANA"
    TARDE = "TARDE"
    VESPERTINO = "VESPERTINO"
    NOCHE = "NOCHE"
    INTERNO = "INTERNO"


class SituacionRevista(str, Enum):
    """Situación de revista del cargo o módulos."""

    TITULAR = "TITULAR"
    PROVISIONAL = "PROVISIONAL"
    SUPLENTE = "SUPLENTE"


class TipoConflicto(str, Enum):
    """Clasificación del tipo de incompatibilidad o conflicto detectado."""

    SUPERPOSICION_HORARIA = "SUPERPOSICION_HORARIA"
    TRASLADO_INSUFICIENTE = "TRASLADO_INSUFICIENTE"
    EXCESO_MODULOS_SEMANALES = "EXCESO_MODULOS_SEMANALES"
    EXCESO_CARGOS_BASE = "EXCESO_CARGOS_BASE"
    DESVIO_DURACION_MODULO = "DESVIO_DURACION_MODULO"


class NivelSeveridad(str, Enum):
    """Nivel de gravedad del conflicto."""

    CRITICO = "CRITICO"
    ADVERTENCIA = "ADVERTENCIA"


class MotivoCese(str, Enum):
    """Motivos formales de cese o fin de vigencia de una designación."""

    REINCORPORACION_TITULAR = "REINCORPORACION_TITULAR"
    FIN_LICENCIA = "FIN_LICENCIA"
    TITULARIZACION = "TITULARIZACION"
    FIN_SUPLENCIA = "FIN_SUPLENCIA"
    RENUNCIA = "RENUNCIA"
    DESPLAZAMIENTO = "DESPLAZAMIENTO"
    CIERRE_CURSO = "CIERRE_CURSO"
    OTRO = "OTRO"


def normalizar_cuit(cuit: str | None) -> str:
    """Limpia y normaliza un CUIT/CUIL a 11 dígitos numéricos sin guiones ni espacios."""
    if not cuit:
        return ""
    return re.sub(r"\D", "", cuit.strip())


@dataclass(frozen=True)
class PeriodoVigencia:
    """Intervalo de vigencia temporal de una designación o suplencia docente."""

    fecha_desde: date
    fecha_hasta: date | None = None

    def __post_init__(self) -> None:
        if self.fecha_hasta is not None and self.fecha_desde > self.fecha_hasta:
            raise HorarioDocenciaInvalidoException(
                f"fecha_desde ({self.fecha_desde}) no puede ser posterior a fecha_hasta ({self.fecha_hasta})"
            )

    @property
    def es_abierta(self) -> bool:
        """True si la designación no posee fecha de finalización fijada."""
        return self.fecha_hasta is None

    @staticmethod
    def fecha_fin_ciclo_lectivo(anio: int) -> date:
        """Calcula el límite estatutario de ciclo lectivo (28/29 de febrero del año posterior)."""
        es_bisiesto = (anio + 1) % 4 == 0 and (
            (anio + 1) % 100 != 0 or (anio + 1) % 400 == 0
        )
        dia = 29 if es_bisiesto else 28
        return date(anio + 1, 2, dia)

    def fecha_hasta_efectiva(self, limitar_a_ciclo: bool = False) -> date | None:
        """Retorna la fecha hasta explícita o el límite estatutario del ciclo lectivo."""
        if self.fecha_hasta is not None:
            return self.fecha_hasta
        if limitar_a_ciclo:
            return self.fecha_fin_ciclo_lectivo(self.fecha_desde.year)
        return None

    def esta_vigente_en(self, fecha: date) -> bool:
        """Determina si la designación estaba activa en una fecha específica."""
        if fecha < self.fecha_desde:
            return False
        return not (self.fecha_hasta is not None and fecha > self.fecha_hasta)

    def duracion_dias(self) -> int | None:
        """Retorna la duración en días si la fecha_hasta está definida."""
        if self.fecha_hasta is None:
            return None
        return (self.fecha_hasta - self.fecha_desde).days + 1


@dataclass(frozen=True)
class FranjaHoraria:
    """Representa un intervalo horario cerrado con formato HH:MM."""

    hora_inicio: str
    hora_fin: str

    def __post_init__(self) -> None:
        if not _TIME_REGEX.match(self.hora_inicio):
            raise FranjaHorariaInvalidaException(
                f"hora_inicio '{self.hora_inicio}' no cumple el formato HH:MM (00:00 a 23:59)"
            )
        if not _TIME_REGEX.match(self.hora_fin):
            raise FranjaHorariaInvalidaException(
                f"hora_fin '{self.hora_fin}' no cumple el formato HH:MM (00:00 a 23:59)"
            )
        if self.inicio_minutos() >= self.fin_minutos():
            raise FranjaHorariaInvalidaException(
                f"hora_inicio ({self.hora_inicio}) debe ser estrictamente menor que hora_fin ({self.hora_fin})"
            )

    def inicio_minutos(self) -> int:
        """Retorna el minuto del día (0-1439) del inicio."""
        h, m = map(int, self.hora_inicio.split(":"))
        return h * 60 + m

    def fin_minutos(self) -> int:
        """Retorna el minuto del día (0-1439) del fin."""
        h, m = map(int, self.hora_fin.split(":"))
        return h * 60 + m

    def duracion_minutos(self) -> int:
        """Retorna la duración en minutos de la franja."""
        return self.fin_minutos() - self.inicio_minutos()

    def se_superpone_con(self, otra: "FranjaHoraria") -> bool:
        """Retorna True si hay solapamiento temporal estricto (no se tocan en el límite exacto)."""
        return max(self.inicio_minutos(), otra.inicio_minutos()) < min(
            self.fin_minutos(), otra.fin_minutos()
        )

    def minutos_solapamiento(self, otra: "FranjaHoraria") -> int:
        """Calcula cuántos minutos se superponen dos franjas."""
        if not self.se_superpone_con(otra):
            return 0
        return min(self.fin_minutos(), otra.fin_minutos()) - max(
            self.inicio_minutos(), otra.inicio_minutos()
        )

    def minutos_hasta(self, posterior: "FranjaHoraria") -> int:
        """Calcula los minutos de margen entre el fin de esta franja y el inicio de la posterior."""
        return posterior.inicio_minutos() - self.fin_minutos()


def inferir_turno(franja: FranjaHoraria) -> Turno:
    """Infiere el turno escolar a partir del horario de inicio de la franja horaria."""
    inicio_min = franja.inicio_minutos()
    if 420 <= inicio_min < 780:
        return Turno.MANANA
    if 780 <= inicio_min < 1080:
        return Turno.TARDE
    if 1080 <= inicio_min < 1320:
        return Turno.VESPERTINO
    return Turno.NOCHE
