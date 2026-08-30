"""Entidades de dominio para resúmenes de tarjetas de crédito."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class TransaccionTarjeta:
    """Transacción individual registrada en el resumen de una tarjeta de crédito."""

    fecha: date
    descripcion: str
    monto_pesos: float
    monto_dolares: float
    nro_cupon: str = ""


@dataclass(frozen=True)
class ResumenTarjeta:
    """Resumen consolidado de una tarjeta de crédito."""

    id_resumen: str
    banco: str
    tarjeta_tipo: str
    tarjeta_categoria: str
    numero_cuenta: str
    fecha_cierre: date
    fecha_vencimiento: date
    saldo_pesos: float
    saldo_dolares: float
    pago_minimo: float
    consumos: tuple[TransaccionTarjeta, ...] = field(
        default_factory=tuple[TransaccionTarjeta, ...]
    )
