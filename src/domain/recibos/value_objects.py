"""Domain Value Objects for salary receipts domain."""

import re
from dataclasses import dataclass
from enum import Enum

from src.domain.recibos.exceptions import InvalidIdentifierError


class TipoConcepto(str, Enum):
    """Concept categorization."""

    REMUNERATIVO = "remunerativo"
    NO_REMUNERATIVO = "no_remunerativo"
    DESCUENTO = "descuento"


class TipoRecibo(str, Enum):
    """Salary receipt template / organization type."""

    DGCYE_PBA = "DGCYE_PBA"
    GENERICO = "GENERICO"


@dataclass(frozen=True)
class CUIT:
    """Argentine Tax/Labor Identification Number (CUIT/CUIL).

    Validates using Modulo 11 check algorithm.
    """

    value: str

    def __post_init__(self) -> None:
        clean = re.sub(r"\D", "", self.value)
        if not self._is_valid(clean):
            raise InvalidIdentifierError(f"Invalid CUIT/CUIL: '{self.value}'")
        formatted = f"{clean[:2]}-{clean[2:10]}-{clean[10]}"
        object.__setattr__(self, "value", formatted)

    @classmethod
    def from_string(cls, raw: str | None) -> "CUIT | None":
        """Factory method returning None on failure."""
        if not raw:
            return None
        try:
            return cls(raw)
        except InvalidIdentifierError:
            return None

    @staticmethod
    def _is_valid(clean_cuit: str) -> bool:
        if len(clean_cuit) != 11:
            return False

        multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        digits = [int(d) for d in clean_cuit]

        total = sum(d * m for d, m in zip(digits[:10], multipliers))
        mod = 11 - (total % 11)

        if mod == 11:
            expected = 0
        elif mod == 10:
            expected = 9
        else:
            expected = mod

        return digits[10] == expected

    @property
    def unformatted(self) -> str:
        """Return pure numeric 11 digits."""
        return self.value.replace("-", "")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DNI:
    """Argentine National Identity Document (DNI)."""

    value: str
    doc_type: str = "DNI"

    def __post_init__(self) -> None:
        clean = re.sub(r"\D", "", self.value)
        if not (6 <= len(clean) <= 8):
            raise InvalidIdentifierError(
                f"Invalid DNI: '{self.value}' (must have between 6 and 8 digits)"
            )
        object.__setattr__(self, "value", clean)

    @classmethod
    def from_string(cls, raw: str | None, doc_type: str = "DNI") -> "DNI | None":
        """Factory method returning None on failure."""
        if not raw:
            return None
        try:
            return cls(value=raw, doc_type=doc_type)
        except InvalidIdentifierError:
            return None

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ImporteMonetario:
    """Immutable monetary representation in ARS rounded to 2 decimal places."""

    amount: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", round(float(self.amount), 2))

    @classmethod
    def zero(cls) -> "ImporteMonetario":
        return cls(0.0)

    @classmethod
    def from_raw(cls, val: str | float | None) -> "ImporteMonetario":
        """Parse string or numeric representation."""
        if val is None:
            return cls.zero()
        if isinstance(val, (int, float)):
            return cls(round(float(val), 2))

        raw = str(val).strip()
        if not raw:
            return cls.zero()

        is_negative = False
        if raw.startswith("(") and raw.endswith(")"):
            is_negative = True
            raw = raw[1:-1].strip()
        elif raw.startswith("-"):
            is_negative = True
            raw = raw[1:].strip()

        raw = re.sub(r"[^\d.,]", "", raw)
        if not raw:
            return cls.zero()

        last_dot = raw.rfind(".")
        last_comma = raw.rfind(",")

        if last_dot != -1 and last_comma != -1:
            if last_comma > last_dot:
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif last_comma != -1:
            raw = raw.replace(",", ".")

        try:
            parsed = float(raw)
            if is_negative:
                parsed = -parsed
            return cls(round(parsed, 2))
        except ValueError:
            return cls.zero()

    def __add__(self, other: "ImporteMonetario | float | int") -> "ImporteMonetario":
        val = other.amount if isinstance(other, ImporteMonetario) else float(other)
        return ImporteMonetario(self.amount + val)

    def __sub__(self, other: "ImporteMonetario | float | int") -> "ImporteMonetario":
        val = other.amount if isinstance(other, ImporteMonetario) else float(other)
        return ImporteMonetario(self.amount - val)

    def __float__(self) -> float:
        return self.amount

    def __str__(self) -> str:
        return f"{self.amount:.2f}"
