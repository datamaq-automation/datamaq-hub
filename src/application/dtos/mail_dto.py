"""Data Transfer Objects for email operations."""

from pydantic import BaseModel, Field

from src.domain.mail.value_objects import CategoriaEmail, NivelPrioridad


class EmailFolderDTO(BaseModel):
    """DTO representing an IMAP mailbox folder."""

    nombre: str = Field(description="Nombre de la carpeta IMAP")
    total_mensajes: int = Field(description="Cantidad total de mensajes en la carpeta")
    no_leidos: int = Field(description="Cantidad de mensajes no leídos")


class EmailAttachmentDTO(BaseModel):
    """DTO representing attachment metadata."""

    nombre: str = Field(description="Nombre de archivo del adjunto")
    content_type: str = Field(description="Tipo MIME del archivo adjunto")
    tamano_bytes: int = Field(description="Tamaño en bytes del archivo adjunto")


class EmailSummaryDTO(BaseModel):
    """DTO representing an email summary in mailbox listings."""

    uid: str = Field(description="Identificador único IMAP del correo")
    remitente: str = Field(description="Dirección o nombre del remitente")
    destinatarios: list[str] = Field(
        default_factory=list[str], description="Lista de destinatarios principales"
    )
    asunto: str = Field(default="", description="Asunto del correo")
    fecha: str = Field(default="", description="Fecha de emisión en formato ISO 8601")
    leido: bool = Field(default=False, description="Indica si el correo fue leído")
    tiene_adjuntos: bool = Field(
        default=False, description="Indica si el correo contiene archivos adjuntos"
    )
    carpeta: str = Field(default="INBOX", description="Nombre de la carpeta de origen")
    snippet: str = Field(
        default="",
        description="Previsualización compacta de texto del correo (primeros 150 caracteres)",
    )


class EmailDetailDTO(BaseModel):
    """DTO representing full email details including content and attachments."""

    uid: str = Field(description="Identificador único IMAP del correo")
    remitente: str = Field(description="Dirección o nombre del remitente")
    destinatarios: list[str] = Field(
        default_factory=list[str], description="Lista de destinatarios principales"
    )
    cc: list[str] = Field(
        default_factory=list[str], description="Lista de destinatarios en copia"
    )
    asunto: str = Field(default="", description="Asunto del correo")
    fecha: str = Field(default="", description="Fecha de emisión en formato ISO 8601")
    leido: bool = Field(default=False, description="Indica si el correo fue leído")
    cuerpo_texto: str = Field(
        default="", description="Cuerpo del mensaje en texto plano"
    )
    cuerpo_html: str = Field(
        default="", description="Cuerpo del mensaje en formato HTML"
    )
    adjuntos: list[EmailAttachmentDTO] = Field(
        default_factory=list[EmailAttachmentDTO],
        description="Lista de metadatos de archivos adjuntos",
    )
    carpeta: str = Field(default="INBOX", description="Nombre de la carpeta de origen")


class UnreadSummaryDTO(BaseModel):
    """DTO representing a summary of unread messages."""

    carpeta: str = Field(description="Nombre de la carpeta")
    total_no_leidos: int = Field(description="Total de correos no leídos")
    ultimos_no_leidos: list[EmailSummaryDTO] = Field(
        default_factory=list[EmailSummaryDTO],
        description="Lista resumida de los correos no leídos más recientes",
    )


class MailInboxResponseDTO(BaseModel):
    """DTO for paginated mailbox listings."""

    carpeta: str = Field(description="Nombre de la carpeta consultada")
    total: int = Field(description="Total de correos en la carpeta")
    no_leidos: int = Field(description="Total de correos no leídos en la carpeta")
    offset: int = Field(default=0, description="Desplazamiento aplicado")
    limit: int = Field(default=20, description="Límite máximo por página")
    correos: list[EmailSummaryDTO] = Field(
        default_factory=list[EmailSummaryDTO],
        description="Lista de correos en la página actual",
    )


class EntidadesDetectadasDTO(BaseModel):
    """DTO de entidades extraídas determinísticamente del correo."""

    empresa: str | None = Field(default=None, description="Empresa o grupo industrial")
    contacto_nombre: str | None = Field(default=None, description="Nombre del contacto")
    contacto_cargo: str | None = Field(default=None, description="Cargo del contacto")
    tipo_proyecto: str | None = Field(default=None, description="Tipo de proyecto")
    ubicacion_planta: str | None = Field(default=None, description="Planta/ubicación")
    telefonos: list[str] = Field(
        default_factory=list[str], description="Teléfonos detectados en la firma"
    )


class AnalisisEmailDTO(BaseModel):
    """DTO del análisis de oportunidad B2B de un correo."""

    uid: str = Field(description="Identificador único IMAP del correo")
    categoria: CategoriaEmail = Field(description="Clasificación semántica")
    prioridad: NivelPrioridad = Field(description="Nivel de prioridad comercial")
    score: int = Field(description="Puntuación de oportunidad de 0 a 100")
    resumen_ejecutivo: str = Field(
        default="", description="Resumen en español del análisis"
    )
    accion_sugerida: str = Field(default="", description="Acción recomendada")
    entidades: EntidadesDetectadasDTO = Field(
        default_factory=EntidadesDetectadasDTO,
        description="Entidades extraídas del correo",
    )
    requiere_alerta: bool = Field(
        default=False, description="Indica si el correo amerita alerta"
    )
    cuenta: str = Field(default="", description="Cuenta de correo de origen")


class ScanMailRequestDTO(BaseModel):
    """DTO de solicitud de escaneo y notificación de correos entrantes."""

    cuenta: str = Field(default="datamaq", description="Cuenta de correo a escanear")
    carpeta: str = Field(default="INBOX", description="Carpeta a inspeccionar")
    limit: int = Field(default=10, ge=1, le=50, description="Máximo de correos a escanear")
    forzar_notificacion: bool = Field(
        default=False, description="Omite el caché de deduplicación"
    )
    auto_registrar_contacto: bool = Field(
        default=False, description="Auto-registra el contacto en Roundcube"
    )


class ScanMailResponseDTO(BaseModel):
    """DTO de respuesta del escaneo de oportunidades sortino a notificación."""

    total_escaneados: int = Field(description="Correos evaluados")
    total_oportunidades: int = Field(description="Correos clasificados como oportunidad")
    alertas_enviadas: int = Field(description="Alertas Telegram entregadas")
    contactos_registrados: int = Field(description="Contactos auto-registrados")
    analisis: list[AnalisisEmailDTO] = Field(
        default_factory=list[AnalisisEmailDTO],
        description="Análisis de cada correo escaneado",
    )
