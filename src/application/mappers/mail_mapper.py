"""Mappers for converting between Domain Entities and Application DTOs."""

from src.application.dtos.mail_dto import (
    AnalisisEmailDTO,
    EmailAttachmentDTO,
    EmailDetailDTO,
    EmailFolderDTO,
    EmailSummaryDTO,
    EntidadesDetectadasDTO,
    UnreadSummaryDTO,
)
from src.domain.mail.entities import (
    AnalisisEmail,
    EmailAttachmentMetadata,
    EmailDetail,
    EmailFolder,
    EmailSummary,
    EntidadesDetectadas,
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

    @staticmethod
    def to_analisis_dto(entidad: AnalisisEmail) -> AnalisisEmailDTO:
        """Convierte una entidad AnalisisEmail a su DTO de aplicación."""
        return AnalisisEmailDTO(
            uid=entidad.uid,
            categoria=entidad.categoria,
            prioridad=entidad.prioridad,
            score=entidad.score,
            resumen_ejecutivo=entidad.resumen_ejecutivo,
            accion_sugerida=entidad.accion_sugerida,
            entidades=MailMapper.to_entidades_dto(entidad.entidades),
            requiere_alerta=entidad.requiere_alerta,
            cuenta=entidad.cuenta,
        )

    @staticmethod
    def to_entidades_dto(entidad: EntidadesDetectadas) -> EntidadesDetectadasDTO:
        """Convierte la entidad de entidades detectadas a DTO."""
        return EntidadesDetectadasDTO(
            empresa=entidad.empresa,
            contacto_nombre=entidad.contacto_nombre,
            contacto_cargo=entidad.contacto_cargo,
            tipo_proyecto=entidad.tipo_proyecto,
            ubicacion_planta=entidad.ubicacion_planta,
            telefonos=list(entidad.telefonos),
        )
