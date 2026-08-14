"""Value objects for salary settlement and projection domain."""

from dataclasses import dataclass
from enum import Enum


class NivelCargo(str, Enum):
    """Educational level / position type."""

    SM = "SM"  # Módulo Nivel Superior
    PM = "PM"  # Módulo Nivel Secundario / Técnico
    PR = "PR"  # Preceptor / Cargo Base


class SituacionRevista(str, Enum):
    """Employment condition in DGCyE."""

    TITULAR = "TIT."
    PROVISIONAL = "PROV."
    SUPLENTE = "SUP."


class TipoConceptoLiquidacion(str, Enum):
    """Concept classification."""

    REMUNERATIVO = "remunerativo"
    NO_REMUNERATIVO = "no_remunerativo"
    DESCUENTO = "descuento"


class CodigoConceptoLiquidacion(str, Enum):
    """Standard liquidation concept codes for DGCyE PBA."""

    BASICO_PROVISIONAL = "0510"
    BASICO_SUPLENTE = "0511"
    ANTIGUEDAD = "0220"
    BONIF_0455 = "0455"
    BONIF_0667 = "0667"
    BONIF_2575 = "2575"
    SAC = "0820"
    RETENCION_BASICO_PARO = "1173"
    RETENCION_ANTIG_PARO = "1273"
    IPS = "1060"
    IOMA = "1280"
    SUTEBA_SINDICATO = "1472"
    SUTEBA_OBRA_SOCIAL = "1473"


class DescripcionConceptoLiquidacion(str, Enum):
    """Standard liquidation concept descriptions."""

    BASICO_PROVISIONAL = "BASICO PROVISIONALES"
    BASICO_SUPLENTE = "BASICO SUPLENTES"
    ANTIGUEDAD = "ANTIGUEDAD"
    BONIF_0455 = "BONIF. REMUN. DOC 08/2008"
    BONIF_0667 = "BONIF.NO JERARQUICA MAR/2014"
    BONIF_2575 = "BON NO REM COMP.FONID/CONECTIV"
    SAC = "SUELDO ANUAL COMPLEM."
    RETENCION_BASICO_PARO = "RETENCION BASICO - PAROS"
    RETENCION_ANTIG_PARO = "RETENCION ANTIG - PAROS"
    IPS = "I.P.S."
    IOMA = "I.O.M.A"
    SUTEBA_SINDICATO = "SUTEBA SINDICATO"
    SUTEBA_OBRA_SOCIAL = "SUTEBA OBRA SOCIAL"


@dataclass(frozen=True)
class ParametrosParitaria:
    """Paritary parameters and unit point values for salary calculation.

    Pure domain Value Object with NO hardcoded default rates.
    """

    periodo: str
    basico_por_modulo_sm: float
    basico_por_modulo_pm: float
    bonif_0455_sm: float
    bonif_0455_pm: float
    bonif_0667_sm: float
    bonif_0667_pm: float
    bonif_2575_sm: float
    bonif_2575_pm: float
    alicuota_ips: float
    alicuota_ioma: float
    alicuota_suteba_sindicato: float
    alicuota_suteba_os: float
    tope_bonificaciones_modulos: float


class EscalaAntiguedad:
    """Official seniority scale for DGCyE PBA teachers."""

    @staticmethod
    def obtener_porcentaje(anios: int) -> float:
        """Returns the statutory seniority percentage for given years of service."""
        if anios < 1:
            return 0.0
        if anios == 1:
            return 0.30
        if anios in (2, 3, 4):
            return 0.33
        if anios in (5, 6):
            return 0.40
        if anios in (7, 8, 9):
            return 0.50
        if anios in (10, 11):
            return 0.60
        if anios in (12, 13, 14):
            return 0.70
        if anios in (15, 16):
            return 0.80
        if anios in (17, 18, 19):
            return 0.90
        if anios in (20, 21):
            return 1.00
        if anios in (22, 23):
            return 1.10
        return 1.20
