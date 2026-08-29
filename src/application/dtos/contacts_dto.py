"""Pydantic v2 DTOs for contacts bounded context."""

from pydantic import BaseModel, Field


class ContactDTO(BaseModel):
    """Output DTO for a contact item."""

    id_contacto: str
    nombre: str
    nombre_pila: str = ""
    apellido: str = ""
    email: str = ""
    telefono: str = ""
    organizacion: str = ""
    notas: str = ""
    vcard: str = ""
    modificado: str = ""
    cuenta: str = ""
    grupos: list[str] = Field(default_factory=list[str])


class CreateContactDTO(BaseModel):
    """Input DTO for creating a new contact."""

    nombre: str = Field(..., description="Nombre completo del contacto")
    nombre_pila: str = Field(default="", description="Nombre de pila")
    apellido: str = Field(default="", description="Apellido")
    email: str = Field(default="", description="Correo electrónico")
    telefono: str = Field(default="", description="Número de teléfono")
    organizacion: str = Field(default="", description="Empresa u organización")
    notas: str = Field(default="", description="Notas adicionales")
    cuenta: str | None = Field(
        default=None, description="Cuenta de correo asociada (opcional)"
    )


class UpdateContactDTO(BaseModel):
    """Input DTO for updating an existing contact."""

    nombre: str | None = Field(default=None, description="Nombre completo")
    nombre_pila: str | None = Field(default=None, description="Nombre de pila")
    apellido: str | None = Field(default=None, description="Apellido")
    email: str | None = Field(default=None, description="Correo electrónico")
    telefono: str | None = Field(default=None, description="Teléfono")
    organizacion: str | None = Field(default=None, description="Organización")
    notas: str | None = Field(default=None, description="Notas")
    cuenta: str | None = Field(default=None, description="Cuenta de correo asociada")


class ContactListResponseDTO(BaseModel):
    """Paginated list response for contacts."""

    total: int
    cuenta: str
    contactos: list[ContactDTO] = Field(default_factory=list[ContactDTO])


class ContactoCompactoDTO(BaseModel):
    """Proyección reducida de contacto para consumo de bajo-token (OpenClaw)."""

    id_contacto: str
    nombre: str
    email: str = ""
    telefono: str = ""
    organizacion: str = ""


class ContactListCompactResponseDTO(BaseModel):
    """Lista paginada con contactos proyectados de forma compacta."""

    total: int
    cuenta: str
    contactos: list[ContactoCompactoDTO] = Field(
        default_factory=list[ContactoCompactoDTO]
    )
