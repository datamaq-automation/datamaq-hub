"""Entidades de dominio para la calculadora de factor de potencia."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SolicitudCalculoCosFi:
    """Parámetros de entrada de una instalación eléctrica industrial para calcular cos fi."""

    potencia_kw: float
    cos_fi_actual: float
    factura_base_ars: float = 0.0
    empresa: str = ""
    tarifa: str = "T2/T3"
