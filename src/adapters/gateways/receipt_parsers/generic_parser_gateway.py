"""Gateway implementing ReceiptParserPort for standard Argentine salary receipts."""

import re

from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    ConceptoItem,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    TotalesConsolidados,
)
from src.domain.recibos.exceptions import ReceiptParsingError
from src.domain.recibos.ports import ExtractedPDF, ReceiptParserPort
from src.domain.recibos.services import TextNormalizerService
from src.domain.recibos.value_objects import (
    CUIT,
    DNI,
    ImporteMonetario,
    TipoConcepto,
    TipoRecibo,
)


class GenericParserGateway(ReceiptParserPort):
    """Fallback parser gateway for standard format salary receipts."""

    def can_handle(self, extracted_pdf: ExtractedPDF) -> bool:
        text = extracted_pdf.raw_full_text.upper()
        keywords = [
            "RECIBO",
            "SUELDO",
            "HABERES",
            "LIQUIDACION",
            "REMUNERACION",
            "NETO",
            "BRUTO",
            "LEGAJO",
        ]
        return any(k in text for k in keywords)

    def parse(self, extracted_pdf: ExtractedPDF) -> ReciboSueldo:
        text = extracted_pdf.raw_full_text
        lines = [
            line.strip()
            for page in extracted_pdf.pages
            for line in page.lines
            if line.strip()
        ]

        if not lines:
            raise ReceiptParsingError("Empty text extracted from PDF document.")

        empleador = self._extract_empleador(text, lines)
        agente = self._extract_agente(text, lines)
        conceptos, subtotal_hab, subtotal_desc = self._extract_conceptos(lines)

        cargo = CargoDetalle(
            secuencia="001",
            situacion_revista="MENSUALIZADO",
            cargo_real=self._extract_job_title(lines),
            periodo_liquidado=agente.mes_pago,
        )
        establecimiento = EstablecimientoDetalle(
            codigo="001",
            nombre=empleador.organismo_o_empresa,
        )

        liq = LiquidacionSecuencia(
            establecimiento=establecimiento,
            cargo=cargo,
            conceptos=conceptos,
            subtotal_haberes=subtotal_hab,
            subtotal_descuentos=subtotal_desc,
            liquido_calculado=round(subtotal_hab - subtotal_desc, 2),
        )

        totales = self._extract_totales(text, liq)

        return ReciboSueldo(
            tipo_recibo=TipoRecibo.GENERICO,
            empleador=empleador,
            agente=agente,
            resumen_liquidos=[],
            liquidaciones=[liq],
            totales=totales,
            metadata={
                "total_paginas": extracted_pdf.total_pages,
                "pdf_metadata": extracted_pdf.metadata,
            },
        )

    def _extract_empleador(self, text: str, lines: list[str]) -> Empleador:
        cuit_str = TextNormalizerService.extract_regex(
            r"\b(30|33|34)-?(\d{8})-?(\d)\b", text
        )
        cuit_vo = CUIT.from_string(cuit_str)

        first_lines = lines[:5]
        org_name = first_lines[0] if first_lines else "EMPRESA / EMPLEADOR"

        for l in first_lines:
            if "S.A." in l.upper() or "S.R.L." in l.upper() or "EMPRESA" in l.upper():
                org_name = l
                break

        return Empleador(
            organismo_o_empresa=TextNormalizerService.normalize(org_name),
            cuit=cuit_vo.value if cuit_vo else None,
        )

    def _extract_agente(self, text: str, lines: list[str]) -> Agente:
        raw_cuil = ""
        cuil_vo: CUIT | None = None
        for line in lines:
            if "CUIL" in line.upper() and (
                "EMPLEADO" in line.upper() or ":" in line or "-" in line
            ):
                cuil_match = TextNormalizerService.extract_regex(
                    r"\b(20|23|24|27)-?(\d{8})-?(\d)\b", line
                )
                if cuil_match:
                    raw_cuil = cuil_match
                    cuil_vo = CUIT.from_string(cuil_match)
                    break

        if not cuil_vo and not raw_cuil:
            cuil_match = TextNormalizerService.extract_regex(
                r"\b(20|23|24|27)-?(\d{8})-?(\d)\b", text
            )
            if cuil_match:
                raw_cuil = cuil_match
                cuil_vo = CUIT.from_string(cuil_match)

        dni_match = TextNormalizerService.extract_regex(
            r"\b(DNI|DOC|DOCUMENTO)?\s*(\d{7,8})\b", text, group=2
        )
        dni_vo = DNI.from_string(
            dni_match
            or (
                cuil_vo.unformatted[2:10]
                if cuil_vo
                else (
                    raw_cuil.replace("-", "")[2:10]
                    if len(raw_cuil.replace("-", "")) == 11
                    else "00000000"
                )
            )
        )

        per_match = TextNormalizerService.extract_regex(
            r"\b(\d{2}\s*/\s*\d{4})\b", text
        )

        name = "EMPLEADO"
        for line in lines[:15]:
            if (
                "EMPLEADO" in line.upper()
                or "APELLIDO" in line.upper()
                or "AGENTE" in line.upper()
            ):
                parts = line.split(":")
                if len(parts) > 1:
                    name = parts[1].strip()
                    break

        return Agente(
            nombre_completo=TextNormalizerService.normalize(name),
            tipo_documento="DNI",
            numero_documento=dni_vo.value if dni_vo else "",
            cuil=cuil_vo.value if cuil_vo else raw_cuil,
            mes_pago=per_match or "",
        )

    def _extract_job_title(self, lines: list[str]) -> str | None:
        for line in lines[:15]:
            if any(
                k in line.upper()
                for k in ["CATEGORIA:", "CARGO:", "PUESTO:", "SECCION:"]
            ):
                parts = line.split(":")
                if len(parts) > 1:
                    return TextNormalizerService.normalize(parts[1])
        return "EMPLEADO"

    def _extract_conceptos(
        self, lines: list[str]
    ) -> tuple[list[ConceptoItem], float, float]:
        conceptos: list[ConceptoItem] = []
        tot_hab = 0.0
        tot_desc = 0.0

        pattern_three_col = re.compile(
            r"^(\d{1,5})\s+([A-Za-zÁÉÍÓÚÑ0-9\.\s/%()#$,-]+?)\s+([\d\.,]+)(?:\s+([\d\.,]+))?$"
        )

        for line in lines:
            m = pattern_three_col.match(line)
            if m:
                code, desc, val1_str, val2_str = m.groups()
                desc_upper = desc.upper()
                if "TOTAL" in desc_upper or "SUBTOTAL" in desc_upper:
                    continue

                val1 = float(ImporteMonetario.from_raw(val1_str))
                val2 = float(ImporteMonetario.from_raw(val2_str)) if val2_str else None

                if val2 is not None and val2 > 0:
                    conceptos.append(
                        ConceptoItem(
                            codigo=code,
                            descripcion=TextNormalizerService.normalize(desc),
                            haberes=val1,
                            descuentos=None,
                            tipo=TipoConcepto.REMUNERATIVO,
                        )
                    )
                    conceptos.append(
                        ConceptoItem(
                            codigo=code,
                            descripcion=f"{TextNormalizerService.normalize(desc)} (RET)",
                            haberes=None,
                            descuentos=val2,
                            tipo=TipoConcepto.DESCUENTO,
                        )
                    )
                    tot_hab += val1
                    tot_desc += val2
                else:
                    is_desc = any(
                        k in desc_upper
                        for k in [
                            "JUBILACION",
                            "LEY 19032",
                            "OBRA SOCIAL",
                            "SINDICATO",
                            "RETENCION",
                            "DESCUENTO",
                            "GANANCIAS",
                        ]
                    )
                    is_no_rem = any(
                        k in desc_upper
                        for k in ["NO REM", "NO REMUNERATIVO", "VIATICOS", "REFRIGERIO"]
                    )

                    if is_desc:
                        tipo = TipoConcepto.DESCUENTO
                        tot_desc += val1
                        conceptos.append(
                            ConceptoItem(
                                codigo=code,
                                descripcion=TextNormalizerService.normalize(desc),
                                haberes=None,
                                descuentos=val1,
                                tipo=tipo,
                            )
                        )
                    elif is_no_rem:
                        tipo = TipoConcepto.NO_REMUNERATIVO
                        tot_hab += val1
                        conceptos.append(
                            ConceptoItem(
                                codigo=code,
                                descripcion=TextNormalizerService.normalize(desc),
                                haberes=val1,
                                descuentos=None,
                                tipo=tipo,
                            )
                        )
                    else:
                        tipo = TipoConcepto.REMUNERATIVO
                        tot_hab += val1
                        conceptos.append(
                            ConceptoItem(
                                codigo=code,
                                descripcion=TextNormalizerService.normalize(desc),
                                haberes=val1,
                                descuentos=None,
                                tipo=tipo,
                            )
                        )

        return conceptos, round(tot_hab, 2), round(tot_desc, 2)

    def _extract_totales(
        self, text: str, liq: LiquidacionSecuencia
    ) -> TotalesConsolidados:
        neto_str = TextNormalizerService.extract_regex(
            r"(?:NETO|LIQUIDO|TOTAL A COBRAR|NETO A COBRAR)\s*[:\$]?\s*([\d\.,]+)", text
        )
        bruto_str = TextNormalizerService.extract_regex(
            r"(?:TOTAL BRUTO|TOTAL HABERES|BRUTO)\s*[:\$]?\s*([\d\.,]+)", text
        )
        desc_str = TextNormalizerService.extract_regex(
            r"(?:TOTAL RETENCIONES|TOTAL DESCUENTOS)\s*[:\$]?\s*([\d\.,]+)", text
        )

        total_hab = (
            float(ImporteMonetario.from_raw(bruto_str))
            if bruto_str
            else liq.subtotal_haberes
        )
        total_desc = (
            float(ImporteMonetario.from_raw(desc_str))
            if desc_str
            else liq.subtotal_descuentos
        )
        total_liq = (
            float(ImporteMonetario.from_raw(neto_str))
            if neto_str
            else liq.liquido_calculado
        )

        rem_sum = sum(
            c.haberes or 0.0
            for c in liq.conceptos
            if c.tipo == TipoConcepto.REMUNERATIVO
        )
        no_rem_sum = sum(
            c.haberes or 0.0
            for c in liq.conceptos
            if c.tipo == TipoConcepto.NO_REMUNERATIVO
        )

        return TotalesConsolidados(
            total_haberes_remunerativos=round(rem_sum if rem_sum > 0 else total_hab, 2),
            total_haberes_no_remunerativos=round(no_rem_sum, 2),
            total_haberes=round(total_hab, 2),
            total_descuentos=round(total_desc, 2),
            total_liquido=round(total_liq, 2),
        )
