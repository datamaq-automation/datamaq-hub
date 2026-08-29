"""Mappers for converting between Domain Entities and Application DTOs."""

from src.application.dtos.mail_dto import (
    EmailAttachmentDTO,
    EmailDetailDTO,
    EmailFolderDTO,
    EmailSummaryDTO,
    UnreadSummaryDTO,
)
from src.domain.mail.entities import (
    EmailAttachmentMetadata,
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)


class MailMapper:
    """Mapper methods for mail entities and DTOs."""

    @staticmethod
    def to_folder_dto(entity: EmailFolder) -> EmailFolderDTO:
        """Converts an EmailFolder entity to EmailFolderDTO."""
        return EmailFolderDTO(
            nombre=entity.nombre,
            total_mensajes=entity.total_mensajes,
            no_leidos=entity.no_leidos,
        )

    @staticmethod
    def to_attachment_dto(entity: EmailAttachmentMetadata) -> EmailAttachmentDTO:
        """Converts an EmailAttachmentMetadata entity to EmailAttachmentDTO."""
        return EmailAttachmentDTO(
            nombre=entity.nombre,
            content_type=entity.content_type,
            tamano_bytes=entity.tamano_bytes,
        )

    @staticmethod
    def to_summary_dto(entity: EmailSummary) -> EmailSummaryDTO:
        """Converts an EmailSummary entity to EmailSummaryDTO."""
        return EmailSummaryDTO(
            uid=entity.uid,
            remitente=entity.remitente,
            destinatarios=list(entity.destinatarios),
            asunto=entity.asunto,
            fecha=entity.fecha,
            leido=entity.leido,
            tiene_adjuntos=entity.tiene_adjuntos,
            carpeta=entity.carpeta,
            snippet=entity.snippet,
        )

    @staticmethod
    def to_detail_dto(entity: EmailDetail) -> EmailDetailDTO:
        """Converts an EmailDetail entity to EmailDetailDTO."""
        return EmailDetailDTO(
            uid=entity.uid,
            remitente=entity.remitente,
            destinatarios=list(entity.destinatarios),
            cc=list(entity.cc),
            asunto=entity.asunto,
            fecha=entity.fecha,
            leido=entity.leido,
            cuerpo_texto=entity.cuerpo_texto,
            cuerpo_html=entity.cuerpo_html,
            adjuntos=[MailMapper.to_attachment_dto(a) for a in entity.adjuntos],
            carpeta=entity.carpeta,
        )

    @staticmethod
    def to_unread_summary_dto(entity: UnreadSummary) -> UnreadSummaryDTO:
        """Converts an UnreadSummary entity to UnreadSummaryDTO."""
        return UnreadSummaryDTO(
            carpeta=entity.carpeta,
            total_no_leidos=entity.total_no_leidos,
            ultimos_no_leidos=[
                MailMapper.to_summary_dto(s) for s in entity.ultimos_no_leidos
            ],
        )
