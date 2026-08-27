"""Value Objects para el subdominio de horarios y compatibilidad de docencia."""

import re
from dataclasses import dataclass
from enum import Enum

from src.domain.horarios_docencia.exceptions import FranjaHorariaInvalidaException

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


class NivelSeveridad(str, Enum):
    """Nivel de gravedad del conflicto."""

    CRITICO = "CRITICO"
    ADVERTENCIA = "ADVERTENCIA"


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
