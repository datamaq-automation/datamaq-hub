from collections.abc import Sequence
import io
from pathlib import Path
import re
import pdfplumber

from src.domain.empleo.entities import (
    ContactoPerfil,
    EducacionPerfil,
    ExperienciaPerfil,
    PerfilCandidatoDetallado,
)
from src.domain.empleo.exceptions import LinkedInPDFParsingError
from src.domain.empleo.ports import LinkedInProfileParserPort

PALABRAS_CLAVE_INDUSTRIALES: tuple[str, ...] = (
    "automatización",
    "mantenimiento",
    "electrotecnia",
    "oee",
    "scada",
    "plc",
    "vfd",
    "variador",
    "media tensión",
    "alta tensión",
    "ccm",
    "cbm",
    "loto",
    "inteligencia artificial",
    "robótica",
    "python",
    "iot",
    "industria 4.0",
    "transformación digital",
    "confiabilidad",
    "instrumentación",
    "control de calidad",
    "normas",
    "seguridad",
    "hidráulica",
    "neumática",
    "instalaciones eléctricas",
    "máquinas eléctricas",
)


class PdfplumberLinkedInParserGateway(LinkedInProfileParserPort):
    """Implementación del parser de PDF de perfiles de LinkedIn estándar mediante pdfplumber."""

    def parsear_archivo(self, ruta_archivo: Path) -> PerfilCandidatoDetallado:
        if not ruta_archivo.exists():
            raise LinkedInPDFParsingError(
                f"El archivo PDF de LinkedIn no existe en la ruta: {ruta_archivo}"
            )
        try:
            contenido_pdf = ruta_archivo.read_bytes()
        except Exception as exc:
            raise LinkedInPDFParsingError(
                f"Error al leer archivo PDF {ruta_archivo}: {exc}"
            ) from exc
        return self.parsear_pdf(contenido_pdf)

    def parsear_pdf(self, contenido_pdf: bytes) -> PerfilCandidatoDetallado:
        if not contenido_pdf:
            raise LinkedInPDFParsingError("El contenido del archivo PDF está vacío")

        try:
            with pdfplumber.open(io.BytesIO(contenido_pdf)) as pdf:
                if not pdf.pages:
                    raise LinkedInPDFParsingError("El PDF no contiene páginas legibles")

                # Extraer texto de la primera página con crop de 2 columnas (layout estándar LinkedIn)
                p0 = pdf.pages[0]
                split_x = 220.0
                left_crop = p0.crop((0, 0, split_x, p0.height))
                right_crop = p0.crop((split_x, 0, p0.width, p0.height))

                left_text = left_crop.extract_text() or ""
                right_text = right_crop.extract_text() or ""

                # Extraer texto de las páginas subsiguientes
                other_pages_text: list[str] = []
                for p in pdf.pages[1:]:
                    raw_p = p.extract_text() or ""
                    clean_p = re.sub(r"Page \d+ of \d+", "", raw_p)
                    other_pages_text.append(clean_p)

                full_right_text = right_text + "\n" + "\n".join(other_pages_text)
                full_right_text = re.sub(r"Page \d+ of \d+", "", full_right_text)
        except Exception as exc:
            if isinstance(exc, LinkedInPDFParsingError):
                raise
            raise LinkedInPDFParsingError(
                f"Fallo al procesar estructura PDF de LinkedIn: {exc}"
            ) from exc

        contacto, aptitudes = self._extraer_columna_izquierda(left_text)
        titular, extracto, experiencias, educacion = self._extraer_columna_derecha(
            full_right_text
        )

        nombre_detectado = self._extraer_nombre(full_right_text) or contacto.nombre
        contacto_completo = ContactoPerfil(
            nombre=nombre_detectado,
            email=contacto.email,
            telefono=contacto.telefono,
            linkedin_url=contacto.linkedin_url,
            ubicacion=contacto.ubicacion or "Argentina",
        )

        keywords_detectadas = self._detectar_keywords(
            extracto=extracto,
            aptitudes=aptitudes,
            experiencias=experiencias,
        )
        anios_estimados = self._estimar_anios_experiencia(experiencias)

        return PerfilCandidatoDetallado(
            contacto=contacto_completo,
            titular=titular,
            extracto=extracto,
            aptitudes_principales=tuple(aptitudes),
            experiencias=tuple(experiencias),
            educacion=tuple(educacion),
            palabras_clave_detectadas=tuple(keywords_detectadas),
            anios_experiencia_estimados=anios_estimados,
        )

    def _extraer_columna_izquierda(
        self, left_text: str
    ) -> tuple[ContactoPerfil, list[str]]:
        """Parsea la columna izquierda (contacto y aptitudes principales)."""
        phone = ""
        email_parts: list[str] = []
        linkedin_parts: list[str] = []
        aptitudes: list[str] = []

        in_skills = False
        lines = [line.strip() for line in left_text.splitlines() if line.strip()]

        for line in lines:
            if "Aptitudes principales" in line:
                in_skills = True
                continue

            if in_skills:
                if aptitudes and (
                    aptitudes[-1].endswith(" de") or aptitudes[-1].endswith(" en")
                ):
                    aptitudes[-1] = f"{aptitudes[-1]} {line}"
                else:
                    aptitudes.append(line)
            else:
                if "@" in line or (email_parts and line.startswith(".")):
                    email_parts.append(line)
                elif "linkedin.com" in line or (linkedin_parts and "LinkedIn" in line):
                    linkedin_parts.append(line)
                elif re.search(r"\d{7,}", line):
                    phone = line

        email = "".join(email_parts).replace(" ", "")
        raw_linkedin = " ".join(linkedin_parts)
        linkedin_url = re.sub(r"\(LinkedIn\)", "", raw_linkedin).strip().replace(" ", "")
        if linkedin_url and not linkedin_url.startswith("http"):
            linkedin_url = f"https://{linkedin_url}"

        contacto = ContactoPerfil(
            nombre="",
            email=email,
            telefono=phone,
            linkedin_url=linkedin_url,
        )
        return contacto, aptitudes

    def _extraer_nombre(self, full_right_text: str) -> str:
        lines = [l.strip() for l in full_right_text.splitlines() if l.strip()]
        return lines[0] if lines else ""

    def _extraer_columna_derecha(
        self, full_text: str
    ) -> tuple[str, str, list[ExperienciaPerfil], list[EducacionPerfil]]:
        """Extrae titular, extracto, experiencias y educación de la columna principal."""
        partes_exp = full_text.split("Experiencia")
        encabezado_y_extracto = partes_exp[0]

        resto = partes_exp[1] if len(partes_exp) > 1 else ""
        partes_edu = resto.split("Educación")
        seccion_experiencia = partes_edu[0] if partes_edu else ""
        seccion_educacion = partes_edu[1] if len(partes_edu) > 1 else ""

        extracto = ""
        if "Extracto" in encabezado_y_extracto:
            parts = encabezado_y_extracto.split("Extracto")
            encabezado = parts[0]
            extracto = " ".join(parts[1].split())
        else:
            encabezado = encabezado_y_extracto

        encabezado_lines = [l.strip() for l in encabezado.splitlines() if l.strip()]
        titular_lines: list[str] = []
        for l in encabezado_lines[1:]:
            if l.lower() in ("argentina", "buenos aires, argentina"):
                continue
            titular_lines.append(l)
        titular = " ".join(titular_lines)

        experiencias = self._parsear_bloques_experiencia(seccion_experiencia)
        educacion = self._parsear_bloques_educacion(seccion_educacion)

        return titular, extracto, experiencias, educacion

    def _parsear_bloques_experiencia(
        self, texto_exp: str
    ) -> list[ExperienciaPerfil]:
        """Parsea la lista de cargos, empresas y periodos."""
        experiencias: list[ExperienciaPerfil] = []
        if not texto_exp.strip():
            return experiencias

        lines = [l.strip() for l in texto_exp.splitlines() if l.strip()]
        fecha_re = re.compile(
            r"([a-zñ]+ de \d{4}|\d{4})\s*-\s*(Present|actualidad|presente|[a-zñ]+ de \d{4}|\d{4})",
            re.IGNORECASE,
        )
        duracion_empresa_re = re.compile(
            r"^\d+\s+años?(\s+\d+\s+meses?)?$", re.IGNORECASE
        )

        current_empresa = ""
        i = 0
        while i < len(lines):
            line = lines[i]

            # 1. Empresa seguida de duración total (ej. 'Madygraf \n 12 años 2 meses')
            if i + 1 < len(lines) and duracion_empresa_re.match(lines[i + 1]):
                current_empresa = line
                i += 2
                continue

            # 2. Puesto seguido de fecha (mantiene current_empresa si existe)
            if i + 1 < len(lines) and fecha_re.search(lines[i + 1]):
                puesto = line
                fecha_line = lines[i + 1]
                i += 2
                ubicacion = ""
                if i < len(lines) and any(
                    kw in lines[i]
                    for kw in ["Argentina", "Buenos Aires", "Neuquén"]
                ):
                    ubicacion = lines[i]
                    i += 1

                desc_parts: list[str] = []
                while i < len(lines):
                    if i + 1 < len(lines) and (
                        fecha_re.search(lines[i + 1])
                        or duracion_empresa_re.match(lines[i + 1])
                    ):
                        break
                    if (
                        i + 2 < len(lines)
                        and fecha_re.search(lines[i + 2])
                        and lines[i + 1]
                        and lines[i + 1][0].isupper()
                        and lines[i]
                        and lines[i][0].isupper()
                        and not lines[i].endswith((".", ":", ";", ","))
                    ):
                        break

                    desc_parts.append(lines[i].lstrip(">-• "))
                    i += 1

                duracion = ""
                if "(" in fecha_line and ")" in fecha_line:
                    dur_match = re.search(r"\((.*?)\)", fecha_line)
                    if dur_match:
                        duracion = dur_match.group(1)

                es_actual = (
                    "present" in fecha_line.lower()
                    or "actualidad" in fecha_line.lower()
                    or "presente" in fecha_line.lower()
                )

                empresa_final = current_empresa
                puesto_final = puesto
                if "–" in puesto:
                    parts = puesto.split("–")
                    puesto_final = parts[0].strip()
                    if not empresa_final:
                        empresa_final = parts[1].strip()
                elif "-" in puesto:
                    parts = puesto.split("-")
                    puesto_final = parts[0].strip()

                experiencias.append(
                    ExperienciaPerfil(
                        empresa=empresa_final or "Empresa",
                        puesto=puesto_final or "Posición",
                        periodo=fecha_line,
                        duracion=duracion,
                        ubicacion=ubicacion,
                        descripcion=" ".join(desc_parts).strip(),
                        es_actual=es_actual,
                    )
                )
                continue

            # 3. Empresa nueva sin duración previa
            if (
                i + 2 < len(lines)
                and fecha_re.search(lines[i + 2])
                and lines[i + 1]
                and lines[i + 1][0].isupper()
                and line
                and line[0].isupper()
                and not line.endswith((".", ":", ";", ","))
            ):
                current_empresa = line
                i += 1
                continue

            i += 1

        return experiencias

    def _parsear_bloques_educacion(self, texto_edu: str) -> list[EducacionPerfil]:
        """Parsea la lista de títulos y universidades."""
        educaciones: list[EducacionPerfil] = []
        if not texto_edu.strip():
            return educaciones

        lines = [l.strip() for l in texto_edu.splitlines() if l.strip()]
        i = 0
        while i < len(lines):
            institucion = lines[i]
            titulo = ""
            periodo = ""
            if i + 1 < len(lines):
                detalle = lines[i + 1]
                if "·" in detalle:
                    parts = detalle.split("·")
                    titulo = parts[0].strip()
                    periodo = parts[1].strip().strip("()")
                else:
                    titulo = detalle
                i += 1

            educaciones.append(
                EducacionPerfil(
                    institucion=institucion,
                    titulo=titulo,
                    periodo=periodo,
                )
            )
            i += 1

        return educaciones

    def _detectar_keywords(
        self,
        extracto: str,
        aptitudes: Sequence[str],
        experiencias: Sequence[ExperienciaPerfil],
    ) -> list[str]:
        """Analiza el contenido consolidado y detecta tecnologías y competencias industriales clave."""
        bloque_total = (
            extracto
            + " "
            + " ".join(aptitudes)
            + " "
            + " ".join(f"{e.puesto} {e.descripcion}" for e in experiencias)
        ).lower()

        encontradas: list[str] = []
        for kw in PALABRAS_CLAVE_INDUSTRIALES:
            if kw in bloque_total and kw not in encontradas:
                encontradas.append(kw)
        return encontradas

    def _estimar_anios_experiencia(
        self, experiencias: Sequence[ExperienciaPerfil]
    ) -> float:
        """Estima la cantidad total de años de experiencia a partir de los periodos."""
        anios: list[int] = []
        for exp in experiencias:
            matches = re.findall(r"\b(19\d{2}|20\d{2})\b", exp.periodo)
            for m in matches:
                anios.append(int(m))

        if not anios:
            return 0.0

        min_anio = min(anios)
        max_anio = max(anios)
        tiene_actual = any(e.es_actual for e in experiencias)
        if tiene_actual:
            max_anio = max(max_anio, 2026)

        return float(max(0, max_anio - min_anio))
