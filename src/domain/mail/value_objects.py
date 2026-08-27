"""Value objects for mail domain."""

import re
from dataclasses import dataclass

from src.domain.mail.exceptions import InvalidEmailAddressError

EMAIL_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9_.+-]+|<[^>]+>)?\s*(?:<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?)?$"
)


@dataclass(frozen=True)
class EmailAddress:
    """Value object representing an email address with validation."""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip()
        if not raw:
            raise InvalidEmailAddressError(self.value)
        # Check basic structure
        if "@" not in raw:
            raise InvalidEmailAddressError(self.value)
        # Normalized storage
        object.__setattr__(self, "value", raw)

    @property
    def clean_address(self) -> str:
        """Returns the clean email address without display name or angle brackets."""
        if "<" in self.value and ">" in self.value:
            start = self.value.find("<")
            end = self.value.find(">")
            return self.value[start + 1 : end].strip()
        return self.value.strip()


@dataclass(frozen=True)
class EmailUID:
    """Value object representing an IMAP unique identifier."""

    value: str

    def __post_init__(self) -> None:
        raw = str(self.value).strip()
        if not raw:
            raise ValueError(
                "El identificador único de correo (UID) no puede estar vacío."
            )
        object.__setattr__(self, "value", raw)


@dataclass(frozen=True)
class FolderName:
    """Value object representing an IMAP folder name."""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.strip().strip('"').strip("'")
        if not raw:
            raw = "INBOX"
        object.__setattr__(self, "value", raw)
