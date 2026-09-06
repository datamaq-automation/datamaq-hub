"""DTOs for empleo bounded context."""

from pydantic import BaseModel, Field


class PerfilProfesionalDTO(BaseModel):
    """DTO para el perfil profesional de búsqueda y afinidad."""

    titulo_deseado: str = Field(
        default="Ingeniero de Automatización y Control",
        description="Título o rol profesional objetivo",
    )
    palabras_clave_prioritarias: list[str] = Field(
        default_factory=list[str],
        description="Palabras clave con alta ponderación",
    )
    palabras_clave_secundarias: list[str] = Field(
        default_factory=list[str],
        description="Palabras clave secundarias o complementarias",
    )
    ubicaciones_preferidas: list[str] = Field(
        default_factory=list[str],
        description="Ubicaciones o ciudades de preferencia",
    )
    modalidades_admitidas: list[str] = Field(
        default_factory=list[str],
        description="Modalidades laborales aceptadas",
    )


class BuscarOfertasQueryDTO(BaseModel):
    """DTO de parámetros de consulta para búsqueda de ofertas."""

    palabras_clave: list[str] = Field(
        default_factory=list[str],
        description="Palabras clave para filtrar en los portales",
    )
    ubicacion: str | None = Field(
        default=None,
        description="Filtro geográfico opcional",
    )
    solo_vaca_muerta: bool = Field(
        default=True,
        description="Si es True, aplica heurística estricta de Vaca Muerta / Cuenca Neuquina",
    )
    min_score_afinidad: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Puntaje mínimo de afinidad requerido (0 a 100)",
    )
    perfil: PerfilProfesionalDTO | None = Field(
        default=None,
        description="Perfil profesional para scoring (si es None, se usa el perfil predeterminado)",
    )


class OfertaLaboralDTO(BaseModel):
    """DTO para una oferta laboral normalizada."""

    id_oferta: str
    titulo: str
    empresa: str
    ubicacion: str
    descripcion: str
    url_postulacion: str
    fecha_publicacion: str = ""
    fuente: str
    modalidad: str
    tags: list[str] = Field(default_factory=list[str])
    score_afinidad: float = 0.0
    nivel_afinidad: str = "NULA"
    requisitos: list[str] = Field(default_factory=list[str])


class ResultadoBusquedaDTO(BaseModel):
    """DTO que consolida el resultado de la búsqueda multifuente."""

    ofertas: list[OfertaLaboralDTO] = Field(default_factory=list[OfertaLaboralDTO])
    total_encontradas: int = 0
    fuentes_consultadas: list[str] = Field(default_factory=list[str])
    fecha_consulta: str = ""


class RegistrarOportunidadDTO(BaseModel):
    """DTO para registrar una nueva oportunidad o postulación laboral."""

    titulo: str
    empresa: str = ""
    consultora: str = ""
    ubicacion: str = "Neuquén"
    regimen: str = ""
    jornada: str = ""
    salario_min: float | None = None
    salario_max: float | None = None
    salario_moneda: str = "ARS"
    salario_bruto_neto: str = ""
    url_fuente: str = ""
    estado: str = "DETECTADA"
    fecha_publicacion: str = ""
    fecha_postulacion: str = ""
    fecha_entrevista: str = ""
    fecha_oferta: str = ""
    fecha_descarte: str = ""
    fecha_congelacion: str = ""
    notas: str = ""
    requisitos: list[str] = Field(default_factory=list[str])
    origen: str = "MANUAL"
    tipo_modalidad: str = "RELACION_DEPENDENCIA"
    canal_adquisicion: str = "DIRECTO"
    id_campania: int | None = None


class ActualizarEstadoOportunidadDTO(BaseModel):
    """DTO para actualizar el estado y notas de una oportunidad."""

    id_oportunidad: int
    nuevo_estado: str
    notas: str | None = None


class CambiarEstadoDTO(BaseModel):
    """Payload para actualizar únicamente el estado y notas desde la API."""

    nuevo_estado: str
    notas: str | None = None


class OportunidadDTO(BaseModel):
    """DTO representativo de una oportunidad o postulación registrada."""

    id: int | None = None
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
    estado: str = "DETECTADA"
    fecha_publicacion: str = ""
    fecha_postulacion: str = ""
    fecha_entrevista: str = ""
    fecha_oferta: str = ""
    fecha_descarte: str = ""
    fecha_congelacion: str = ""
    notas: str = ""
    requisitos: list[str] = Field(default_factory=list[str])
    origen: str = "MANUAL"
    tipo_modalidad: str = "RELACION_DEPENDENCIA"
    canal_adquisicion: str = "DIRECTO"
    id_campania: int | None = None


class RegistrarInteraccionDTO(BaseModel):
    """DTO para registrar una interacción o seguimiento de postulación."""

    oportunidad_id: int = 0
    fecha: str
    canal: str = "MAIL"
    contacto_nombre: str = ""
    contacto_email: str = ""
    contacto_telefono: str = ""
    contacto_empresa: str = ""
    resumen: str = ""
    proxima_accion: str = ""
    fecha_proxima_accion: str = ""


class InteraccionDTO(BaseModel):
    """DTO representativo de una interacción o seguimiento de postulación."""

    id: int | None = None
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
