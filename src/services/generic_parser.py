"""Generic parser for standard Argentine private/public sector salary receipts."""

import re

from src.schemas.recibo import (
    AgenteSchema,
    CargoDetalle,
    ConceptoItem,
    EmpleadorSchema,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldoResponse,
    TipoConcepto,
    TipoRecibo,
    TotalesConsolidados,
)
from src.services.base_parser import BaseReceiptParser, ReceiptParsingError
from src.services.pdf_extractor import ExtractedPDF
from src.utils.text_helpers import (
    extract_cuil,
    extract_dni,
    normalize_text,
    parse_currency_amount,
)


class GenericReceiptParser(BaseReceiptParser):
    """Fallback parser for standard Argentine salary receipts (Ley de Contrato de Trabajo)."""

    def can_handle(self, extracted_pdf: ExtractedPDF) -> bool:
        """Can handle any document that has salary receipt keywords or as fallback."""
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

    def parse(self, extracted_pdf: ExtractedPDF) -> ReciboSueldoResponse:
        """Parse standard salary receipt layout."""
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

        # Build single sequence for standard receipt
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

        return ReciboSueldoResponse(
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

    def _extract_empleador(self, text: str, lines: list[str]) -> EmpleadorSchema:
        """Extract company/employer name and CUIT."""
        cuit = extract_cuil(text)
        first_lines = lines[:5]
        org_name = first_lines[0] if first_lines else "EMPRESA / EMPLEADOR"

        # Search for company name indicator if available
        for l in first_lines:
            if "S.A." in l.upper() or "S.R.L." in l.upper() or "EMPRESA" in l.upper():
                org_name = l
                break

        return EmpleadorSchema(
            organismo_o_empresa=normalize_text(org_name),
            cuit=cuit,
        )

    def _extract_agente(self, text: str, lines: list[str]) -> AgenteSchema:
        """Extract employee personal details."""
        cuil = ""
        # Search specifically for CUIL on employee line or labeled line
        for line in lines:
            if "CUIL" in line.upper() and (
                "EMPLEADO" in line.upper() or ":" in line or "-" in line
            ):
                extracted = extract_cuil(line)
                if extracted:
                    cuil = extracted
                    break

        # If not found specifically, look for personal prefixes (20, 27, 23, 24)
        if not cuil:
            m_pers = re.search(r"\b(20|23|24|27)-?(\d{8})-?(\d)\b", text)
            if m_pers:
                cuil = f"{m_pers.group(1)}-{m_pers.group(2)}-{m_pers.group(3)}"
            else:
                cuil = extract_cuil(text) or ""

        dni = extract_dni(text) or (
            cuil.replace("-", "")[2:10] if len(cuil.replace("-", "")) == 11 else ""
        )

        # Period search (e.g., '07/2026' or 'JULIO 2026')
        per_m = re.search(r"\b(\d{2}\s*/\s*\d{4})\b", text)
        period = per_m.group(1) if per_m else ""

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

        return AgenteSchema(
            nombre_completo=normalize_text(name),
            tipo_documento="DNI",
            numero_documento=dni,
            cuil=cuil,
            mes_pago=period,
        )

    def _extract_job_title(self, lines: list[str]) -> str | None:
        """Extract job title or category if present."""
        for line in lines[:15]:
            if any(
                k in line.upper()
                for k in ["CATEGORIA:", "CARGO:", "PUESTO:", "SECCION:"]
            ):
                parts = line.split(":")
                if len(parts) > 1:
                    return normalize_text(parts[1])
        return "EMPLEADO"

    def _extract_conceptos(
        self, lines: list[str]
    ) -> tuple[list[ConceptoItem], float, float]:
        """Extract concept lines using tabular or regex pattern matching."""
        conceptos: list[ConceptoItem] = []
        tot_hab = 0.0
        tot_desc = 0.0

        # Pattern: [CODE] DESCRIPTION [AMOUNT] or [CODE] DESCRIPTION [HABERES] [DESCUENTOS]
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

                val1 = parse_currency_amount(val1_str)
                val2 = parse_currency_amount(val2_str) if val2_str else None

                if val2 is not None and val2 > 0:
                    # Column 1 is haberes, column 2 is descuentos
                    conceptos.append(
                        ConceptoItem(
                            codigo=code,
                            descripcion=normalize_text(desc),
                            haberes=val1,
                            descuentos=None,
                            tipo=TipoConcepto.REMUNERATIVO,
                        )
                    )
                    conceptos.append(
                        ConceptoItem(
                            codigo=code,
                            descripcion=f"{normalize_text(desc)} (RET)",
                            haberes=None,
                            descuentos=val2,
                            tipo=TipoConcepto.DESCUENTO,
                        )
                    )
                    tot_hab += val1
                    tot_desc += val2
                else:
                    # Single amount: determine if deduction or earning
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
                                descripcion=normalize_text(desc),
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
                                descripcion=normalize_text(desc),
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
                                descripcion=normalize_text(desc),
                                haberes=val1,
                                descuentos=None,
                                tipo=tipo,
                            )
                        )

        return conceptos, round(tot_hab, 2), round(tot_desc, 2)

    def _extract_totales(
        self, text: str, liq: LiquidacionSecuencia
    ) -> TotalesConsolidados:
        """Extract explicit totals if mentioned in text or compute from sequence."""
        neto_m = re.search(
            r"(?:NETO|LIQUIDO|TOTAL A COBRAR|NETO A COBRAR)\s*[:\$]?\s*([\d\.,]+)",
            text,
            re.IGNORECASE,
        )
        bruto_m = re.search(
            r"(?:TOTAL BRUTO|TOTAL HABERES|BRUTO)\s*[:\$]?\s*([\d\.,]+)",
            text,
            re.IGNORECASE,
        )
        desc_m = re.search(
            r"(?:TOTAL RETENCIONES|TOTAL DESCUENTOS)\s*[:\$]?\s*([\d\.,]+)",
            text,
            re.IGNORECASE,
        )

        total_hab = (
            parse_currency_amount(bruto_m.group(1)) if bruto_m else liq.subtotal_haberes
        )
        total_desc = (
            parse_currency_amount(desc_m.group(1))
            if desc_m
            else liq.subtotal_descuentos
        )
        total_liq = (
            parse_currency_amount(neto_m.group(1)) if neto_m else liq.liquido_calculado
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
