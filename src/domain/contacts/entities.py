"""Domain entities for contacts bounded context."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Contact:
    """Immutable entity representing an address book contact."""

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
    eliminado: bool = False
    cuenta: str = ""
    grupos: list[str] = field(default_factory=list[str])


@dataclass(frozen=True)
class ContactGroup:
    """Immutable entity representing a contact group/category."""

    id_grupo: str
    nombre: str
    cuenta: str = ""
    total_contactos: int = 0
