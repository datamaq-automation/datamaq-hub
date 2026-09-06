"""Value objects for empleo bounded context."""

import re
from enum import Enum


class ModalidadTrabajo(str, Enum):
    """Modalidad laboral del puesto."""

    PRESENCIAL = "PRESENCIAL"
    REMOTO = "REMOTO"
    HIBRIDO = "HIBRIDO"
    ROTACIONAL_YACIMIENTO = "ROTACIONAL_YACIMIENTO"
    INDEFINIDO = "INDEFINIDO"


class FuenteOferta(str, Enum):
    """Origen o portal de la oferta laboral."""

    YPF = "YPF"
    TECPETROL = "TECPETROL"
    PAE = "PAE"
    VISTA = "VISTA"
    LINKEDIN = "LINKEDIN"
    GENERICO = "GENERICO"


class NivelAfinidad(str, Enum):
    """Clasificación cualitativa del calce del perfil con la oferta."""

    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"
    NULA = "NULA"


class EstadoOportunidad(str, Enum):
    """Estado del ciclo de vida de una postulación u oportunidad laboral."""

    DETECTADA = "DETECTADA"
    POSTULADA = "POSTULADA"
    EN_CONTACTO = "EN_CONTACTO"
    ENTREVISTA = "ENTREVISTA"
    OFERTA = "OFERTA"
    DESCARTADA = "DESCARTADA"
    CONGELADA = "CONGELADA"


class UbicacionCuenca:
    """Clasificador y detector de ubicaciones de la cuenca neuquina / Vaca Muerta."""

    LOCALIDADES_VACA_MUERTA: tuple[str, ...] = (
        "anelo",
        "añelo",
        "neuquen",
        "neuquén",
        "rincon de los sauces",
        "rincón de los sauces",
        "plaza huincul",
        "cutral co",
        "cutral-co",
        "catriel",
        "cipolletti",
        "allen",
        "rio negro",
        "río negro",
        "san patricio del chanar",
        "san patricio del chañar",
        "barda del medio",
        "senillosa",
        "plottier",
        "centenario",
    )

    @classmethod
    def es_vaca_muerta(cls, ubicacion: str) -> bool:
        """Determina si una cadena de ubicación corresponde a la zona de Vaca Muerta."""
        if not ubicacion:
            return False
        norm = ubicacion.lower()
        for loc in cls.LOCALIDADES_VACA_MUERTA:
            if re.search(r"\b" + re.escape(loc) + r"\b", norm):
                return True
        return False
