"""Gateway implementing ReceiptParserPort for DGCyE PBA salary receipts."""

import re
from typing import ClassVar

from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    ConceptoItem,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
)
from src.domain.recibos.exceptions import ReceiptParsingError
from src.domain.recibos.ports import ExtractedPDF, ReceiptParserPort
from src.domain.recibos.services import TextNormalizerService, TotalesCalculatorService
from src.domain.recibos.value_objects import (
    CUIT,
    DNI,
    ImporteMonetario,
    TipoConcepto,
    TipoRecibo,
)


class DGCyEParserGateway(ReceiptParserPort):
    """Gateway for parsing Buenos Aires DGCyE multi-sequence salary receipts."""

    FOOTER_NOISE_PATTERNS: ClassVar[list[str]] = [
        r"Incluye todos los pagos realizados.*Pag\.\d+",
        r"Se recuerda la implementación de Domicilio",
        r"La Línea 144 brinda atención",
        r"También podés comunicarte a través",
        r"o por correo a atencion144pba",
        r"Para acceder a la comunidad educativa",
        r"usuario tu nueva cuenta abc",
        r"misma que utilizabas hasta ahora",
        r"DEPARTAMENTO IMPUESTOS Y TRIBUTOS",
        r"En caso de percibir haberes retroactivos",
        r"Ganancias, usted deberá presentar",
        r"de percibir dichos haberes retroactivos",
        r"De la misma manera, puede solicitar",
        r"su apellido, nombre y DNI",
    ]

    def can_handle(self, extracted_pdf: ExtractedPDF) -> bool:
        text = extracted_pdf.raw_full_text.upper()
        return (
            "DIRECCION GENERAL DE CULTURA Y EDUCACION" in text
            or "DGCYE" in text
            or (
                "PROVINCIA DE BUENOS AIRES" in text
                and "CARACTERISTICAS DEL ESTABLECIMIENTO" in text
            )
        )

    def parse(self, extracted_pdf: ExtractedPDF) -> ReciboSueldo:
        if not self.can_handle(extracted_pdf):
            raise ReceiptParsingError(
                "Document is not a recognized DGCyE PBA salary receipt."
            )

        cleaned_lines = self._clean_lines(extracted_pdf)

        empleador = self._parse_empleador(cleaned_lines)
        agente = self._parse_agente(cleaned_lines)
        resumen_liquidos = self._parse_resumen_liquidos(cleaned_lines)
        liquidaciones = self._parse_liquidaciones(cleaned_lines)

        totales = TotalesCalculatorService.calculate(liquidaciones, resumen_liquidos)

        return ReciboSueldo(
            tipo_recibo=TipoRecibo.DGCYE_PBA,
            empleador=empleador,
            agente=agente,
            resumen_liquidos=resumen_liquidos,
            liquidaciones=liquidaciones,
            totales=totales,
            metadata={
                "total_paginas": extracted_pdf.total_pages,
                "total_secuencias_liquidadas": len(liquidaciones),
                "total_items_resumen": len(resumen_liquidos),
                "pdf_metadata": extracted_pdf.metadata,
            },
        )

    def _clean_lines(self, extracted_pdf: ExtractedPDF) -> list[str]:
        lines: list[str] = []
        for page in extracted_pdf.pages:
            for raw_line in page.lines:
                line_str = raw_line.strip()
                if not line_str:
                    continue
                if any(
                    re.search(pat, line_str, re.IGNORECASE)
                    for pat in self.FOOTER_NOISE_PATTERNS
                ):
                    continue
                lines.append(line_str)
        return lines

    def _parse_empleador(self, lines: list[str]) -> Empleador:
        full_text = "\n".join(lines[:15])
        cuit_str = TextNormalizerService.extract_regex(
            r"CUIT\s+N°?\s*([\d-]+)", full_text, group=1
        )
        cuit_vo = (
            CUIT.from_string(cuit_str)
            if cuit_str
            else CUIT.from_string("30-62739371-3")
        )

        return Empleador(
            organismo_o_empresa="PROVINCIA DE BUENOS AIRES - DIRECCION GENERAL DE CULTURA Y EDUCACION",
            dependencia="DIRECCION GENERAL DE ADMINISTRACION",
            cuit=cuit_vo.value if cuit_vo else "30-62739371-3",
        )

    def _parse_agente(self, lines: list[str]) -> Agente:
        agent_idx = -1
        for idx, line in enumerate(lines[:12]):
            if "APELLIDO Y NOMBRE" in line and (
                "CUIT/CUIL" in line or "TIPO DOC" in line
            ):
                agent_idx = idx + 1
                break

        if agent_idx != -1 and agent_idx < len(lines):
            target_line = lines[agent_idx]
            m = re.match(
                r"^(.*?)\s+(DNI|LC|LE|CI|PAS)\s+(\d+)\s+([MFX])\s+([\d-]+)\s+(\d{2}\s*/\s*\d{4})$",
                target_line,
            )
            if m:
                raw_name, doc_type, doc_num, sex, cuil_str, mes_pago = m.groups()
                dni_vo = DNI.from_string(doc_num, doc_type=doc_type)
                cuit_vo = CUIT.from_string(cuil_str)
                return Agente(
                    nombre_completo=TextNormalizerService.normalize(raw_name),
                    tipo_documento=dni_vo.doc_type if dni_vo else doc_type,
                    numero_documento=dni_vo.value if dni_vo else doc_num,
                    sexo=sex,
                    cuil=cuit_vo.value if cuit_vo else cuil_str,
                    mes_pago=mes_pago,
                )

        full_text = "\n".join(lines[:20])
        cuil_match = TextNormalizerService.extract_regex(
            r"\b(20|23|24|27|30|33|34)-?(\d{8})-?(\d)\b", full_text, group=0
        )
        cuit_vo = CUIT.from_string(cuil_match)
        dni_vo = DNI.from_string(cuit_vo.unformatted[2:10] if cuit_vo else "00000000")

        return Agente(
            nombre_completo=TextNormalizerService.normalize(
                lines[5] if len(lines) > 5 else "AGENTE DGCYE"
            ),
            tipo_documento="DNI",
            numero_documento=dni_vo.value if dni_vo else "",
            sexo="M",
            cuil=cuit_vo.value if cuit_vo else "",
            mes_pago="",
        )

    def _parse_resumen_liquidos(self, lines: list[str]) -> list[ResumenLiquidoItem]:
        items: list[ResumenLiquidoItem] = []
        in_liquidos = False

        for line in lines:
            if line.strip() == "LIQUIDOS":
                in_liquidos = True
                continue
            if in_liquidos and (
                line.startswith("TOTAL ")
                or "CARACTERISTICAS DEL ESTABLECIMIENTO" in line
            ):
                in_liquidos = False
                break
            if in_liquidos:
                if "ESTABLECIMIENTO SEC." in line:
                    continue
                m = re.match(
                    r"^(\d+\s+[A-Z]+\s+\d+)\s+(\d{3})\s+(\d{2}\s*/\s*\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s*-\s*(.*?)\s+([\d\.,]+)$",
                    line,
                )
                if m:
                    estab_code, sec, per, f_pago, op_code, op_desc, monto_str = (
                        m.groups()
                    )
                    items.append(
                        ResumenLiquidoItem(
                            establecimiento_codigo=estab_code,
                            secuencia=sec,
                            periodo_liquidado=per,
                            fecha_pago=f_pago,
                            orden_pago_codigo=op_code,
                            orden_pago_descripcion=TextNormalizerService.normalize(
                                op_desc
                            ),
                            liquido_pesos=float(ImporteMonetario.from_raw(monto_str)),
                        )
                    )

        return items

    def _parse_liquidaciones(self, lines: list[str]) -> list[LiquidacionSecuencia]:
        start_idx = 0
        for idx, line in enumerate(lines):
            if line.startswith("TOTAL ") and re.search(r"TOTAL\s+[\d\.]+", line):
                start_idx = idx + 1
                break

        detail_lines = lines[start_idx:] if start_idx > 0 else lines

        liquidaciones: list[LiquidacionSecuencia] = []
        current_estab: EstablecimientoDetalle | None = None
        current_cargo: CargoDetalle | None = None
        current_conceptos: list[ConceptoItem] = []
        current_orden_pago: str | None = None

        concept_regex = re.compile(r"^(\d{4})\s+(.+?)\s+([\d\.,]+)$")

        i = 0
        while i < len(detail_lines):
            line = detail_lines[i]

            # 1. Establishment header
            if "CARACTERISTICAS DEL ESTABLECIMIENTO" in line:
                distrito = line.split("CARACTERISTICAS DEL ESTABLECIMIENTO")[0].strip()
                i += 1
                if i < len(detail_lines) and "CATEGORIA" in detail_lines[i]:
                    i += 1
                if i < len(detail_lines):
                    val_line = detail_lines[i]
                    m_est = re.match(
                        r"^(\S+)\s+(\d+)\s+(\d+)\s+([SN])\s+([SN])\s+(\d+)\s*(.*)$",
                        val_line,
                    )
                    if m_est:
                        cat, desf, sec, carc, d_esc, turn, nom = m_est.groups()
                        current_estab = EstablecimientoDetalle(
                            codigo=cat,
                            distrito=distrito,
                            categoria=cat,
                            desfavorabilidad=int(desf),
                            secciones=int(sec),
                            es_carcel=carc == "S",
                            doble_escolaridad=d_esc == "S",
                            turnos=int(turn),
                            nombre=TextNormalizerService.normalize(nom),
                        )
                i += 1
                continue

            # 2. Orden de pago line
            if line.startswith("ORDEN DE PAGO:"):
                current_orden_pago = line.replace("ORDEN DE PAGO:", "").strip()
                i += 1
                continue

            # 3. Sequence header
            if "SECUENCIA REVISTA CARGO REAL" in line:
                i += 1
                if i < len(detail_lines) and detail_lines[i].startswith(
                    "ORDEN DE PAGO:"
                ):
                    current_orden_pago = (
                        detail_lines[i].replace("ORDEN DE PAGO:", "").strip()
                    )
                    i += 1
                if i < len(detail_lines):
                    seq_line = detail_lines[i]
                    m_seq = re.match(
                        r"^(\d{3})\s+(\S+)\s+(\S+)\s+([\d\.]+)\s+(\S+)$",
                        seq_line,
                    )
                    if m_seq:
                        sec, rev, crg, c_hor, per_liq = m_seq.groups()
                        current_cargo = CargoDetalle(
                            secuencia=sec,
                            situacion_revista=rev,
                            cargo_real=crg,
                            carga_horaria=float(c_hor),
                            periodo_liquidado=per_liq,
                            orden_pago=current_orden_pago,
                        )
                        current_conceptos = []
                i += 1
                continue

            # 4. Skip concepts column header
            if "COD HABERES Haberes Descuentos" in line:
                i += 1
                continue

            # 5. Sequence trailer
            if "ANTIGUEDAD EN AÑOS:" in line:
                m_trail = re.search(
                    r"ANTIGUEDAD EN AÑOS:\s*(\d+).*?INASISTENCIAS:\s*([\d\.]+)",
                    line,
                )
                if current_cargo and m_trail:
                    current_cargo.antiguedad_anios = int(m_trail.group(1))
                    current_cargo.inasistencias = float(m_trail.group(2))

                if current_estab and current_cargo:
                    sub_haberes = sum(c.haberes or 0.0 for c in current_conceptos)
                    sub_descuentos = sum(c.descuentos or 0.0 for c in current_conceptos)
                    liq_calc = round(sub_haberes - sub_descuentos, 2)

                    liquidaciones.append(
                        LiquidacionSecuencia(
                            establecimiento=current_estab.model_copy(),
                            cargo=current_cargo.model_copy(),
                            conceptos=current_conceptos,
                            subtotal_haberes=round(sub_haberes, 2),
                            subtotal_descuentos=round(sub_descuentos, 2),
                            liquido_calculado=liq_calc,
                        )
                    )
                    current_cargo = None
                    current_conceptos = []
                i += 1
                continue

            # 6. Concept item
            m_c = concept_regex.match(line)
            if m_c and current_cargo is not None:
                c_code, c_desc, c_val_str = m_c.groups()
                val = float(ImporteMonetario.from_raw(c_val_str))
                tipo, haberes, descuentos = self._classify_concept(c_code, c_desc, val)

                current_conceptos.append(
                    ConceptoItem(
                        codigo=c_code,
                        descripcion=TextNormalizerService.normalize(c_desc),
                        haberes=haberes,
                        descuentos=descuentos,
                        tipo=tipo,
                    )
                )
                i += 1
                continue

            i += 1

        return liquidaciones

    def _classify_concept(
        self, code: str, desc: str, value: float
    ) -> tuple[TipoConcepto, float | None, float | None]:
        desc_upper = desc.upper()
        if code.startswith("1") or any(
            k in desc_upper
            for k in ["RETENCION", "I.P.S", "I.O.M.A", "SUTEBA", "DESCUENTO"]
        ):
            return TipoConcepto.DESCUENTO, None, value

        if code.startswith("2") or "NO REM" in desc_upper or "FONID" in desc_upper:
            return TipoConcepto.NO_REMUNERATIVO, value, None

        return TipoConcepto.REMUNERATIVO, value, None
