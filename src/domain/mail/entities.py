"""Domain entities for mail bounded context."""

from dataclasses import dataclass, field


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
