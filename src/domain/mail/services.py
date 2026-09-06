"""Domain services for decoding and sanitizing email headers and content."""

import re
from email.header import decode_header, make_header
from email.utils import parseaddr

from src.domain.mail.entities import (
    AnalisisEmail,
    EmailDetail,
    EntidadesDetectadas,
)
from src.domain.mail.value_objects import CategoriaEmail, NivelPrioridad


class MailDecoderService:
    """Pure domain service for parsing and sanitizing MIME headers and text bodies."""

    @staticmethod
    def decode_header_str(raw_header: str | None) -> str:
        """Decodes RFC 2047 encoded email headers to clean Unicode string."""
        if not raw_header:
            return ""
        try:
            return str(make_header(decode_header(raw_header))).strip()
        except (LookupError, ValueError, TypeError, UnicodeDecodeError):
            return str(raw_header).strip()

    @staticmethod
    def clean_email_list(raw_header: str | None) -> list[str]:
        """Parses a comma-separated email header into clean email list."""
        if not raw_header:
            return []
        decoded = MailDecoderService.decode_header_str(raw_header)
        parts = [p.strip() for p in decoded.split(",") if p.strip()]
        return parts

    @staticmethod
    def strip_html(text: str) -> str:
        """Reduce un cuerpo HTML a texto plano legible."""
        sin_bloques = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE
        )
        sin_tags = re.sub(r"<[^>]+>", " ", sin_bloques)
        for entidad, caracter in (
            ("&nbsp;", " "),
            ("&amp;", "&"),
            ("&lt;", "<"),
            ("&gt;", ">"),
            ("&quot;", '"'),
            ("&#39;", "'"),
        ):
            sin_tags = sin_tags.replace(entidad, caracter)
        return sin_tags

    @staticmethod
    def build_snippet(
        raw_body: bytes,
        content_type: str = "text/plain",
        transfer_encoding: str = "",
        max_chars: int = 200,
    ) -> str:
        """Construye una vista previa de una porción inicial del cuerpo de un correo.

        Pensado para listados, donde solo se descargan los primeros bytes del cuerpo.
        Un base64 cortado a la mitad no se puede decodificar de forma confiable, así que
        en ese caso se devuelve cadena vacía en lugar de basura: es preferible no mostrar
        nada a mostrar algo incorrecto.
        """
        if not raw_body:
            return ""

        codificacion = transfer_encoding.strip().lower()
        if codificacion == "base64":
            return ""

        texto = raw_body.decode("utf-8", errors="replace")

        if codificacion == "quoted-printable":
            import quopri

            # El último escape puede venir cortado por el fetch parcial: se descarta.
            recortado = re.sub(r"=[0-9A-Fa-f]?$", "", texto)
            texto = quopri.decodestring(
                recortado.encode("utf-8", errors="replace")
            ).decode("utf-8", errors="replace")

        if "html" in content_type.lower():
            texto = MailDecoderService.strip_html(texto)

        # El carácter de reemplazo delata bytes truncados a mitad de secuencia UTF-8.
        texto = texto.replace("\ufffd", "")
        compactado = " ".join(texto.split())
        if len(compactado) <= max_chars:
            return compactado
        return compactado[:max_chars].rstrip() + "…"

    @staticmethod
    def sanitize_text(text: str | None) -> str:
        """Sanitizes text content removing null bytes and trailing whitespace."""
        if not text:
            return ""
        # Remove null bytes
        cleaned = text.replace("\x00", "")
        # Normalize multiple trailing line breaks
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()


# Palabras clave: señales de proyecto/telemetría y calidad de energía.
_PALABRAS_PROYECTO: tuple[str, ...] = (
    "automatizacion",
    "bajada de datos",
    "lineas de inyeccion",
    "inyectoras",
    "plc",
    "scada",
    "telemetria",
    "tiempos de ciclo",
    "reunion en planta",
    "evaluando proveedores",
    "cotizacion",
    "rfq",
)
_PALABRAS_ENERGIA: tuple[str, ...] = (
    "factor de potencia",
    "cos fi",
    "cos phi",
    "multa edenor",
    "recargo edenor",
    "banco de capacitores",
    "compensacion reactiva",
)
_PALABRAS_DOCENCIA: tuple[str, ...] = (
    "sad",
    "secretaria de asuntos docentes",
    "jefatura de inspeccion",
    "abc",
    "designacion",
)
_PALABRAS_FACTURACION: tuple[str, ...] = (
    "factura",
    "presupuesto proveedor",
    "orden de compra proveedor",
)
_PALABRAS_NEWSLETTER: tuple[str, ...] = (
    "unsubscribe",
    "newsletter",
    "mailchimp",
    "hubspot",
    "bulk",
)
_PALABRAS_CARGO_COMPRA: tuple[str, ...] = (
    "buyer",
    "comprador",
    "jefe de mantenimiento",
    "jefe de planta",
    "gerente de produccion",
)
_GRUPOS_AUTOMOTRICES: dict[str, str] = {
    "jtekt": "JTEKT AUTOMOTIVE ARGENTINA (Toyota Group)",
    "toyota boshoku": "TOYOTA BOSHOKU (Toyota Group)",
    "denso": "DENSO (Toyota Group)",
    "faurecia": "FAURECIA (Grupo Forvia)",
}
_FREEMAIL_DOMINIOS: set[str] = {
    "gmail.com",
    "gmail.com.ar",
    "hotmail.com",
    "hotmail.com.ar",
    "outlook.com",
    "yahoo.com",
    "yahoo.com.ar",
    "icloud.com",
    "live.com",
    "proton.me",
    "aol.com",
}

_NORMALIZAR_MAPA = {
    "á": "a",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "ñ": "n",
    "ü": "u",
    "Á": "a",
    "É": "e",
    "Í": "i",
    "Ó": "o",
    "Ú": "u",
    "Ñ": "n",
    "Ü": "u",
}


def _normalizar(texto: str) -> str:
    """Normaliza acentos y pasa a minúsculas para matching determinístico."""
    resultado = texto
    for origen, destino in _NORMALIZAR_MAPA.items():
        resultado = resultado.replace(origen, destino)
    return resultado.lower()


def _contiene_palabras(texto: str, palabras: tuple[str, ...]) -> bool:
    return any(p in texto for p in palabras)


def _contar_señales(texto: str, palabras: tuple[str, ...]) -> int:
    """Cuenta cuántas distintas señales de la lista aparecen en el texto."""
    return sum(1 for p in palabras if p in texto)


def _primer_match(texto: str, palabras: tuple[str, ...]) -> str | None:
    for p in palabras:
        if p in texto:
            return p
    return None


def _partes_remitente(remitente: str) -> tuple[str, str]:
    """Separa el remitente en (nombre visible, dirección).

    El par de ángulos se resuelve a mano porque `parseaddr` interpreta la coma de
    `Gurzale, Sol <sol.gurzale@jtekt.com>` como separador de una lista de direcciones
    y devuelve el nombre partido — y así es como llegan los correos corporativos reales.
    """
    crudo = (remitente or "").strip()
    if not crudo:
        return "", ""

    m = re.search(r"<([^<>]+)>\s*$", crudo)
    if m:
        direccion = m.group(1).strip()
        nombre = crudo[: m.start()].strip().strip("\"'").strip()
        return nombre, direccion

    nombre, direccion = parseaddr(crudo)
    if not direccion and "@" in crudo:
        direccion = crudo
    return nombre.strip(), direccion.strip()


class EmailOpportunityAnalyzerService:
    """Motor determinístico (cero LLM) de scoring de oportunidades B2B en correos.

    Evalúa palabras clave técnicas, dominios corporativos, firmas y grupos
    industriales en Python puro de dominio. Aplica la regla de inmutabilidad:
    no hardcodea datos monetarios volátiles; solo clasifica señales textuales.
    """

    def analizar(self, detail: EmailDetail, cuenta: str = "") -> AnalisisEmail:
        cuerpo_norm = _normalizar(
            f"{detail.asunto}\n{detail.cuerpo_texto}\n{detail.remitente}"
        )
        remitente_norm = _normalizar(detail.remitente)

        # Scoring acumulativo por cada señal de proyecto/energía encontrada,
        # acotado para no explotar por mera extensión de texto.
        hay_docencia = _contiene_palabras(cuerpo_norm, _PALABRAS_DOCENCIA)
        hay_facturacion = _contiene_palabras(cuerpo_norm, _PALABRAS_FACTURACION)
        hay_newsletter = _contiene_palabras(cuerpo_norm, _PALABRAS_NEWSLETTER)

        señales_proyecto = _contar_señales(cuerpo_norm, _PALABRAS_PROYECTO)
        señales_energia = _contar_señales(cuerpo_norm, _PALABRAS_ENERGIA)

        score = 0
        hay_proyecto = señales_proyecto > 0
        hay_energia = señales_energia > 0
        if hay_proyecto:
            score += min(50, 20 + 10 * señales_proyecto)
        if hay_energia:
            score += min(50, 20 + 10 * señales_energia)
        score += min(30, 10 * señales_proyecto)  # refuerzo por densidad de señales

        dominio_corporativo = self._es_dominio_corporativo(remitente_norm)
        rol_comprador = _contiene_palabras(cuerpo_norm, _PALABRAS_CARGO_COMPRA)
        if dominio_corporativo:
            score += 15
        if rol_comprador:
            score += 15

        grupo = self._detectar_grupo(cuerpo_norm)
        if grupo:
            score += 10

        telefonos = self._extraer_telefonos(detail.cuerpo_texto)
        if telefonos:
            score += 5

        score = max(0, min(100, score))

        if hay_newsletter:
            categoria = CategoriaEmail.SPAM_NEWSLETTER
        elif hay_docencia and not hay_proyecto:
            categoria = CategoriaEmail.DOCENCIA_OFICIAL
        elif hay_facturacion and not (hay_proyecto or hay_energia):
            categoria = CategoriaEmail.PROVEEDOR_FACTURACION
        elif (
            (hay_proyecto or hay_energia)
            and (dominio_corporativo or rol_comprador)
            or score >= 40
        ):
            categoria = CategoriaEmail.OPORTUNIDAD_COMERCIAL
        else:
            categoria = CategoriaEmail.GENERAL_INFORMATIVO

        requiere_alerta = (
            categoria == CategoriaEmail.OPORTUNIDAD_COMERCIAL and score >= 40
        )
        prioridad = (
            self._asignar_prioridad(score)
            if categoria == CategoriaEmail.OPORTUNIDAD_COMERCIAL
            else NivelPrioridad.BAJA
        )

        entidades = self._extraer_entidades(
            detail=detail,
            cuerpo_norm=cuerpo_norm,
            remitente_norm=remitente_norm,
            grupo=grupo,
            tipo_proyecto=self._tipo_proyecto(cuerpo_norm),
        )

        resumen = self._resumen_ejecutivo(
            hay_proyecto=hay_proyecto,
            hay_energia=hay_energia,
            categoria=categoria,
        )
        accion = self._accion_sugerida(categoria, entidades)

        return AnalisisEmail(
            uid=detail.uid,
            categoria=categoria,
            prioridad=prioridad,
            score=score,
            resumen_ejecutivo=resumen,
            accion_sugerida=accion,
            entidades=entidades,
            requiere_alerta=requiere_alerta,
            cuenta=cuenta,
        )

    @staticmethod
    def _dominio_remitente(remitente_norm: str) -> str:
        """Devuelve el dominio del remitente, tolerando el formato `Nombre <addr>`."""
        _nombre, direccion = _partes_remitente(remitente_norm)
        m = re.search(r"[@]([a-z0-9.-]+)$", direccion)
        return m.group(1) if m else ""

    @staticmethod
    def _es_dominio_corporativo(remitente_norm: str) -> bool:
        """Detecta si el remitente pertenece a un dominio no-freemail/corporativo."""
        dominio = EmailOpportunityAnalyzerService._dominio_remitente(remitente_norm)
        if not dominio or dominio in _FREEMAIL_DOMINIOS:
            return False
        return "." in dominio

    @staticmethod
    def _detectar_grupo(cuerpo_norm: str) -> str | None:
        for clave, nombre in _GRUPOS_AUTOMOTRICES.items():
            if clave in cuerpo_norm:
                return nombre
        return None

    @staticmethod
    def _extraer_telefonos(texto: str) -> list[str]:
        resultados: list[str] = []
        cuerpo_limpio = texto.replace("\x00", "")
        for m in re.finditer(r"(?<!\d)(\+?\d[\d\s().-]{8,}\d)(?!\d)", cuerpo_limpio):
            numero = m.group(1).strip()
            if numero not in resultados:
                resultados.append(numero)
        return resultados[:3]

    @staticmethod
    def _tipo_proyecto(cuerpo_norm: str) -> str | None:
        if "inyeccion" in cuerpo_norm or "inyectoras" in cuerpo_norm:
            return "Bajada de Datos / Telemetría de Inyectoras"
        if "factor de potencia" in cuerpo_norm or "cos fi" in cuerpo_norm:
            return "Calidad de Energía / Factor de Potencia"
        match = _primer_match(cuerpo_norm, _PALABRAS_PROYECTO[:6])
        return match.capitalize() if match else None

    @staticmethod
    def _extraer_entidades(
        detail: EmailDetail,
        cuerpo_norm: str,
        remitente_norm: str,
        grupo: str | None,
        tipo_proyecto: str | None,
    ) -> EntidadesDetectadas:
        # Empresa
        empresa: str | None = None
        if grupo:
            empresa = grupo
        else:
            dominio = EmailOpportunityAnalyzerService._dominio_remitente(remitente_norm)
            if dominio and dominio not in _FREEMAIL_DOMINIOS:
                empresa = dominio.split(".")[0].capitalize()

        # Cargo: buscar rol comprador en el cuerpo
        cargo = None
        for rol in _PALABRAS_CARGO_COMPRA:
            idx = cuerpo_norm.find(rol)
            if idx != -1:
                cargo = rol.capitalize()
                break

        # Nombre: el display name del remitente si viene; si no, el local-part.
        display, direccion = _partes_remitente(detail.remitente)
        nombre: str | None = display or None
        if nombre and "," in nombre:
            # Los directorios corporativos escriben "Apellido, Nombre".
            apellido, _, pila = nombre.partition(",")
            if pila.strip():
                nombre = f"{pila.strip()} {apellido.strip()}"
        if not nombre:
            local = (direccion or detail.remitente).split("@")[0]
            nombre = local.replace(".", " ").strip().title() or None

        return EntidadesDetectadas(
            empresa=empresa,
            contacto_nombre=nombre,
            contacto_cargo=cargo,
            tipo_proyecto=tipo_proyecto,
            ubicacion_planta=None,
            telefonos=_extraer_telefonos_priv(detail.cuerpo_texto),
        )

    @staticmethod
    def _asignar_prioridad(score: int) -> NivelPrioridad:
        if score >= 70:
            return NivelPrioridad.ALTA
        if score >= 40:
            return NivelPrioridad.MEDIA
        return NivelPrioridad.BAJA

    @staticmethod
    def _resumen_ejecutivo(
        hay_proyecto: bool, hay_energia: bool, categoria: CategoriaEmail
    ) -> str:
        if categoria != CategoriaEmail.OPORTUNIDAD_COMERCIAL:
            return f"Correo clasificado como {categoria.value}. No requiere seguimiento comercial."
        partes: list[str] = []
        if hay_proyecto:
            partes.append(
                "busca proveedores para proyecto de automatización/telemetría"
            )
        if hay_energia:
            partes.append(
                "presenta requerimiento de calidad de energía/factor de potencia"
            )
        if not partes:
            partes.append("presenta una solicitud comercial")
        return "El correo " + "; ".join(partes) + "."

    @staticmethod
    def _accion_sugerida(
        categoria: CategoriaEmail, entidades: EntidadesDetectadas
    ) -> str:
        if categoria != CategoriaEmail.OPORTUNIDAD_COMERCIAL:
            return "Sin acción requerida."
        destino = entidades.empresa or "el contacto"
        return f"Responder a {destino} proponiendo franja horaria para reunión técnica."


def _extraer_telefonos_priv(texto: str) -> list[str]:
    resultados: list[str] = []
    for m in re.finditer(r"(?<!\d)(\+?\d[\d\s.()-]{8,}\d)(?!\d)", texto):
        numero = m.group(1).strip()
        if numero not in resultados:
            resultados.append(numero)
    return resultados[:3]
