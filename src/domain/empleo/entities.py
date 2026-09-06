"""Domain entities for empleo bounded context."""

from dataclasses import dataclass

from src.domain.empleo.exceptions import PerfilInvalidoError
from src.domain.empleo.value_objects import (
    EstadoOportunidad,
    FuenteOferta,
    ModalidadTrabajo,
    NivelAfinidad,
)


@dataclass(frozen=True)
class OportunidadLaboral:
    """Representa una oportunidad o postulación registrada en la base de datos de búsqueda laboral."""

    id: int | None
    titulo: str
    empresa: str = ""
    consultora: str = ""
    ubicacion: str = ""
    regimen: str = ""
    jornada: str = ""
    salario_min: float | None = None
    salario_max: float | None = None
    salario_moneda: str = "ARS"
    salario_bruto_neto: str = ""
    url_fuente: str = ""
    estado: EstadoOportunidad = EstadoOportunidad.DETECTADA
    fecha_publicacion: str = ""
    fecha_postulacion: str = ""
    fecha_entrevista: str = ""
    fecha_oferta: str = ""
    fecha_descarte: str = ""
    fecha_congelacion: str = ""
    notas: str = ""
    requisitos: tuple[str, ...] = ()
    origen: str = "MANUAL"
    tipo_modalidad: str = "RELACION_DEPENDENCIA"
    canal_adquisicion: str = "DIRECTO"
    id_campania: int | None = None


@dataclass(frozen=True)
class InteraccionPostulacion:
    """Interacción, contacto o seguimiento asociado a una oportunidad laboral."""

    id: int | None
    oportunidad_id: int
    fecha: str
    canal: str = "MAIL"
    contacto_nombre: str = ""
    contacto_email: str = ""
    contacto_telefono: str = ""
    contacto_empresa: str = ""
    resumen: str = ""
    proxima_accion: str = ""
    fecha_proxima_accion: str = ""


@dataclass(frozen=True)
class OfertaLaboral:
    """Entidad inmutable que representa una oportunidad laboral."""

    id_oferta: str
    titulo: str
    empresa: str
    ubicacion: str
    descripcion: str
    url_postulacion: str
    fecha_publicacion: str = ""
    fuente: FuenteOferta = FuenteOferta.GENERICO
    modalidad: ModalidadTrabajo = ModalidadTrabajo.INDEFINIDO
    tags: tuple[str, ...] = ()
    score_afinidad: float = 0.0
    nivel_afinidad: NivelAfinidad = NivelAfinidad.NULA
    requisitos: tuple[str, ...] = ()


@dataclass(frozen=True)
class PerfilProfesional:
    """Perfil profesional objetivo utilizado para scoring y filtrado."""

    titulo_deseado: str
    palabras_clave_prioritarias: tuple[str, ...] = ()
    palabras_clave_secundarias: tuple[str, ...] = ()
    ubicaciones_preferidas: tuple[str, ...] = ()
    modalidades_admitidas: tuple[ModalidadTrabajo, ...] = ()

    def __post_init__(self) -> None:
        if not self.titulo_deseado and not self.palabras_clave_prioritarias:
            raise PerfilInvalidoError(
                "El perfil profesional debe definir al menos un título deseado o palabras clave prioritarias."
            )


@dataclass(frozen=True)
class ResultadoBusquedaEmpleo:
    """Agregado que resume el resultado consolidado de una búsqueda multifuente."""

    ofertas: tuple[OfertaLaboral, ...] = ()
    total_encontradas: int = 0
    fuentes_consultadas: tuple[FuenteOferta, ...] = ()
    fecha_consulta: str = ""


def obtener_perfil_agustin_bustos() -> PerfilProfesional:
    """Retorna el perfil profesional parametrizado de Agustín Leonardo Bustos según su CV."""
    return PerfilProfesional(
        titulo_deseado="Especialista en Confiabilidad Operacional y Desempeño de Activos",
        palabras_clave_prioritarias=(
            "confiabilidad",
            "apm",
            "mantenimiento",
            "instrumentacion",
            "instrumentación",
            "electromecanica",
            "electromecánica",
            "electrico",
            "eléctrico",
            "variadores",
            "vfd",
            "media tension",
            "media tensión",
            "13.2 kv",
            "13.2kv",
            "ccm",
            "telemetria",
            "telemetría",
            "iot",
            "iiot",
            "predictivo",
            "preventivo",
            "cbm",
            "smart meters",
            "gmao",
            "cmms",
            "scada",
            "plc",
            "control",
            "troubleshooting",
            "comisionado",
            "loto",
            "nfpa 70e",
            "aea 90364",
            "diagrama",
            "14x7",
            "10x5",
            "rotativo",
        ),
        palabras_clave_secundarias=(
            "python",
            "machine learning",
            "inteligencia artificial",
            "aprendizaje automatico",
            "aprendizaje automático",
            "analisis de datos",
            "análisis de datos",
            "compresor",
            "neumatica",
            "neumática",
            "hidraulica",
            "hidráulica",
            "hse",
            "ssma",
            "manejo defensivo",
            "uptime",
            "npt",
            "solar",
            "generadores",
            "celdas",
            "siemens",
            "schneider",
            "abb",
            "tenaris",
            "yacimiento",
            "pozo",
            "planta",
            "modbus",
            "profibus",
            "ethernet/ip",
        ),
        ubicaciones_preferidas=(
            "añelo",
            "anelo",
            "neuquen",
            "neuquén",
            "rio negro",
            "río negro",
            "rincon de los sauces",
            "rincón de los sauces",
            "plaza huincul",
            "cutral co",
            "catriel",
            "allen",
            "cipolletti",
        ),
        modalidades_admitidas=(
            ModalidadTrabajo.ROTACIONAL_YACIMIENTO,
            ModalidadTrabajo.PRESENCIAL,
            ModalidadTrabajo.HIBRIDO,
            ModalidadTrabajo.REMOTO,
        ),
    )
