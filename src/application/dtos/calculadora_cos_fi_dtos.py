"""DTOs para la calculadora de factor de potencia cos fi."""

from pydantic import BaseModel, ConfigDict, Field


class CalculoCosFiRequestDTO(BaseModel):
    """Solicitud de cálculo de recargo por factor de potencia y compensación."""

    model_config = ConfigDict(extra="forbid")

    potencia_kw: float = Field(
        ...,
        gt=0.0,
        description="Potencia activa contratada o pico de la fábrica en kW",
        examples=[50.0],
    )
    cos_fi_actual: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="Valor actual de cos φ (factor de potencia) medido o en factura",
        examples=[0.78],
    )
    factura_base_ars: float = Field(
        default=0.0,
        ge=0.0,
        description="Importe base mensual de la factura eléctrica en ARS (opcional)",
        examples=[850000.0],
    )
    empresa: str = Field(
        default="",
        description="Nombre de la empresa o fábrica (opcional)",
        examples=["Metalúrgica Tigre"],
    )
    tarifa: str = Field(
        default="T2/T3",
        description="Categoría tarifaria (ej. T2, T3 Edenor/Edesur)",
        examples=["T3"],
    )


class CalculoCosFiResponseDTO(BaseModel):
    """Resultado del cálculo de penalidad tarifaria y propuesta de banco de capacitores."""

    model_config = ConfigDict(extra="forbid")

    cos_fi_actual: float = Field(description="Factor de potencia actual medido")
    cos_fi_objetivo: float = Field(
        description="Factor de potencia reglamentario ENRE (0.95)"
    )
    recargo_porcentaje: float = Field(
        description="Porcentaje de recargo en la factura eléctrica (%)"
    )
    recargo_mensual_ars: float = Field(description="Recargo estimado mensual en ARS")
    recargo_anual_ars: float = Field(description="Recargo acumulado anual en ARS")
    potencia_reactiva_kvar: float = Field(
        description="Potencia reactiva exacta a compensar en kVAr"
    )
    banco_capacitores_recomendado_kvar: float = Field(
        description="Capacidad del banco de capacitores comercial recomendado en kVAr"
    )
    estado: str = Field(
        description="Estado de la instalación ('optimo', 'multa_leve', 'multa_critica')"
    )
    mensaje_diagnostico: str = Field(
        description="Diagnóstico técnico explicativo en español"
    )
    whatsapp_url: str = Field(
        description="Enlace directo pre-formateado a WhatsApp para consultar cotización"
    )
