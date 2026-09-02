#!/usr/bin/env python3
"""Watchdog determinístico y generador de reportes proactivos de analítica y presupuesto (DataMaq Hub).

Monitorea:
1. Google Ads: Pacing de presupuesto diario ($1.500 ARS/día límite) y KPIs calculados.
2. GA4: Eventos de conversión (direct_contact, whatsapp_click, etc.) y tráfico reciente.
3. Microsoft Clarity: Grabaciones con lead_intent y UX.
4. Detección automática de anomalías determinísticas y alertas.

Puede ejecutarse vía cron/systemd timer o manualmente. Envía reportes a Telegram
si `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` están configurados.

Uso:
    PYTHONPATH=. ./venv/bin/python scripts/analytics_watchdog.py [--dry-run] [--json] [--budget-limit LIMIT]
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.adapters.gateways.gbp_gateway import GoogleBusinessProfileGateway
from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway
from src.application.use_cases.generar_analytics_digest import (
    DEFAULT_BUDGET_LIMIT_ARS,
    GenerarAnalyticsDigestUseCase,
)
from src.infrastructure.pydantic.config import get_settings


def send_telegram_alert(text: str, bot_token: str, chat_id: str) -> bool:
    """Envía la alerta formateada a Telegram mediante Bot API."""
    if not bot_token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print(f"[Watchdog] Error enviando alerta a Telegram: {exc}", file=sys.stderr)
        return False


def run_watchdog(
    dry_run: bool = False,
    budget_limit_ars: float = DEFAULT_BUDGET_LIMIT_ARS,
) -> dict[str, Any]:
    """Ejecuta el pipeline de analítica determinístico y retorna el estado estructurado."""
    settings = get_settings()

    # Configurar ADC de Google para GA4
    if settings.google_application_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
            settings.google_application_credentials
        )

    cache = ApiCacheGateway(
        database_url=settings.database_url,
        ttl_by_prefix=settings.cache_ttls or None,
    )
    ads_gw = GoogleAdsGateway(
        developer_token=settings.google_ads_developer_token,
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
        refresh_token=settings.google_ads_refresh_token,
        customer_id=settings.google_ads_login_customer_id,
        cache=cache,
    )
    ga4_gw = GA4Gateway(
        ga4_property_id=settings.ga4_property_id,
        google_application_credentials=settings.google_application_credentials,
        cache=cache,
    )
    clarity_gw = ClarityGateway(
        clarity_id=settings.clarity_id,
        clarity_api_token=settings.clarity_api_token,
        cache=cache,
    )

    gbp_gw = GoogleBusinessProfileGateway(
        client_id=settings.gbp_oauth_client_id,
        client_secret=settings.gbp_oauth_client_secret,
        refresh_token=settings.gbp_refresh_token,
        account_id=settings.gbp_account_id,
        location_id=settings.gbp_location_id,
        cache=cache,
    )

    use_case = GenerarAnalyticsDigestUseCase(
        google_ads_port=ads_gw,
        ga4_port=ga4_gw,
        clarity_port=clarity_gw,
        budget_limit_ars=budget_limit_ars,
        gbp_port=gbp_gw,
    )

    digest_dto = use_case.execute(days=1)
    report_dict = digest_dto.model_dump()
    report_md = digest_dto.resumen_markdown

    telegram_sent = False
    if not dry_run and settings.telegram_bot_token and settings.telegram_chat_id:
        telegram_sent = send_telegram_alert(
            report_md, settings.telegram_bot_token, settings.telegram_chat_id
        )

    report_dict["telegram_sent"] = telegram_sent
    return report_dict


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Watchdog de analítica, conversiones y gasto de Ads (DataMaq Hub)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime el reporte en pantalla sin enviar mensaje a Telegram.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime la salida en formato JSON estructurado.",
    )
    parser.add_argument(
        "--budget-limit",
        type=float,
        default=DEFAULT_BUDGET_LIMIT_ARS,
        help="Límite diario de gasto en ARS para alertas (por defecto: 1500.0).",
    )

    args = parser.parse_args()
    result = run_watchdog(
        dry_run=args.dry_run,
        budget_limit_ars=args.budget_limit,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["resumen_markdown"])
        if result["telegram_sent"]:
            print("\n[Watchdog] ✅ Alerta enviada con éxito a Telegram.")
        elif not args.dry_run:
            print("\n[Watchdog] ℹ️ Telegram no configurado o modo dry-run.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
