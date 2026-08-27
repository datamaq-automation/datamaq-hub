"""Data Transfer Objects for email operations."""

from pydantic import BaseModel, Field


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
