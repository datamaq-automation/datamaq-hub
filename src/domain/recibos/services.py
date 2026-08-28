"""Domain services for salary receipts domain."""

import re
import unicodedata
from typing import Any

from src.domain.recibos.entities import (
    EstadoLineaConciliacion,
    LineaConciliada,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResultadoConciliacion,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoConcepto

TOLERANCIA_REDONDEO_CENTAVOS: float = 0.10


class TextNormalizerService:
    """Sanitizes text, resolves OCR mis-encodings, and normalizes whitespaces."""

    @staticmethod
    def normalize(text: str | None) -> str:
        if not text:
            return ""

        t = str(text)
        t = re.sub(r"EDUCACI\?N", "EDUCACIÓN", t)
        t = re.sub(r"\bEDUCACIÓ\b", "EDUCACIÓN", t)

        t = unicodedata.normalize("NFKC", t)
        t = re.sub(r"[ \t]+", " ", t)
        return t.strip()

    @staticmethod
    def extract_regex(
        pattern: str | re.Pattern[str], text: str, group: int = 0
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
            if abs(sum_resumen - total_liq) <= TOLERANCIA_REDONDEO_CENTAVOS:
                total_liq = sum_resumen

        return TotalesConsolidados(
            total_haberes_remunerativos=round(total_rem, 2),
            total_haberes_no_remunerativos=round(total_no_rem, 2),
            total_haberes=round(total_haberes, 2),
            total_descuentos=round(total_desc, 2),
            total_liquido=round(total_liq, 2),
        )


class ConciliadorReciboDocenteService:
    """Motor de conciliación automática entre un recibo mensual y las designaciones docentes históricas."""

    @classmethod
    def conciliar(
        cls,
        recibo: ReciboSueldo,
        designaciones: list[Any],
    ) -> ResultadoConciliacion:
        mes_pago_norm = cls._normalizar_mes_pago(recibo.agente.mes_pago)
        docente_cuit = recibo.agente.cuil.replace("-", "").strip()

        lineas_conciliadas: list[LineaConciliada] = []
        lineas_huerfanas: list[LineaConciliada] = []
        designaciones_matcheadas_ids: set[str] = set()

        total_recibo = 0.0
        total_conciliado = 0.0
        total_huerfano = 0.0

        # Mapear secuencias y liquidaciones detalladas
        liq_map: dict[str, Any] = {}
        for liq in recibo.liquidaciones:
            key = f"{liq.establecimiento.codigo or ''}-{liq.cargo.secuencia}"
            liq_map[key] = liq

        # Iterar sobre las líneas del resumen de líquidos
        items_a_evaluar: list[ResumenLiquidoItem] = (
            recibo.resumen_liquidos
            if recibo.resumen_liquidos
            else [
                ResumenLiquidoItem(
                    secuencia=l.cargo.secuencia,
                    establecimiento_codigo=l.establecimiento.codigo or "",
                    periodo_liquidado=l.cargo.periodo_liquidado or mes_pago_norm,
                    fecha_pago="",
                    orden_pago_codigo="",
                    orden_pago_descripcion="",
                    liquido_pesos=l.liquido_calculado,
                )
                for l in recibo.liquidaciones
            ]
        )

        for item in items_a_evaluar:
            secuencia = str(item.secuencia).strip()
            escuela_cod = str(item.establecimiento_codigo).strip()
            periodo_liq = cls._normalizar_periodo_liquidado(item.periodo_liquidado)
            monto = float(item.liquido_pesos)
            total_recibo += monto

            es_retroactivo = periodo_liq < mes_pago_norm

            # Obtener datos de la liquidación si están disponibles
            liq_detail = liq_map.get(f"{escuela_cod}-{secuencia}")
            modulos_recibo = (
                float(liq_detail.cargo.carga_horaria or 0.0) if liq_detail else 0.0
            )
            revista_recibo = (
                str(liq_detail.cargo.situacion_revista or "").upper()
                if liq_detail
                else ""
            )

            # Buscar designación coincidente
            desig_match, motivo = cls._buscar_designacion_coincidente(
                escuela_cod=escuela_cod,
                secuencia=secuencia,
                periodo_liq=periodo_liq,
                modulos=modulos_recibo,
                revista=revista_recibo,
                designaciones=designaciones,
            )

            if desig_match:
                id_desig = getattr(desig_match, "id_designacion", None)
                if id_desig:
                    designaciones_matcheadas_ids.add(str(id_desig))

                modulos_desig = float(getattr(desig_match, "modulos", 0.0))
                revista_desig = str(getattr(desig_match, "revista", "")).upper()
                fecha_hasta = getattr(desig_match, "fecha_hasta", None)
                if hasattr(desig_match, "vigencia") and desig_match.vigencia:
                    fecha_hasta = getattr(desig_match.vigencia, "fecha_hasta", None)

                # Clasificar estado
                if fecha_hasta is not None and es_retroactivo:
                    estado = EstadoLineaConciliacion.CONCILIADO_RETROACTIVO
                    obs = f"Suplencia/cargo cesado el {fecha_hasta}, cobrado retroactivo en {mes_pago_norm} ({motivo})"
                elif (
                    modulos_recibo > 0
                    and modulos_desig > 0
                    and abs(modulos_recibo - modulos_desig) > 0.01
                ):
                    estado = EstadoLineaConciliacion.DISCREPANCIA
                    obs = f"Discrepancia en módulos: recibo={modulos_recibo} vs designación={modulos_desig} ({motivo})"
                else:
                    estado = EstadoLineaConciliacion.CONCILIADO_EXACTO
                    obs = f"Conciliado correctamente ({motivo})"

                linea = LineaConciliada(
                    id_designacion=str(id_desig) if id_desig else None,
                    secuencia=secuencia,
                    escuela_codigo=escuela_cod,
                    periodo_liquidado=periodo_liq,
                    revista_recibo=revista_recibo,
                    revista_designacion=revista_desig,
                    modulos_recibo=modulos_recibo,
                    modulos_designacion=modulos_desig,
                    liquido_pesos=round(monto, 2),
                    estado=estado,
                    es_retroactivo=es_retroactivo,
                    observacion=obs,
                )
                lineas_conciliadas.append(linea)
                total_conciliado += monto
            else:
                # Línea huérfana en el recibo
                linea = LineaConciliada(
                    id_designacion=None,
                    secuencia=secuencia,
                    escuela_codigo=escuela_cod,
                    periodo_liquidado=periodo_liq,
                    revista_recibo=revista_recibo,
                    revista_designacion=None,
                    modulos_recibo=modulos_recibo,
                    modulos_designacion=None,
                    liquido_pesos=round(monto, 2),
                    estado=EstadoLineaConciliacion.HUERFANA_RECIBO,
                    es_retroactivo=es_retroactivo,
                    observacion="Línea liquidada en recibo sin designación registrada en el sistema",
                )
                lineas_huerfanas.append(linea)
                total_huerfano += monto

        # Detectar designaciones no cobradas durante el mes_pago
        designaciones_no_cobradas: list[LineaConciliada] = []
        for d in designaciones:
            id_d = str(getattr(d, "id_designacion", ""))
            if (
                id_d
                and id_d not in designaciones_matcheadas_ids
                and cls._designacion_estaba_vigente_en(d, mes_pago_norm)
            ):
                sec_d = str(getattr(d, "secuencia", "") or "")
                esc_d = str(
                    getattr(d, "escuela_numero", "")
                    or getattr(d, "establecimiento", "")
                )
                mod_d = float(getattr(d, "modulos", 0.0))
                rev_d = str(getattr(d, "revista", ""))

                linea_no_cobrada = LineaConciliada(
                    id_designacion=id_d,
                    secuencia=sec_d,
                    escuela_codigo=esc_d,
                    periodo_liquidado=mes_pago_norm,
                    revista_recibo="",
                    revista_designacion=rev_d,
                    modulos_recibo=0.0,
                    modulos_designacion=mod_d,
                    liquido_pesos=0.0,
                    estado=EstadoLineaConciliacion.HUERFANA_DESIGNACION,
                    es_retroactivo=False,
                    observacion="Designación vigente en el período que no figura liquidada en este recibo",
                )
                designaciones_no_cobradas.append(linea_no_cobrada)

        es_completa = len(lineas_huerfanas) == 0 and len(designaciones_no_cobradas) == 0

        return ResultadoConciliacion(
            id_recibo=recibo.id_recibo,
            mes_pago=mes_pago_norm,
            docente_cuit=docente_cuit,
            total_lineas_recibo=len(items_a_evaluar),
            total_designaciones_evaluadas=len(designaciones),
            lineas_conciliadas=lineas_conciliadas,
            lineas_huerfanas_recibo=lineas_huerfanas,
            designaciones_no_cobradas=designaciones_no_cobradas,
            total_liquidado_recibo=round(total_recibo, 2),
            total_liquidado_conciliado=round(total_conciliado, 2),
            total_liquidado_huerfano=round(total_huerfano, 2),
            es_conciliacion_completa=es_completa,
        )

    @staticmethod
    def _normalizar_mes_pago(mes_pago: str) -> str:
        s = str(mes_pago).strip().replace("/", "-")
        if "-" in s:
            parts = s.split("-")
            if len(parts[0]) == 4:
                return f"{parts[0]}-{parts[1].zfill(2)}"
            if len(parts[1]) == 4:
                return f"{parts[1]}-{parts[0].zfill(2)}"
        if len(s) == 6 and s.isdigit():
            return f"{s[:4]}-{s[4:]}"
        return s

    @staticmethod
    def _normalizar_periodo_liquidado(periodo: str) -> str:
        s = str(periodo).strip().replace("/", "-")
        if len(s) == 6 and s.isdigit():
            return f"{s[:4]}-{s[4:]}"
        if "-" in s:
            parts = s.split("-")
            if len(parts[0]) == 4:
                return f"{parts[0]}-{parts[1].zfill(2)}"
        return s

    @classmethod
    def _buscar_designacion_coincidente(
        cls,
        escuela_cod: str,
        secuencia: str,
        periodo_liq: str,
        modulos: float,
        revista: str,
        designaciones: list[Any],
    ) -> tuple[Any | None, str]:
        # Paso 1: Coincidencia exacta por secuencia + escuela compatible + período
        for d in designaciones:
            sec_d = str(getattr(d, "secuencia", "") or "").strip()
            if (
                sec_d
                and cls._secuencias_coinciden(sec_d, secuencia)
                and cls._designacion_cubre_periodo(d, periodo_liq)
                and cls._escuela_es_compatible(d, escuela_cod)
            ):
                return (
                    d,
                    "Coincidencia exacta por número de secuencia y escuela",
                )

        # Paso 2: Coincidencia por código de escuela + período + módulos
        for d in designaciones:
            if cls._escuela_es_compatible(
                d, escuela_cod
            ) and cls._designacion_cubre_periodo(d, periodo_liq):
                mod_d = float(getattr(d, "modulos", 0.0))
                if modulos > 0 and mod_d > 0 and abs(mod_d - modulos) < 0.01:
                    return d, "Coincidencia por escuela y carga de módulos"

        # Paso 3: Coincidencia por escuela + período (si no hay ambigüedad)
        matches_escuela = [
            d
            for d in designaciones
            if cls._escuela_es_compatible(d, escuela_cod)
            and cls._designacion_cubre_periodo(d, periodo_liq)
        ]

        if len(matches_escuela) == 1:
            return matches_escuela[
                0
            ], "Coincidencia unívoca por establecimiento educativo"

        return None, ""

    @staticmethod
    def _secuencias_coinciden(sec1: str, sec2: str) -> bool:
        if sec1 == sec2:
            return True
        try:
            return int(sec1) == int(sec2)
        except ValueError:
            return False

    @classmethod
    def _escuela_es_compatible(cls, desig: Any, esc_recibo: str) -> bool:
        recibo_str = esc_recibo.lower().strip()
        if not recibo_str:
            return False

        esc_num_desig = str(getattr(desig, "escuela_numero", "") or "").lower().strip()
        estab_desig = str(getattr(desig, "establecimiento", "") or "").lower().strip()
        distrito_desig = str(getattr(desig, "distrito", "") or "").lower().strip()

        # Distrito mismatch check
        if (
            recibo_str.startswith("116")
            and distrito_desig
            and "escobar" not in distrito_desig
        ):
            return False
        if (
            recibo_str.startswith("055")
            and distrito_desig
            and not any(k in distrito_desig for k in ("tigre", "san fernando", "055"))
        ):
            return False

        # Si el establecimiento o número coincide directamente
        if esc_num_desig and (
            esc_num_desig in recibo_str or recibo_str in esc_num_desig
        ):
            if distrito_desig:
                if "pilar" in distrito_desig and "116" in recibo_str:
                    return False
                if "pilar" in distrito_desig and "055" in recibo_str:
                    return False
            return True

        return bool(
            estab_desig and (estab_desig in recibo_str or recibo_str in estab_desig)
        )

    @classmethod
    def _designacion_cubre_periodo(cls, desig: Any, periodo_ym: str) -> bool:
        fecha_desde_str = str(getattr(desig, "fecha_desde", ""))
        fecha_hasta_str = getattr(desig, "fecha_hasta", None)
        if hasattr(desig, "vigencia") and desig.vigencia:
            vig = desig.vigencia
            fecha_desde_str = str(getattr(vig, "fecha_desde", ""))
            fecha_hasta_str = getattr(vig, "fecha_hasta", None)

        if not fecha_desde_str:
            return True

        desde_ym = fecha_desde_str[:7]
        if periodo_ym < desde_ym:
            return False

        if fecha_hasta_str:
            hasta_ym = str(fecha_hasta_str)[:7]
            if periodo_ym > hasta_ym:
                return False

        return True

    @classmethod
    def _designacion_estaba_vigente_en(cls, desig: Any, mes_pago_ym: str) -> bool:
        return cls._designacion_cubre_periodo(desig, mes_pago_ym)
