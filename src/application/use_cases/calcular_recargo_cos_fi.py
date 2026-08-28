"""Caso de uso para calcular recargo por factor de potencia cos fi y armar propuesta técnica."""

import urllib.parse

from src.application.dtos.calculadora_cos_fi_dtos import (
    CalculoCosFiRequestDTO,
    CalculoCosFiResponseDTO,
)
from src.domain.calculadora_cos_fi.entities import SolicitudCalculoCosFi
from src.domain.calculadora_cos_fi.services import CalculadoraCosFiService


class CalcularRecargoCosFiUseCase:
    """Ejecuta el cálculo determinístico de penalidad y genera la propuesta comercial de DataMaq."""

    def __init__(self, whatsapp_phone: str = "5491136528392") -> None:
        self._whatsapp_phone = whatsapp_phone

    def execute(self, request: CalculoCosFiRequestDTO) -> CalculoCosFiResponseDTO:
        """Calcula el diagnóstico de factor de potencia y construye la respuesta enriquecida."""
        solicitud = SolicitudCalculoCosFi(
            potencia_kw=request.potencia_kw,
            cos_fi_actual=request.cos_fi_actual,
            factura_base_ars=request.factura_base_ars,
            empresa=request.empresa,
            tarifa=request.tarifa,
        )

        resultado = CalculadoraCosFiService.calcular_penalidad(solicitud)

        # Generar texto dinámico para WhatsApp
        if resultado.banco_capacitores_recomendado_kvar > 0:
            msg = (
                f"Hola DataMaq! Hice el cálculo en su web: tenemos una potencia de {request.potencia_kw:.0f} kW "
                f"con un cos φ de {request.cos_fi_actual:.2f}. "
                f"El sistema recomienda un banco de {resultado.banco_capacitores_recomendado_kvar:.1f} kVAr "
                f"(recargo actual: {resultado.recargo_porcentaje:.1f}%). "
                "Quisiera solicitar medición en planta y presupuesto."
            )
        else:
            msg = (
                f"Hola DataMaq! Hice el cálculo en su web para {request.potencia_kw:.0f} kW. "
                "Nuestro cos φ está en norma pero quisiera asesoramiento sobre telemetría y eficiencia energética."
            )

        encoded_msg = urllib.parse.quote(msg)
        whatsapp_url = f"https://wa.me/{self._whatsapp_phone}?text={encoded_msg}"

        return CalculoCosFiResponseDTO(
            cos_fi_actual=resultado.cos_fi_medido,
            cos_fi_objetivo=resultado.cos_fi_objetivo,
            recargo_porcentaje=resultado.recargo_porcentaje,
            recargo_mensual_ars=resultado.recargo_mensual_ars,
            recargo_anual_ars=resultado.recargo_anual_ars,
            potencia_reactiva_kvar=resultado.potencia_reactiva_kvar,
            banco_capacitores_recomendado_kvar=resultado.banco_capacitores_recomendado_kvar,
            estado=resultado.estado.value,
            mensaje_diagnostico=resultado.mensaje_diagnostico,
            whatsapp_url=whatsapp_url,
        )
