"""Value objects for contacts domain."""

import re
from dataclasses import dataclass

from src.domain.contacts.exceptions import InvalidContactDataError


@dataclass(frozen=True)
class ContactId:
    """Immutable identifier for contacts."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not str(self.value).strip():
            raise InvalidContactDataError(
                "El identificador de contacto no puede estar vacío."
            )
        object.__setattr__(self, "value", str(self.value).strip())


@dataclass(frozen=True)
class EmailAddress:
    """Immutable validated email address."""

    value: str

    def __post_init__(self) -> None:
        raw = str(self.value).strip().lower()
        if not raw:
            raise InvalidContactDataError("El correo electrónico no puede estar vacío.")
        if "@" not in raw or "." not in raw.split("@")[-1]:
            raise InvalidContactDataError(f"Formato de email inválido: '{raw}'")
        object.__setattr__(self, "value", raw)


@dataclass(frozen=True)
class PhoneNumber:
    """Immutable phone number with sanitized representation."""

    value: str

    def __post_init__(self) -> None:
        raw = str(self.value).strip()
        # Keep digits, +, -, (, ), spaces
        cleaned = re.sub(r"[^\d+\-()\s]", "", raw)
        object.__setattr__(self, "value", cleaned)
