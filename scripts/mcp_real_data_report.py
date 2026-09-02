#!/usr/bin/env python3
"""Genera un reporte consolidado con los valores reales de los tres servidores FastMCP.
Utiliza los gateways existentes (GoogleAdsGateway, GA4Gateway, ClarityGateway) y la clase Settings
para cargar credenciales desde el .env.
El reporte se escribe en `reports/fastmcp_report_YYYYMMDD.md`.
"""
import datetime
from pathlib import Path

from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.infrastructure.pydantic.config import Settings


def main() -> None:
    settings = Settings()
    # ---------- Google Ads ----------
    ads = GoogleAdsGateway(
        settings.google_ads_developer_token,
        settings.google_ads_client_id,
        settings.google_ads_client_secret,
        settings.google_ads_refresh_token,
        settings.google_ads_login_customer_id,
    )
    pacing = ads.get_daily_budget_pacing()
    perf = ads.get_campaign_performance(days=7)
    search_terms = ads.get_search_terms_report(days=7, limit=20)

    # ---------- GA4 ----------
    ga4 = GA4Gateway(
        settings.ga4_property_id,
        settings.google_application_credentials,
    )
    top_pages = ga4.get_top_pages(days=7, limit=10)
    traffic = ga4.get_traffic_sources(days=7, limit=10)
    conversions = ga4.get_conversions(days=7)

    # ---------- Clarity ----------
    clarity = ClarityGateway(settings.clarity_id, settings.clarity_api_token)
    project_info = clarity.get_project_info()
    live = clarity.get_live_insights()
    intent_urls = clarity.get_intent_recording_urls()

    # ---------- Render report ----------
    today = datetime.date.today().isoformat()
    report_path = Path("reports") / f"fastmcp_report_{today}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        f.write(f"# FastMCP Report – {today}\n\n")
        f.write("## Google Ads – Pacing\n")
        f.write(f"- Gasto hoy: {pacing.get('spent_ars')} ARS\n")
        f.write(f"- Límite diario: {pacing.get('daily_budget_limit_ars')} ARS\n")
        f.write(f"- % del límite: {pacing.get('pacing_percentage')}\n\n")
        f.write("## Google Ads – Performance (últimos 7 días)\n")
        f.write(f"- Impresiones totales: {perf.get('total_impressions', 'N/A')}\n")
        f.write(f"- Clics totales: {perf.get('total_clicks', 'N/A')}\n")
        f.write(f"- CPC medio: {perf.get('avg_cpc_ars', 'N/A')} ARS\n\n")
        f.write("## Google Ads – Términos de búsqueda (top 20)\n")
        for term in search_terms.get('terms', []):
            f.write(f"- {term['search_term']} (clics: {term['clicks']}, conv: {term['conversions']})\n")
        f.write("\n")
        f.write("## GA4 – Top Pages\n")
        for row in top_pages.get('rows', []):
            f.write(f"- {row.get('pagePath')} – vistas: {row.get('screenPageViews')} – usuarios: {row.get('activeUsers')}\n")
        f.write("\n")
        f.write("## GA4 – Fuentes de tráfico\n")
        for row in traffic.get('rows', []):
            f.write(f"- {row.get('sessionSource')}/{row.get('sessionMedium')} – sesiones: {row.get('sessions')}\n")
        f.write("\n")
        f.write("## GA4 – Conversiones (eventos)\n")
        for row in conversions.get('rows', []):
            f.write(f"- {row.get('eventName')} – count: {row.get('eventCount')}\n")
        f.write("\n")
        f.write("## Clarity – Project Info\n")
        f.write(f"- Dashboard: {project_info.get('dashboard_url')}\n")
        f.write(f"- Heatmaps: {project_info.get('heatmaps_url')}\n")
        f.write("\n")
        f.write("## Clarity – Live Insights\n")
        live_data = live.get('data', {})
        f.write(f"- Usuarios activos: {live_data.get('activeUsers', 'N/A')}\n")
        f.write(f"- Page views: {live_data.get('pageViews', 'N/A')}\n")
        f.write("\n")
        f.write("## Clarity – Grabaciones por intención\n")
        for intent, url in intent_urls.items():
            f.write(f"- {intent}: {url}\n")
    print(f"Reporte generado: {report_path}")


if __name__ == "__main__":
    main()
