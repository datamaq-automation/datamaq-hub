#!/usr/bin/env python3
"""Watchdog y generador de reportes proactivos de analítica y presupuesto (DataMaq Hub).

Monitorea:
1. Google Ads: Pacing de presupuesto diario ($1.500 ARS/día límite) y estado de campañas.
2. GA4: Eventos de conversión (direct_contact, whatsapp_click, etc.) y tráfico reciente.
3. Microsoft Clarity: Usuarios activos y enlaces directos a grabaciones con lead_intent.

Puede ejecutarse vía cron/systemd timer o manualmente. Envía reportes a Telegram
si `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` están configurados.

Uso:
    PYTHONPATH=. ./venv/bin/python scripts/analytics_watchdog.py [--dry-run] [--json]
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from src.infrastructure.fastmcp import clarity, ga4, google_ads
from src.infrastructure.pydantic.config import get_settings

DEFAULT_BUDGET_LIMIT_ARS = 1500.0


def _build_markdown_report(
    ads_data: dict[str, Any],
    ga4_data: dict[str, Any],
    clarity_data: dict[str, Any],
    budget_limit_ars: float,
) -> str:
    """Construye un reporte ejecutivo formateado en Markdown para Telegram / CLI."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [
        "🏭 *DataMaq Hub — Telemetría & Ads Watchdog*",
        f"📅 _{now_str}_\n",
    ]

    # 1. Google Ads
    lines.append("💰 *Google Ads:*")
    ads_status = ads_data.get("status", "unknown")
    if ads_status == "ready":
        pacing = ads_data.get("daily_budget_pacing", {})
        spent = float(pacing.get("spent_ars") or pacing.get("spent_today_ars") or 0.0)
        pacing_pct = (spent / budget_limit_ars) * 100.0 if budget_limit_ars > 0 else 0.0

        alert_icon = "⚠️" if spent > budget_limit_ars else "✅"
        lines.append(
            f"• Gasto Hoy: *${spent:,.2f} ARS* / Límite: *${budget_limit_ars:,.2f} ARS* ({pacing_pct:.1f}%) {alert_icon}"
        )
        campaigns = ads_data.get("campaigns", [])
        if campaigns:
            active_camps = [c for c in campaigns if c.get("status") == "ENABLED"]
            lines.append(f"• Campañas Activas ({len(active_camps)}):")
            for c in active_camps:
                lines.append(f"  - `{c.get('name', 'Campaña')}`")
        else:
            lines.append(
                f"• Estado Campañas: `{ads_data.get('campaign_status', 'ENABLED')}`"
            )
    else:
        lines.append(f"• Estado: `{ads_status}` (OAuth2 / Developer Token en espera)")

    # 2. GA4
    lines.append("\n📈 *Google Analytics 4 (Últimas 24h / 7d):*")
    ga4_status = ga4_data.get("status", "unknown")
    if ga4_status == "configured":
        convs = ga4_data.get("conversions", {}).get("rows", [])
        if convs:
            top_convs = [
                f"`{c.get('eventName', 'event')}`: {c.get('eventCount', '0')}"
                for c in convs[:4]
            ]
            lines.append("• Conversiones: " + ", ".join(top_convs))
        else:
            lines.append("• Conversiones: _Sin eventos registrados en el período_")

        pages = ga4_data.get("top_pages", {}).get("rows", [])
        if pages:
            top_p = [
                f"`{p.get('pagePath', '/')}` ({p.get('screenPageViews', '0')} views)"
                for p in pages[:3]
            ]
            lines.append("• Top Páginas: " + " | ".join(top_p))
    else:
        lines.append(f"• Estado: `{ga4_status}`")

    # 3. Microsoft Clarity
    lines.append("\n🎥 *Microsoft Clarity UX:*")
    proj_info = clarity_data.get("project_info", {})
    intent_urls = proj_info.get("intent_recording_urls", {})
    live_status = clarity_data.get("live_insights", {}).get("status", "unknown")

    if intent_urls:
        email_url = intent_urls.get("email_click", "")
        wa_url = intent_urls.get("whatsapp_click", "")
        form_url = intent_urls.get("form_submit", "")
        lines.append("• Grabaciones filtradas por intención:")
        if email_url:
            lines.append(f"  ✉️ [Email Clicks]({email_url})")
        if wa_url:
            lines.append(f"  💬 [WhatsApp Clicks]({wa_url})")
        if form_url:
            lines.append(f"  📋 [Form Submits]({form_url})")
    else:
        lines.append(f"• Estado: `{live_status}`")

    return "\n".join(lines)


def send_telegram_alert(text: str, bot_token: str, chat_id: str) -> bool:
    """Envía la alerta formateada a Telegram mediante Bot API."""
    if not bot_token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
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
    """Ejecuta las consultas y retorna el estado estructurado del watchdog."""
    settings = get_settings()

    # Configurar ADC de Google para GA4
    if settings.google_application_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
            settings.google_application_credentials
        )

    # 1. Google Ads
    ads_status = google_ads.get_google_ads_status()
    ads_data: dict[str, Any] = dict(ads_status)
    if ads_status.get("status") == "ready":
        ads_data["daily_budget_pacing"] = google_ads.get_daily_budget_pacing()
        perf = google_ads.get_campaign_performance(1)
        ads_data["campaigns"] = perf.get("campaigns", [])
        if perf.get("campaigns"):
            ads_data["campaign_status"] = perf["campaigns"][0].get("status", "ENABLED")

    # 2. GA4
    ga4_status = ga4.get_ga4_status()
    ga4_data: dict[str, Any] = dict(ga4_status)
    if ga4_status.get("status") == "configured":
        ga4_data["conversions"] = ga4.get_ga4_conversions(1)
        ga4_data["top_pages"] = ga4.get_ga4_top_pages(1)
        ga4_data["traffic_sources"] = ga4.get_ga4_traffic_sources(1)

    # 3. Clarity
    clarity_data: dict[str, Any] = {
        "project_info": clarity.get_clarity_project_info(),
        "live_insights": clarity.get_live_insights(),
    }

    report_md = _build_markdown_report(
        ads_data=ads_data,
        ga4_data=ga4_data,
        clarity_data=clarity_data,
        budget_limit_ars=budget_limit_ars,
    )

    telegram_sent = False
    if not dry_run and settings.telegram_bot_token and settings.telegram_chat_id:
        telegram_sent = send_telegram_alert(
            report_md, settings.telegram_bot_token, settings.telegram_chat_id
        )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ads": ads_data,
        "ga4": ga4_data,
        "clarity": clarity_data,
        "report_markdown": report_md,
        "telegram_sent": telegram_sent,
    }


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
        print(result["report_markdown"])
        if result["telegram_sent"]:
            print("\n[Watchdog] ✅ Alerta enviada con éxito a Telegram.")
        elif not args.dry_run:
            print("\n[Watchdog] ℹ️ Telegram no configurado o modo dry-run.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
