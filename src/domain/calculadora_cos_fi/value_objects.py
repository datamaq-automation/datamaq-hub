"""Value objects para la calculadora de factor de potencia y dimensionamiento de capacitores."""

from dataclasses import dataclass
from enum import Enum


class EstadoCosFi(str, Enum):
    """Estado del factor de potencia de la instalación eléctrica."""

    OPTIMO = "optimo"  # cos fi >= 0.95 (sin recargos)
    MULTA_LEVE = "multa_leve"  # 0.85 <= cos fi < 0.95 (recargo moderado)
    MULTA_CRITICA = "multa_critica"  # cos fi < 0.85 (recargo severo)


@dataclass(frozen=True)
class CalculoPenalidad:
    """Resultado del cálculo determinístico de penalidad y compensación."""

    cos_fi_medido: float
    cos_fi_objetivo: float
    recargo_porcentaje: float
    recargo_mensual_ars: float
    recargo_anual_ars: float
    potencia_reactiva_kvar: float
    banco_capacitores_recomendado_kvar: float
    estado: EstadoCosFi
    mensaje_diagnostico: str
