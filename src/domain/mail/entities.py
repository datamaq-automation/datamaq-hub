"""Domain entities for mail bounded context."""

from dataclasses import dataclass, field

from src.domain.mail.value_objects import CategoriaEmail, NivelPrioridad


@dataclass(frozen=True)
class EmailFolder:
    """Representation of an IMAP folder/mailbox with message statistics."""

    nombre: str
    total_mensajes: int
    no_leidos: int


@dataclass(frozen=True)
class EmailAttachmentMetadata:
    """Metadata describing an attachment found in an email message."""

    nombre: str
    content_type: str
    tamano_bytes: int


@dataclass(frozen=True)
class EmailSummary:
    """Summary of an email message suited for mailbox listings and previews."""

    uid: str
    remitente: str
    destinatarios: list[str] = field(default_factory=list[str])
    asunto: str = ""
    fecha: str = ""
    leido: bool = False
    tiene_adjuntos: bool = False
    carpeta: str = "INBOX"
    snippet: str = ""


@dataclass(frozen=True)
class EmailDetail:
    """Full detail of an email message including plain text, HTML and attachments."""

    uid: str
    remitente: str
    destinatarios: list[str] = field(default_factory=list[str])
    cc: list[str] = field(default_factory=list[str])
    asunto: str = ""
    fecha: str = ""
    leido: bool = False
    cuerpo_texto: str = ""
    cuerpo_html: str = ""
    adjuntos: list[EmailAttachmentMetadata] = field(
        default_factory=list[EmailAttachmentMetadata]
    )
    carpeta: str = "INBOX"


@dataclass(frozen=True)
class UnreadSummary:
    """High-level summary of unread messages in a given folder."""

    carpeta: str
    total_no_leidos: int
    ultimos_no_leidos: list[EmailSummary] = field(default_factory=list[EmailSummary])


@dataclass(frozen=True)
class EntidadesDetectadas:
    """Entidades extraídas determinísticamente del correo entrante."""

    empresa: str | None = None
    contacto_nombre: str | None = None
    contacto_cargo: str | None = None
    tipo_proyecto: str | None = None
    ubicacion_planta: str | None = None
    telefonos: list[str] = field(default_factory=list[str])


@dataclass(frozen=True)
class AnalisisEmail:
    """Resultado del scoring determinístico de oportunidad B2B para un correo."""

    uid: str
    categoria: CategoriaEmail
    prioridad: NivelPrioridad
    score: int
    resumen_ejecutivo: str
    accion_sugerida: str
    entidades: EntidadesDetectadas
    requiere_alerta: bool
    cuenta: str = ""
