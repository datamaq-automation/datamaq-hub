"""Servicio de dominio para cálculo determinístico de multas por factor de potencia cos fi."""

import math
from typing import Final

from src.domain.calculadora_cos_fi.entities import SolicitudCalculoCosFi
from src.domain.calculadora_cos_fi.exceptions import (
    FacturaInvalidaException,
    PotenciaInvalidaException,
    ValorCosFiInvalidoException,
)
from src.domain.calculadora_cos_fi.value_objects import (
    CalculoPenalidad,
    EstadoCosFi,
)

COS_FI_OBJETIVO_ENRE: Final[float] = 0.95

ESCALONES_COMERCIALES_KVAR: Final[list[float]] = [
    2.5,
    5.0,
    7.5,
    10.0,
    12.5,
    15.0,
    20.0,
    25.0,
    30.0,
    40.0,
    50.0,
    60.0,
    75.0,
    90.0,
    100.0,
    125.0,
    150.0,
    175.0,
    200.0,
    250.0,
    300.0,
    400.0,
    500.0,
]


class CalculadoraCosFiService:
    """Calcula penalidades tarifarias ENRE/Edenor y dimensiona el banco de capacitores."""

    @staticmethod
    def calcular_penalidad(solicitud: SolicitudCalculoCosFi) -> CalculoPenalidad:
        """Aplica la fórmula oficial de recargo por bajo factor de potencia y dimensionamiento de reactiva."""
        cos_fi = solicitud.cos_fi_actual
        potencia = solicitud.potencia_kw
        factura = solicitud.factura_base_ars

        if cos_fi <= 0.0 or cos_fi > 1.0:
            raise ValorCosFiInvalidoException(
                f"El valor de cos fi ({cos_fi}) debe estar en el rango (0.0, 1.0]."
            )
        if potencia <= 0.0:
            raise PotenciaInvalidaException(
                f"La potencia activa ({potencia} kW) debe ser mayor a 0."
            )
        if factura < 0.0:
            raise FacturaInvalidaException(
                f"La factura base (${factura}) no puede ser negativa."
            )

        if cos_fi >= COS_FI_OBJETIVO_ENRE:
            return CalculoPenalidad(
                cos_fi_medido=round(cos_fi, 2),
                cos_fi_objetivo=COS_FI_OBJETIVO_ENRE,
                recargo_porcentaje=0.0,
                recargo_mensual_ars=0.0,
                recargo_anual_ars=0.0,
                potencia_reactiva_kvar=0.0,
                banco_capacitores_recomendado_kvar=0.0,
                estado=EstadoCosFi.OPTIMO,
                mensaje_diagnostico=(
                    "¡Excelente! Tu instalación cumple con la reglamentación del ENRE "
                    f"(cos φ = {cos_fi:.2f} ≥ 0.95). No tenés recargos por energía reactiva."
                ),
            )

        # Fórmula ENRE / Edenor: Recargo % = ((0.95 / cos_fi) - 1) * 100
        recargo_porcentaje = round(((COS_FI_OBJETIVO_ENRE / cos_fi) - 1.0) * 100.0, 2)
        recargo_mensual = round(factura * (recargo_porcentaje / 100.0), 2)
        recargo_anual = round(recargo_mensual * 12.0, 2)

        # Cálculo de Qc = P * (tan(phi_1) - tan(phi_2))
        theta_1 = math.acos(cos_fi)
        theta_2 = math.acos(COS_FI_OBJETIVO_ENRE)
        tan_1 = math.tan(theta_1)
        tan_2 = math.tan(theta_2)
        qc_exacta = potencia * (tan_1 - tan_2)
        potencia_reactiva_kvar = round(max(0.0, qc_exacta), 2)

        # Buscar escalón comercial inmediatamente superior
        banco_recomendado = potencia_reactiva_kvar
        for escalon in ESCALONES_COMERCIALES_KVAR:
            if escalon >= potencia_reactiva_kvar:
                banco_recomendado = escalon
                break

        estado = EstadoCosFi.MULTA_CRITICA if cos_fi < 0.85 else EstadoCosFi.MULTA_LEVE

        mensaje = (
            f"Alerta: Tu cos φ actual ({cos_fi:.2f}) genera un recargo del {recargo_porcentaje:.1f}% "
            f"en la factura eléctrica. Necesitás compensar {potencia_reactiva_kvar:.1f} kVAr "
            f"(banco comercial recomendado: {banco_recomendado:.1f} kVAr) para anular la multa."
        )

        return CalculoPenalidad(
            cos_fi_medido=round(cos_fi, 2),
            cos_fi_objetivo=COS_FI_OBJETIVO_ENRE,
            recargo_porcentaje=recargo_porcentaje,
            recargo_mensual_ars=recargo_mensual,
            recargo_anual_ars=recargo_anual,
            potencia_reactiva_kvar=potencia_reactiva_kvar,
            banco_capacitores_recomendado_kvar=banco_recomendado,
            estado=estado,
            mensaje_diagnostico=mensaje,
        )
