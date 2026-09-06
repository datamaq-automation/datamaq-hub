#!/usr/bin/env python3
"""Watchdog de oportunidades comerciales en el correo entrante (DataMaq Hub).

Escanea los correos no leídos con el motor determinístico de scoring B2B y despacha
una alerta a Telegram por cada oportunidad nueva. La deduplicación (TTL de 30 días,
`ApiCachePort`) hace que sea seguro correrlo cada pocos minutos: un mismo correo
alerta una sola vez.

La lectura es estrictamente read-only (`BODY.PEEK`): los correos no se marcan como
leídos, así que el buzón humano queda intacto.

Uso:
    PYTHONPATH=. ./venv/bin/python scripts/mail_watchdog.py [--dry-run] [--json]
                                    [--cuenta datamaq] [--carpeta INBOX] [--limit 10]
"""

import argparse
import json
import sys
from typing import Any

from src.adapters.controllers.dependencies import (
    get_default_contacts_gateway,
    get_default_mail_notifier_gateway,
    get_default_tarea_gateway,
    get_mail_analysis_controller,
)
from src.adapters.gateways.api_cache_gateway import (
    ApiCacheGateway,
    resolve_database_url,
)
from src.adapters.gateways.cached_mail_reader_gateway import CachedMailReaderGateway
from src.adapters.gateways.gmail_api_gateway import GmailApiGateway
from src.adapters.gateways.imap_mail_gateway import ImapMailGateway
from src.application.dtos.mail_dto import ScanMailRequestDTO
from src.domain.mail.ports import MailNotifierPort, MailReaderPort
from src.infrastructure.pydantic.config import get_settings


class _NotificadorSilencioso(MailNotifierPort):
    """Sustituto de `--dry-run`: cuenta oportunidades sin mandar nada a Telegram."""

    def __init__(self) -> None:
        self.omitidas: list[str] = []

    def notificar_oportunidad_email(self, analisis: Any, email: Any) -> bool:
        self.omitidas.append(str(getattr(analisis, "uid", "")))
        # Devolver False evita que el caso de uso escriba la caché de deduplicación,
        # de modo que un dry-run no "consume" la alerta real.
        return False


def _build_reader(account: str | None) -> tuple[MailReaderPort, ApiCacheGateway]:
    """Arma el lector de correo con caché para la cuenta indicada."""
    settings = get_settings()
    cfg = settings.get_mail_account_config(account)

    reader: MailReaderPort
    if cfg.oauth2_refresh_token:
        reader = GmailApiGateway(
            client_id=cfg.oauth2_client_id,
            client_secret=cfg.oauth2_client_secret,
            refresh_token=cfg.oauth2_refresh_token,
            user_email=cfg.user,
            timeout_seconds=cfg.timeout_seconds,
        )
    else:
        reader = ImapMailGateway(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            use_ssl=cfg.use_ssl,
            timeout_seconds=cfg.timeout_seconds,
            oauth2_client_id=cfg.oauth2_client_id,
            oauth2_client_secret=cfg.oauth2_client_secret,
            oauth2_refresh_token=cfg.oauth2_refresh_token,
        )

    cache = ApiCacheGateway(
        database_url=resolve_database_url(settings.database_url),
        ttl_by_prefix=settings.cache_ttls or None,
    )
    cacheado: MailReaderPort = CachedMailReaderGateway(
        reader=reader, cache=cache, account=cfg.user
    )
    return cacheado, cache


def run_mail_watchdog(
    cuenta: str | None = None,
    carpeta: str = "INBOX",
    limit: int = 10,
    dry_run: bool = False,
    auto_contacto: bool = False,
) -> dict[str, Any]:
    """Ejecuta el escaneo y devuelve el resultado estructurado."""
    settings = get_settings()
    reader, cache = _build_reader(cuenta)
    cfg = settings.get_mail_account_config(cuenta)

    notifier: MailNotifierPort
    if dry_run:
        notifier = _NotificadorSilencioso()
    else:
        notifier = get_default_mail_notifier_gateway(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )

    controller = get_mail_analysis_controller(
        gateway=reader,
        cache=cache,
        notifier=notifier,
        contacts_repo=(
            get_default_contacts_gateway(database_url=settings.roundcube_db_url)
            if auto_contacto
            else None
        ),
        tarea_repo=get_default_tarea_gateway(database_url=settings.database_url),
    )

    # `get_mail_account_config` tiene un fallback deliberado a la primera cuenta de
    # MAIL_ACCOUNTS cuando el buzón por defecto no tiene credenciales. Es útil para
    # consultas interactivas, pero en un cron sin supervisión significaría escanear
    # el buzón equivocado en silencio: se avisa por stderr.
    solicitada = (cuenta or settings.default_mail_account).strip().lower()
    if solicitada not in {cfg.user.lower(), "default", "datamaq"}:
        print(
            f"[MailWatchdog] Aviso: se pidió '{solicitada}' y se resolvió el buzón "
            f"'{cfg.user}'. Verificá MAIL_IMAP_USER / MAIL_ACCOUNTS.",
            file=sys.stderr,
        )

    resultado = controller.analizar_correos(
        dto=ScanMailRequestDTO(
            cuenta=cfg.user,
            carpeta=carpeta,
            limit=limit,
            auto_registrar_contacto=auto_contacto,
        )
    )
    salida = resultado.model_dump()
    salida["cuenta"] = cfg.user
    salida["dry_run"] = dry_run
    return salida


def _imprimir_resumen(resultado: dict[str, Any]) -> None:
    print(
        f"📬 Buzón {resultado['cuenta']}: "
        f"{resultado['total_escaneados']} correos escaneados, "
        f"{resultado['total_oportunidades']} oportunidades, "
        f"{resultado['alertas_enviadas']} alertas enviadas."
    )
    for analisis in resultado.get("analisis", []):
        if analisis["categoria"] != "OPORTUNIDAD_COMERCIAL":
            continue
        entidades = analisis.get("entidades", {})
        print(
            f"  · [{analisis['prioridad']}] {entidades.get('empresa') or 'Empresa desconocida'}"
            f" — {entidades.get('contacto_nombre') or 'contacto sin identificar'}"
            f" (score {analisis['score']}/100)"
        )
    if resultado["dry_run"]:
        print(
            "ℹ️  Modo dry-run: no se envió ninguna alerta ni se marcó la deduplicación."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Watchdog de oportunidades B2B en el correo entrante (DataMaq Hub)."
    )
    parser.add_argument(
        "--cuenta", default=None, help="Alias o email de la cuenta a escanear."
    )
    parser.add_argument(
        "--carpeta", default="INBOX", help="Carpeta IMAP a inspeccionar."
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Máximo de correos a escanear."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calcula el scoring sin enviar alertas ni tocar la deduplicación.",
    )
    parser.add_argument(
        "--auto-contact",
        action="store_true",
        help="Registra el contacto en la libreta de Roundcube ante cada alerta nueva.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Salida en JSON estructurado."
    )
    args = parser.parse_args()

    try:
        resultado = run_mail_watchdog(
            cuenta=args.cuenta,
            carpeta=args.carpeta,
            limit=args.limit,
            dry_run=args.dry_run,
            auto_contacto=args.auto_contact,
        )
    except Exception as exc:  # noqa: BLE001
        # El watchdog corre por cron sin supervisión: un fallo debe salir por stderr
        # con código distinto de cero, nunca romper silenciosamente.
        print(f"[MailWatchdog] Error durante el escaneo: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        _imprimir_resumen(resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
