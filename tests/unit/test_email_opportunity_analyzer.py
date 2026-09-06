"""Tests unitarios del analizador determinístico de oportunidades B2B en correos.

Casos de estudio reales: JTEKT Automotive / Toyota Group, calidad de energía
(factor de potencia / multa Edenor), newsletters/spam, avisos bancarios y
notificaciones docentes SAD/ABC.
"""

from src.domain.mail.entities import EmailDetail
from src.domain.mail.services import EmailOpportunityAnalyzerService
from src.domain.mail.value_objects import CategoriaEmail, NivelPrioridad


def _email(
    cuerpo_texto: str,
    *,
    remitente: str = "sol.gurzale@jtekt.onmicrosoft.com",
    asunto: str = "",
) -> EmailDetail:
    return EmailDetail(
        uid="99",
        remitente=remitente,
        asunto=asunto,
        cuerpo_texto=cuerpo_texto,
        carpeta="INBOX",
    )


def test_caso_real_jtekt_toyota_group() -> None:
    """Dado un correo de Sol Gurzalé (JTEKT/Toyota) → OPORTUNIDAD, ALTA, score alto."""
    cuerpo = (
        "Estimados, somos JTEKT Automotive Argentina (Toyota Group). "
        "Estamos analizando potenciales proveedores para la bajada de datos "
        "de las lineas de inyeccion a PC local. Ademas necesitamos telemetria "
        "de tiempos de ciclo y coordinamos una reunion en planta. Solicitamos "
        "cotizacion formal.\n\n"
        "Sol Gurzalé\n"
        "Buyer\n"
        "Móvil: +54 11 5555-1234"
    )
    resultado = EmailOpportunityAnalyzerService().analizar(_email(cuerpo))

    assert resultado.categoria == CategoriaEmail.OPORTUNIDAD_COMERCIAL
    assert resultado.prioridad == NivelPrioridad.ALTA
    assert resultado.score >= 85
    assert resultado.requiere_alerta is True
    assert (
        "Toyota Group" in resultado.entidades.empresa
        or "JTEKT" in resultado.entidades.empresa
    )
    assert resultado.entidades.contacto_cargo == "Buyer"
    assert resultado.entidades.tipo_proyecto is not None
    assert resultado.entidades.telefonos
    assert resultado.resumen_ejecutivo
    assert resultado.accion_sugerida


def test_caso_factor_de_potencia_multa_edenor() -> None:
    """Dado un correo sobre factor de potencia y multa Edenor → OPORTUNIDAD, ALTA."""
    cuerpo = (
        "Buenos dias, somos una fabrica con un problema de factor de potencia. "
        "Edendor nos aplica una multa por cos fi bajo y necesitamos evaluar "
        "un banco de capacitores y compensacion reactiva. "
        "Nos gustaria coordinar una visita tecnica.\n\n"
        "Jefe de Mantenimiento\n"
        "Juan Perez\n"
        "juan.perez@fabrica.com.ar"
    )
    resultado = EmailOpportunityAnalyzerService().analizar(
        _email(cuerpo), cuenta="datamaq"
    )

    assert resultado.categoria == CategoriaEmail.OPORTUNIDAD_COMERCIAL
    assert resultado.prioridad == NivelPrioridad.ALTA
    assert resultado.score >= 70


def test_newsletter_spam_no_alerta() -> None:
    """Dado un newsletter con unsubscribe → SPAM_NEWSLETTER, BAJA, sin alerta."""
    cuerpo = (
        "Descubrí las mejores prácticas de automatización industrial\n"
        "<a>Unsubscribe</a> para no recibir más correos."
    )
    resultado = EmailOpportunityAnalyzerService().analizar(
        _email(cuerpo, remitente="news@mailchimp.com")
    )

    assert resultado.categoria == CategoriaEmail.SPAM_NEWSLETTER
    assert resultado.prioridad == NivelPrioridad.BAJA
    assert resultado.requiere_alerta is False


def test_aviso_bancario_generico_no_alerta() -> None:
    """Dado un aviso bancario genérico → GENERAL_INFORMATIVO, sin alerta."""
    cuerpo = (
        "Estimado cliente, su resumen de cuenta de agosto ya está disponible. "
        "Ingrese a su home banking para ver el detalle de movimientos."
    )
    resultado = EmailOpportunityAnalyzerService().analizar(
        _email(cuerpo, remitente="no-reply@banco.example.com")
    )

    assert resultado.categoria != CategoriaEmail.OPORTUNIDAD_COMERCIAL
    assert resultado.requiere_alerta is False


def test_notificacion_docente_sad_abc() -> None:
    """Dado un correo de SAD/ABC de designación docente → DOCENCIA_OFICIAL."""
    cuerpo = (
        "SECRETARÍA DE ASUNTOS DOCENTES — SAD 9. Se informa la designación "
        "provisional en el cargo para el ciclo 2026. Adjuntamos la resolución."
    )
    resultado = EmailOpportunityAnalyzerService().analizar(
        _email(cuerpo, remitente="sad9@abc.gob.ar")
    )

    assert resultado.categoria == CategoriaEmail.DOCENCIA_OFICIAL
    assert resultado.requiere_alerta is False


def test_umbrales_de_prioridad() -> None:
    """Dado scores con umbrales 70/40 → ALTA/MEDIA/BAJA."""
    # Contexto 100% industrial sin dominio corporativo (remitente freemail)
    alta = EmailOpportunityAnalyzerService().analizar(
        _email(
            "automatizacion bajada de datos lineas de inyeccion inyectoras plc "
            "scada telemetria tiempos de ciclo reunion en planta evaluando "
            "proveedores cotizacion rfq",
            remitente="jefe@hotmail.com",
        )
    )
    media = EmailOpportunityAnalyzerService().analizar(
        _email("telemetria de tiempos de ciclo en la planta", remitente="a@yahoo.com")
    )
    baja = EmailOpportunityAnalyzerService().analizar(
        _email("hola, como va todo?", remitente="a@gmail.com")
    )

    assert alta.prioridad == NivelPrioridad.ALTA
    assert media.prioridad == NivelPrioridad.MEDIA
    assert baja.prioridad == NivelPrioridad.BAJA
    assert 0 <= alta.score <= 100
    assert 0 <= media.score <= 100
    assert 0 <= baja.score <= 100


def test_partes_remitente_resuelve_el_formato_de_directorio_corporativo():
    """Los directorios corporativos mandan "Apellido, Nombre <addr>"; la coma rompe parseaddr."""
    from src.domain.mail.services import _partes_remitente

    assert _partes_remitente("Gurzale, Sol <sol.gurzale@jtekt.onmicrosoft.com>") == (
        "Gurzale, Sol",
        "sol.gurzale@jtekt.onmicrosoft.com",
    )
    assert _partes_remitente('"Perez, Juan" <juan@empresa.com>') == (
        "Perez, Juan",
        "juan@empresa.com",
    )
    assert _partes_remitente("ana@siderar.com.ar") == ("", "ana@siderar.com.ar")
    assert _partes_remitente("") == ("", "")


def test_dominio_corporativo_se_detecta_con_nombre_visible():
    """Regresión: el `$` del regex fallaba con `Nombre <addr>` y se perdían 15 puntos de score."""
    from src.domain.mail.services import EmailOpportunityAnalyzerService, _normalizar

    detectar = EmailOpportunityAnalyzerService._es_dominio_corporativo
    assert (
        detectar(_normalizar("Gurzale, Sol <sol.gurzale@jtekt.onmicrosoft.com>"))
        is True
    )
    assert detectar(_normalizar("sol.gurzale@jtekt.onmicrosoft.com")) is True
    # Freemail sigue sin contar como corporativo, venga como venga.
    assert detectar(_normalizar("Juan Perez <juan@gmail.com>")) is False
    assert detectar(_normalizar("juan@gmail.com")) is False


def test_analisis_extrae_nombre_legible_del_display_name():
    from src.domain.mail.entities import EmailDetail
    from src.domain.mail.services import EmailOpportunityAnalyzerService
    from src.domain.mail.value_objects import CategoriaEmail, NivelPrioridad

    correo = EmailDetail(
        uid="1",
        remitente="Gurzale, Sol <sol.gurzale@jtekt.onmicrosoft.com>",
        asunto="RE: Proyecto automatización",
        cuerpo_texto=(
            "Estamos evaluando proveedores para la bajada de datos de las lineas de "
            "inyeccion y los tiempos de ciclo de las inyectoras. Jefe de mantenimiento."
        ),
    )
    analisis = EmailOpportunityAnalyzerService().analizar(
        correo, cuenta="info@datamaq.com.ar"
    )

    assert analisis.entidades.contacto_nombre == "Sol Gurzale"
    assert analisis.entidades.empresa == "JTEKT AUTOMOTIVE ARGENTINA (Toyota Group)"
    assert analisis.categoria == CategoriaEmail.OPORTUNIDAD_COMERCIAL
    assert analisis.prioridad == NivelPrioridad.ALTA
    assert analisis.requiere_alerta is True


def test_analisis_deduce_nombre_del_local_part_si_no_hay_display_name():
    from src.domain.mail.entities import EmailDetail
    from src.domain.mail.services import EmailOpportunityAnalyzerService

    correo = EmailDetail(
        uid="2", remitente="ana.lopez@siderar.com.ar", asunto="Consulta"
    )
    analisis = EmailOpportunityAnalyzerService().analizar(correo)
    assert analisis.entidades.contacto_nombre == "Ana Lopez"
