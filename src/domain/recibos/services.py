"""Domain services for salary receipts domain."""

import re
import unicodedata
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _ItemConciliacionInterno:
    secuencia: str
    establecimiento_codigo: str
    periodo_liquidado: str
    liquido_pesos: float
    modulos: float = 0.0
    revista: str = ""


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
        mes_pago_norm = cls.normalizar_periodo_a_iso(recibo.agente.mes_pago)
        docente_cuit = recibo.agente.cuil.replace("-", "").strip()

        lineas_conciliadas: list[LineaConciliada] = []
        lineas_huerfanas: list[LineaConciliada] = []
        designaciones_matcheadas_ids: set[str] = set()
        # Track designaciones ya usadas por cada período devengado
        designaciones_usadas_por_periodo: dict[str, set[str]] = {}

        total_recibo = 0.0
        total_conciliado = 0.0
        total_huerfano = 0.0

        # Mapear secuencias y liquidaciones detalladas
        liq_map: dict[str, Any] = {}
        for liq in recibo.liquidaciones:
            key = f"{liq.establecimiento.codigo or ''}-{liq.cargo.secuencia}"
            liq_map[key] = liq

        # Construir items a conciliar directamente desde las liquidaciones detalladas
        # (o fallback a resumen de líquidos si no hubiera liquidaciones)
        items_a_evaluar: list[_ItemConciliacionInterno] = []
        if recibo.liquidaciones:
            items_a_evaluar = [
                _ItemConciliacionInterno(
                    secuencia=l.cargo.secuencia,
                    establecimiento_codigo=f"{l.establecimiento.distrito or ''} {l.establecimiento.codigo or ''}".strip(),
                    periodo_liquidado=l.cargo.periodo_liquidado or mes_pago_norm,
                    liquido_pesos=l.liquido_calculado,
                    modulos=float(l.cargo.carga_horaria or 0.0),
                    revista=str(l.cargo.situacion_revista or "").upper(),
                )
                for l in recibo.liquidaciones
            ]
        elif recibo.resumen_liquidos:
            items_a_evaluar = [
                _ItemConciliacionInterno(
                    secuencia=r.secuencia,
                    establecimiento_codigo=r.establecimiento_codigo,
                    periodo_liquidado=r.periodo_liquidado,
                    liquido_pesos=r.liquido_pesos,
                    modulos=0.0,
                    revista="",
                )
                for r in recibo.resumen_liquidos
            ]

        for item in items_a_evaluar:
            secuencia = str(item.secuencia).strip()
            escuela_cod = str(item.establecimiento_codigo).strip()
            periodo_liq = cls.normalizar_periodo_a_iso(item.periodo_liquidado)
            monto = float(item.liquido_pesos)
            total_recibo += monto

            es_retroactivo = periodo_liq < mes_pago_norm
            modulos_recibo = float(getattr(item, "modulos", 0.0))
            revista_recibo = str(getattr(item, "revista", ""))

            usadas_este_periodo = designaciones_usadas_por_periodo.setdefault(
                periodo_liq, set()
            )
            desigs_candidatas = [
                d
                for d in designaciones
                if str(getattr(d, "id_designacion", "")) not in usadas_este_periodo
            ]

            # Buscar designación coincidente
            desig_match, motivo = cls._buscar_designacion_coincidente(
                escuela_cod=escuela_cod,
                secuencia=secuencia,
                periodo_liq=periodo_liq,
                modulos=modulos_recibo,
                revista=revista_recibo,
                designaciones=desigs_candidatas,
            )

            if desig_match:
                id_desig = getattr(desig_match, "id_designacion", None)
                if id_desig:
                    id_str = str(id_desig)
                    designaciones_matcheadas_ids.add(id_str)
                    usadas_este_periodo.add(id_str)

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

    @classmethod
    def extraer_anio_mes(cls, periodo: str) -> tuple[int, int]:
        """Extrae de forma robusta (año, mes) a partir de cualquier formato de período.
        Soporta: '2026-07', '07-2026', '07/2026', '07 / 2026', '202607', '072026', etc.
        """
        raw = str(periodo or "").strip()
        str_nums = re.findall(r"\d+", raw)
        if len(str_nums) >= 2:
            n1, n2 = int(str_nums[0]), int(str_nums[1])
            if 1900 <= n1 <= 2100 and 1 <= n2 <= 12:
                return n1, n2
            if 1900 <= n2 <= 2100 and 1 <= n1 <= 12:
                return n2, n1
        elif len(str_nums) == 1:
            s = str_nums[0]
            if len(s) == 6:
                p1, p2 = int(s[:4]), int(s[4:])
                if 1900 <= p1 <= 2100 and 1 <= p2 <= 12:
                    return p1, p2
                p1, p2 = int(s[:2]), int(s[2:])
                if 1900 <= p2 <= 2100 and 1 <= p1 <= 12:
                    return p2, p1
        return 2026, 1

    @classmethod
    def normalizar_periodo_a_iso(cls, periodo: str) -> str:
        anio, mes = cls.extraer_anio_mes(periodo)
        return f"{anio:04d}-{mes:02d}"

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
        # Candidatos que cubren el período liquidado
        candidatos: list[tuple[int, Any, str]] = []

        for d in designaciones:
            if not cls._designacion_cubre_periodo(d, periodo_liq):
                continue

            sec_d = str(getattr(d, "secuencia", "") or "").strip()
            score = 0
            motivos: list[str] = []

            # 1. Coincidencia por secuencia (máxima prioridad si existe)
            if sec_d and cls._secuencias_coinciden(sec_d, secuencia):
                score += 1000
                motivos.append("número de secuencia exacto")

            # 2. Compatibilidad de escuela y distrito
            escuela_compat = cls._escuela_es_compatible(d, escuela_cod)
            if escuela_compat:
                score += 500
                motivos.append("establecimiento/distrito compatible")
            elif not sec_d:
                # Si no coincide la escuela y no hay secuencia, descartar
                continue

            # 3. Coincidencia por carga horaria / módulos
            mod_d = float(getattr(d, "modulos", 0.0))
            if modulos > 0 and mod_d > 0 and abs(mod_d - modulos) < 0.01:
                score += 200
                motivos.append(f"{modulos} módulos")
            elif modulos > 0 and mod_d > 0:
                # Penalizar ligera discrepancia si hay candidatos con módulos exactos
                score += 50

            # 4. Coincidencia por situación de revista
            rev_d = str(getattr(d, "revista", "")).upper()
            if revista and rev_d and (revista in rev_d or rev_d in revista):
                score += 50
                motivos.append(f"revista {revista}")

            if score >= 700:
                candidatos.append((score, d, ", ".join(motivos)))

        if not candidatos:
            return None, ""

        # Ordenar por mayor score descendente
        candidatos.sort(key=lambda x: x[0], reverse=True)
        _score, best_d, best_motivo = candidatos[0]
        return best_d, f"Coincidencia ({best_motivo})"

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

        # Extraer distrito del recibo
        recibo_nums = [int(n) for n in re.findall(r"\d+", recibo_str)]
        recibo_distrito_num = recibo_str[:3] if len(recibo_str) >= 3 else ""

        # Control de compatibilidad distrital
        if recibo_distrito_num == "116":
            if distrito_desig and "escobar" not in distrito_desig:
                return False
            if (
                "tigre" in estab_desig
                or "san fernando" in estab_desig
                or "pilar" in estab_desig
            ):
                return False
        elif recibo_distrito_num == "055":
            if distrito_desig and not any(
                k in distrito_desig for k in ("tigre", "san fernando", "055")
            ):
                return False
            if "escobar" in estab_desig or "pilar" in estab_desig:
                return False
        elif recibo_distrito_num == "084":
            if distrito_desig and "pilar" not in distrito_desig:
                return False

        # Extraer números de escuela de la designación
        nums_desig = [
            int(n) for n in re.findall(r"\d+", f"{esc_num_desig} {estab_desig}")
        ]

        # En recibos DGCyE PBA "055 IS 0199", el número de escuela es el último (199)
        if len(recibo_nums) >= 2:
            school_num_recibo = recibo_nums[-1]
            if school_num_recibo in nums_desig:
                return True

        # Heurísticas para nombres de sedes conocidos (si omiten el número en el nombre)
        # EEST N°1 Tigre: sedes Tejedor / Marabotto
        if (
            "055 mt 0001" in recibo_str
            or ("055" in recibo_str and "0001" in recibo_str)
        ) and any(
            k in estab_desig
            for k in ("tejedor", "marabotto", "eest 1", "eest n°1", "eest n° 1")
        ):
            return True
        # EEST N°3 Tigre
        if (
            "055 mt 0003" in recibo_str
            or ("055" in recibo_str and "0003" in recibo_str)
        ) and any(k in estab_desig for k in ("eest 3", "eest n°3", "eest n° 3")):
            return True
        # EEST N°1 Escobar: sedes Independencia / Marin / Yrigoyen
        if (
            "116 mt 0001" in recibo_str
            or ("116" in recibo_str and "0001" in recibo_str)
        ) and any(
            k in estab_desig
            for k in ("independencia", "marin", "yrigoyen", "eest 1", "eest n°1")
        ):
            return True
        # ISFDyT N°199 Tigre
        if (
            "055 is 0199" in recibo_str
            or ("055" in recibo_str and "0199" in recibo_str)
        ) and any(k in estab_desig for k in ("199", "isfdyt", "isft")):
            return True

        # Substring fallback
        if esc_num_desig and (
            esc_num_desig in recibo_str or recibo_str in esc_num_desig
        ):
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
