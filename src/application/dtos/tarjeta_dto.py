"""DTOs de aplicación para resúmenes de tarjetas de crédito."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TransaccionTarjetaDTO(BaseModel):
    """Transacción individual registrada en el resumen de una tarjeta."""

    model_config = ConfigDict(extra="forbid")

    fecha: date
    descripcion: str
    monto_pesos: float
    monto_dolares: float
    nro_cupon: str = ""


class ResumenTarjetaDTO(BaseModel):
    """Resumen consolidado de una tarjeta de crédito."""

    model_config = ConfigDict(extra="forbid")

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
    consumos: list[TransaccionTarjetaDTO] = Field(
        default_factory=list[TransaccionTarjetaDTO]
    )
