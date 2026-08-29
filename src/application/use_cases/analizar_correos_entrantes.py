"""Caso de uso orquestador: AnalizarCorreosEntrantesUseCase.

Escanea el buzón, ejecuta el scoring determinístico de oportunidades B2B,
notifica por Telegram (deduplicado vía ApiCachePort con TTL de 30 días) y
opcionalmente auto-registra el contacto en Roundcube y crea una tarea de
respuesta prioritaria.
"""

import uuid

from src.application.dtos.mail_dto import (
    AnalisisEmailDTO,
    ScanMailRequestDTO,
    ScanMailResponseDTO,
)
from src.application.mappers.mail_mapper import MailMapper
from src.domain.cache.ports import ApiCachePort
from src.domain.contacts.entities import Contact
from src.domain.contacts.ports import ContactsRepositoryPort
from src.domain.mail.entities import AnalisisEmail, EmailDetail
from src.domain.mail.ports import MailNotifierPort, MailReaderPort
from src.domain.mail.services import EmailOpportunityAnalyzerService
from src.domain.mail.value_objects import CategoriaEmail, NivelPrioridad
from src.domain.tareas.entities import Tarea
from src.domain.tareas.ports import TareaRepositoryPort
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)

TTL_ALERTA_MAIL = 30 * 24 * 3600  # 30 días


def _clave_alerta(cuenta: str, uid: str) -> str:
    return f"mail:alerted:{cuenta}:{uid}"


def _prioridad_tarea(nivel: NivelPrioridad) -> PrioridadTarea:
    if nivel == NivelPrioridad.ALTA:
        return PrioridadTarea.ALTA
    if nivel == NivelPrioridad.MEDIA:
        return PrioridadTarea.MEDIA
    return PrioridadTarea.MEDIA


class AnalizarCorreosEntrantesUseCase:
    """Escanea, analiza y notifica oportunidades B2B en correos entrantes."""

    def __init__(
        self,
        mail_reader: MailReaderPort,
        analyzer: EmailOpportunityAnalyzerService,
        notifier: MailNotifierPort,
        cache: ApiCachePort,
        contacts_repo: ContactsRepositoryPort | None = None,
        tarea_repo: TareaRepositoryPort | None = None,
    ) -> None:
        self.mail_reader = mail_reader
        self.analyzer = analyzer
        self.notifier = notifier
        self.cache = cache
        self.contacts_repo = contacts_repo
        self.tarea_repo = tarea_repo

    def execute(self, request: ScanMailRequestDTO) -> ScanMailResponseDTO:
        """Ejecuta el escaneo completo con notificación deduplicada."""
        _, total, _ = self.mail_reader.list_messages(
            folder=request.carpeta,
            limit=request.limit,
            unread_only=True,
        )
        resumenes, _, _ = self.mail_reader.list_messages(
            folder=request.carpeta,
            limit=request.limit,
            unread_only=True,
        )

        detalles_analisis: list[AnalisisEmailDTO] = []
        oportunidad_total = 0
        alertas = 0
        contactos_registrados = 0

        for resumen in resumenes:
            detail = self.mail_reader.get_message_by_uid(
                uid=resumen.uid, folder=request.carpeta
            )
            if detail is None:
                continue
            analisis = self.analyzer.analizar(detail, cuenta=request.cuenta)
            detalles_analisis.append(MailMapper.to_analisis_dto(analisis))

            if not analisis.requiere_alerta:
                continue
            if analisis.categoria != CategoriaEmail.OPORTUNIDAD_COMERCIAL:
                continue

            oportunidad_total += 1
            clave = _clave_alerta(request.cuenta, analisis.uid)
            ya_alertado = self.cache.get(clave) is not None
            if ya_alertado and not request.forzar_notificacion:
                continue

            enviada = self.notifier.notificar_oportunidad_email(analisis, detail)
            if enviada:
                self.cache.set(clave, {"alertado": True}, ttl_seconds=TTL_ALERTA_MAIL)
                alertas += 1

                contacto_registrado = self._registrar_contacto(
                    analisis, detail, request
                )
                if contacto_registrado:
                    contactos_registrados += 1
                self._crear_tarea(analisis)

        return ScanMailResponseDTO(
            total_escaneados=total if total else len(resumenes),
            total_oportunidades=oportunidad_total,
            alertas_enviadas=alertas,
            contactos_registrados=contactos_registrados,
            analisis=detalles_analisis,
        )

    def analizar_single(
        self, uid: str, cuenta: str, carpeta: str = "INBOX"
    ) -> AnalisisEmailDTO:
        """Analiza un correo individual sin notificar ni cachear."""
        detail = self.mail_reader.get_message_by_uid(uid=uid, folder=carpeta)
        if detail is None:
            from src.domain.mail.exceptions import EmailNotFoundError

            raise EmailNotFoundError(uid=uid, folder=carpeta)
        analisis = self.analyzer.analizar(detail, cuenta=cuenta)
        return MailMapper.to_analisis_dto(analisis)

    def _registrar_contacto(
        self,
        analisis: AnalisisEmail,
        detail: EmailDetail,
        request: ScanMailRequestDTO,
    ) -> bool:
        if not self.contacts_repo or not request.auto_registrar_contacto:
            return False
        nombre_contacto = analisis.entidades.contacto_nombre
        if not nombre_contacto:
            return False
        entidades = analisis.entidades
        telefono = entidades.telefonos[0] if entidades.telefonos else ""
        notas = (
            f"Cargo: {entidades.contacto_cargo}"
            if entidades.contacto_cargo
            else ""
        )
        contacto = Contact(
            id_contacto=str(uuid.uuid4()),
            nombre=nombre_contacto,
            email=detail.remitente,
            telefono=telefono,
            organizacion=entidades.empresa or "",
            notas=notas,
            cuenta=request.cuenta,
        )
        self.contacts_repo.create_contact(contacto, account=request.cuenta)
        return True

    def _crear_tarea(self, analisis: AnalisisEmail) -> None:
        if not self.tarea_repo:
            return
        contacto = analisis.entidades.contacto_nombre or "contacto"
        empresa = analisis.entidades.empresa or ""
        titulo = f"📞 Responder a {contacto} - {empresa}".strip(" -")
        tarea = Tarea(
            id_tarea=str(uuid.uuid4()),
            titulo=titulo,
            prioridad=_prioridad_tarea(analisis.prioridad),
            estado=EstadoTarea.PENDIENTE,
            categoria=CategoriaTarea.GENERAL,
            id_referencia=analisis.uid,
            tipo_referencia="mail",
            metadatos={"score": analisis.score, "cuenta": analisis.cuenta},
        )
        self.tarea_repo.guardar(tarea)
