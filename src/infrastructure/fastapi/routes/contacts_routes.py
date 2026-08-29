"""FastAPI routes for address book contacts."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from src.adapters.controllers.contacts_controller import ContactsController
from src.adapters.controllers.dependencies import get_contacts_controller
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.contacts_dto import (
    ContactDTO,
    ContactListCompactResponseDTO,
    ContactListResponseDTO,
    ContactoCompactoDTO,
    CreateContactDTO,
    UpdateContactDTO,
)
from src.infrastructure.pydantic.config import get_settings

router = APIRouter(prefix="/contactos", tags=["Contactos"])


def get_configured_contacts_controller() -> ContactsController:
    """Dependency resolver creating ContactsController with configured DB."""
    settings = get_settings()
    from src.adapters.gateways.sql_contacts_gateway import SQLContactsGateway

    gateway = SQLContactsGateway(database_url=settings.roundcube_db_url)
    return get_contacts_controller(repository=gateway)


def _proyectar_compacto(contacto: ContactDTO) -> ContactoCompactoDTO:
    """Reduce un contacto a su representación de bajo-token (compact)."""
    return ContactoCompactoDTO(
        id_contacto=contacto.id_contacto,
        nombre=contacto.nombre,
        email=contacto.email,
        telefono=contacto.telefono,
        organizacion=contacto.organizacion,
    )


@router.get(
    "",
    response_model=APIResponseDTO[ContactListResponseDTO]
    | APIResponseDTO[ContactListCompactResponseDTO],
)
async def list_contacts(
    controller: Annotated[
        ContactsController, Depends(get_configured_contacts_controller)
    ],
    q: Annotated[
        str | None,
        Query(description="Búsqueda por texto (nombre, apellido, email, etc.)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
    compact: Annotated[
        bool, Query(description="Proyectar solo campos esenciales (bajo-token)")
    ] = False,
) -> (
    APIResponseDTO[ContactListResponseDTO]
    | APIResponseDTO[ContactListCompactResponseDTO]
):
    """Lists and searches address book contacts."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    result = controller.list_contacts(
        account=effective_account, query=q, limit=limit, offset=offset
    )
    if compact:
        return APIResponseDTO[ContactListCompactResponseDTO](
            success=True,
            data=ContactListCompactResponseDTO(
                total=result.total,
                cuenta=result.cuenta,
                contactos=[_proyectar_compacto(c) for c in result.contactos],
            ),
        )
    return APIResponseDTO[ContactListResponseDTO](success=True, data=result)


@router.get("/export/vcard", summary="Exportar contactos en formato vCard (.vcf)")
async def export_vcard(
    controller: Annotated[
        ContactsController, Depends(get_configured_contacts_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> Response:
    """Exports all address book contacts as a standard vCard 3.0 file for WhatsApp Business or mobile sync."""
    settings = get_settings()
    effective_account = (
        account
        if account is not None
        else getattr(settings, "default_mail_account", "")
    )
    vcard_data = controller.export_vcard(account=effective_account)
    return Response(
        content=vcard_data,
        media_type="text/vcard; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=contactos_datamaq.vcf"},
    )


@router.get("/{contact_id}", response_model=APIResponseDTO[ContactDTO])
async def get_contact(
    contact_id: str,
    controller: Annotated[
        ContactsController, Depends(get_configured_contacts_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[ContactDTO]:
    """Retrieves full details of a contact by identifier."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    result = controller.get_contact_detail(
        contact_id=contact_id, account=effective_account
    )
    return APIResponseDTO[ContactDTO](success=True, data=result)


@router.post("", response_model=APIResponseDTO[ContactDTO])
async def create_contact(
    payload: CreateContactDTO,
    controller: Annotated[
        ContactsController, Depends(get_configured_contacts_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[ContactDTO]:
    """Creates a new contact in the address book."""
    settings = get_settings()
    effective_account = payload.cuenta or account or settings.default_mail_account
    result = controller.create_contact(dto=payload, account=effective_account)
    return APIResponseDTO[ContactDTO](success=True, data=result)


@router.put("/{contact_id}", response_model=APIResponseDTO[ContactDTO])
async def update_contact(
    contact_id: str,
    payload: UpdateContactDTO,
    controller: Annotated[
        ContactsController, Depends(get_configured_contacts_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[ContactDTO]:
    """Updates an existing contact."""
    settings = get_settings()
    effective_account = payload.cuenta or account or settings.default_mail_account
    result = controller.update_contact(
        contact_id=contact_id, dto=payload, account=effective_account
    )
    return APIResponseDTO[ContactDTO](success=True, data=result)


@router.delete("/{contact_id}", response_model=APIResponseDTO[dict[str, Any]])
async def delete_contact(
    contact_id: str,
    controller: Annotated[
        ContactsController, Depends(get_configured_contacts_controller)
    ],
    account: Annotated[
        str | None,
        Query(description="Cuenta de correo asociada (opcional)"),
    ] = None,
) -> APIResponseDTO[dict[str, Any]]:
    """Deletes a contact from the address book."""
    settings = get_settings()
    effective_account = account or settings.default_mail_account
    deleted = controller.delete_contact(
        contact_id=contact_id, account=effective_account
    )
    return APIResponseDTO[dict[str, Any]](
        success=True,
        data={"eliminado": deleted, "id_contacto": contact_id},
    )
