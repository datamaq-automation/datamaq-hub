"""Domain services for salary receipts domain."""

import re
import unicodedata

from src.domain.recibos.entities import (
    LiquidacionSecuencia,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoConcepto


class TextNormalizerService:
    """Sanitizes text, resolves OCR mis-encodings, and normalizes whitespaces."""

    @staticmethod
    def normalize(text: str | None) -> str:
        if not text:
            return ""

        t = str(text)
        t = t.replace("AGUSTÁN", "AGUSTÍN")
        t = re.sub(r"EDUCACI\?N", "EDUCACIÓN", t)
        t = re.sub(r"\bEDUCACIÓ\b", "EDUCACIÓN", t)

        t = unicodedata.normalize("NFKC", t)
        t = re.sub(r"[ \t]+", " ", t)
        return t.strip()

    @staticmethod
    def extract_regex(
        pattern: str | re.Pattern, text: str, group: int = 0
    ) -> str | None:
        m = re.search(pattern, text)
        if m:
            return m.group(group)
        return None


class TotalesCalculatorService:
    """Consolidates subtotals across sequences and checks consistency."""

    @staticmethod
    def calculate(
        liquidaciones: list[LiquidacionSecuencia],
        resumen_liquidos: list[ResumenLiquidoItem] | None = None,
    ) -> TotalesConsolidados:
        total_rem = 0.0
        total_no_rem = 0.0
        total_haberes = 0.0
        total_desc = 0.0
        total_liq = 0.0

        for liq in liquidaciones:
            for c in liq.conceptos:
                if c.tipo == TipoConcepto.REMUNERATIVO:
                    val = c.haberes or 0.0
                    total_rem += val
                    total_haberes += val
                elif c.tipo == TipoConcepto.NO_REMUNERATIVO:
                    val = c.haberes or 0.0
                    total_no_rem += val
                    total_haberes += val
                elif c.tipo == TipoConcepto.DESCUENTO:
                    val = c.descuentos or 0.0
                    total_desc += val

            total_liq += liq.liquido_calculado

        if resumen_liquidos:
            sum_resumen = sum(r.liquido_pesos for r in resumen_liquidos)
            if abs(sum_resumen - total_liq) < 0.1:
                total_liq = sum_resumen

        return TotalesConsolidados(
            total_haberes_remunerativos=round(total_rem, 2),
            total_haberes_no_remunerativos=round(total_no_rem, 2),
            total_haberes=round(total_haberes, 2),
            total_descuentos=round(total_desc, 2),
            total_liquido=round(total_liq, 2),
        )
