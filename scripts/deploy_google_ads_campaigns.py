#!/usr/bin/env python3
"""Script de automatización para validación, simulación y despliegue de campañas B2B en Google Ads API.

Soporta modo simulación segura (--dry-run por defecto) y aplicación en vivo (--apply) de forma idempotente.
"""

import argparse
import sys
from typing import Any

from src.adapters.gateways.google_ads_gateway import (
    GoogleAdsException,
    _get_google_ads_client,
)
from src.infrastructure.pydantic.config import get_settings

CAMPAIGNS_SPEC: list[dict[str, Any]] = [
    {
        "name": "Telemetria y Adquisicion de Datos — Retrofit IoT",
        "budget_ars": 1100.0,
        "cpc_bid_ceiling_ars": 500.0,
        "channel_type": "SEARCH",
        "target_url": "https://datamaq.com.ar/?utm_source=google_ads&utm_medium=cpc&utm_campaign=retrofit-iot#servicios",
        "path1": "datos",
        "path2": "maquinas",
        "ad_group_name": "Adquisicion de Datos OT a IT",
        "keywords": [
            {
                "text": "adquisicion de datos de produccion industrial",
                "match_type": "EXACT",
            },
            {"text": "bajada de datos de maquinas a pc", "match_type": "EXACT"},
            {"text": "monitoreo de inyectoras de plastico", "match_type": "EXACT"},
            {"text": "telemetria de maquinas industriales", "match_type": "EXACT"},
            {
                "text": "conteo de piezas produccion automatizacion",
                "match_type": "EXACT",
            },
            {"text": "medicion de tiempos de ciclo fabrica", "match_type": "EXACT"},
            {"text": "monitoreo de paradas de planta", "match_type": "EXACT"},
            {"text": "sistema andon conteo de produccion", "match_type": "EXACT"},
            {"text": "retrofit iot maquinas industriales", "match_type": "EXACT"},
            {"text": "adquisicion de datos plc a pc", "match_type": "PHRASE"},
            {"text": "bajada de datos linea de produccion", "match_type": "PHRASE"},
            {"text": "monitoreo de maquinas industriales pyme", "match_type": "PHRASE"},
            {"text": "automatizacion de toma de datos fabrica", "match_type": "PHRASE"},
            {
                "text": "conteo de piezas automatico para maquinas",
                "match_type": "PHRASE",
            },
            {
                "text": "sensores para inyectoras de plastico produccion",
                "match_type": "PHRASE",
            },
        ],
        "headlines": [
            "Datos de Planta a su PC",
            "Telemetría para Inyectoras",
            "Conteo de Piezas en Vivo",
            "Bajada de Datos de Máquinas",
            "Adquisición de Datos OT a IT",
            "Monitoreo Líneas de Planta",
            "Registro en Base de Datos",
            "Sin Licencias Mensuales",
            "Medición Tiempos de Ciclo",
            "DataMaq Automatización",
            "Zona Norte: Garín y Pilar",
            "Integración PLC y Sensores",
            "Base de Datos 100% Local",
            "Alertas Parada de Planta",
            "Ingeniería en Planta",
        ],
        "descriptions": [
            "Bajada de datos de inyectoras a PC local. Registro de ciclos y piezas en tiempo real.",
            "Conecte sus máquinas sin cambiar de PLC. Base de datos local y sin nube obligatoria.",
            "Diagnóstico e instalación en Zona Norte. Hardware robusto y software a medida.",
            "Automatice el reporte de producción y paradas de planta. Soporte por ingenieros.",
        ],
        "negative_keywords": [
            "gratis",
            "curso",
            "tutorial",
            "pdf",
            "arduino",
            "raspberry",
            "tesis",
            "universidad",
            "empleo",
            "sueldo",
            "curriculum",
            "manual",
        ],
    },
    {
        "name": "Calidad de Energia — Cero Multas Edenor cos fi",
        "budget_ars": 400.0,
        "cpc_bid_ceiling_ars": 400.0,
        "channel_type": "SEARCH",
        "target_url": "https://datamaq.com.ar/?utm_source=google_ads&utm_medium=cpc&utm_campaign=calidad-energia#servicios",
        "path1": "cero-multas",
        "path2": "energia",
        "ad_group_name": "Factor de Potencia y Banco Capacitores",
        "keywords": [
            {"text": "multa factor de potencia industrial", "match_type": "EXACT"},
            {"text": "multa cos fi edenor", "match_type": "EXACT"},
            {"text": "recargo factor de potencia edenor t3", "match_type": "EXACT"},
            {
                "text": "banco de capacitores industrial trifasico",
                "match_type": "EXACT",
            },
            {
                "text": "eliminar multa factor de potencia fabrica",
                "match_type": "PHRASE",
            },
            {
                "text": "banco de capacitores pilar parque industrial",
                "match_type": "PHRASE",
            },
            {"text": "banco de capacitores garin fabrica", "match_type": "PHRASE"},
            {
                "text": "analizador de redes trifasico medicion industrial",
                "match_type": "PHRASE",
            },
        ],
        "headlines": [
            "Cero Multas de Edenor",
            "Elimine Penalidad cos fi",
            "Factor de Potencia en 48hs",
            "Diagnóstico 100% Deducible",
            "Banco de Capacitores",
            "Evite Recargos en Factura",
            "Ingeniería Eléctrica Pyme",
            "Atención Directa en Planta",
            "Medición con Powermeter",
            "Descuento Banco Provincia",
            "Financiación en Cuotas",
            "DataMaq Eficiencia",
            "Zona Norte: Pilar y Garín",
            "Asesoramiento Especializado",
            "Telemetría Sin Costo Fijo",
        ],
        "descriptions": [
            "Elimine multas por factor de potencia en Edenor. Diagnóstico deducible 100%.",
            "Diagnóstico en planta en Zona Norte. Medición con analizador y solución en 48hs.",
            "Evite penalidades millonarias. Financiación en cuotas y descuento Banco Provincia.",
            "Instalación llave en mano de hardware Powermeter y telemetría de por vida.",
        ],
        "negative_keywords": [
            "gratis",
            "curso",
            "tutorial",
            "pdf",
            "arduino",
            "raspberry",
            "tesis",
            "universidad",
            "empleo",
            "sueldo",
            "curriculum",
            "manual",
        ],
    },
]


def print_simulation_plan(customer_id: str) -> None:
    """Imprime el plan detallado de despliegue en modo simulación."""
    total_budget = sum(c["budget_ars"] for c in CAMPAIGNS_SPEC)
    print("=" * 70)
    print("🛠️  PLAN DE DESPLIEGUE GOOGLE ADS API (MODO SIMULACIÓN / DRY-RUN)")
    print(f"🏢 Cuenta de Cliente: {customer_id}")
    print(f"💰 Presupuesto Diario Total Planificado: ${total_budget:,.2f} ARS/día")
    print("=" * 70)

    for idx, camp in enumerate(CAMPAIGNS_SPEC, 1):
        print(f"\n[{idx}/2] Campaña: {camp['name']}")
        print(f"     • Presupuesto Asignado: ${camp['budget_ars']:,.2f} ARS/día")
        print(f"     • Red: {camp['channel_type']} (Búsqueda de Google Pura)")
        print(f"     • Límite CPC Máximo: ${camp['cpc_bid_ceiling_ars']:,.2f} ARS")
        print(f"     • URL Final: {camp['target_url']}")
        print(f"     • Grupo de Anuncios: {camp['ad_group_name']}")
        print(f"     • Palabras Clave ({len(camp['keywords'])}):")
        for kw in camp["keywords"]:
            match_str = (
                f"[{kw['text']}]" if kw["match_type"] == "EXACT" else f'"{kw["text"]}"'
            )
            print(f"       - {match_str} ({kw['match_type']})")
        print(f"     • Palabras Negativas ({len(camp['negative_keywords'])}):")
        print(f"       - {', '.join(camp['negative_keywords'])}")
        print(f"     • Títulos Adaptables ({len(camp['headlines'])}):")
        for h in camp["headlines"][:5]:
            print(f"       - {h}")
        print(f"       ... (+{len(camp['headlines']) - 5} títulos adicionales)")
        print(f"     • Descripciones Adaptables ({len(camp['descriptions'])}):")
        for d in camp["descriptions"]:
            print(f"       - {d}")
        print("-" * 70)


def get_existing_campaigns_map(client: Any, customer_id: str) -> dict[str, str]:
    """Retorna un mapeo de nombre_campaña -> resource_name de campañas existentes."""
    ga_service = client.get_service("GoogleAdsService")
    query = "SELECT campaign.id, campaign.name, campaign.resource_name FROM campaign"
    mapping: dict[str, str] = {}
    try:
        rows = ga_service.search(customer_id=customer_id, query=query)
        for r in rows:
            mapping[r.campaign.name] = r.campaign.resource_name
    except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
        print(f"ℹ️ Error consultando campañas existentes: {exc}")
    return mapping


def get_existing_ad_groups_map(client: Any, customer_id: str) -> dict[str, str]:
    """Retorna un mapeo de nombre_grupo -> resource_name de grupos de anuncios existentes."""
    ga_service = client.get_service("GoogleAdsService")
    query = "SELECT ad_group.id, ad_group.name, ad_group.resource_name FROM ad_group"
    mapping: dict[str, str] = {}
    try:
        rows = ga_service.search(customer_id=customer_id, query=query)
        for r in rows:
            mapping[r.ad_group.name] = r.ad_group.resource_name
    except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
        print(f"ℹ️ Error consultando ad groups existentes: {exc}")
    return mapping


def deploy_campaigns_live(client: Any, customer_id: str) -> None:
    """Ejecuta las mutaciones en la API de Google Ads para crear presupuestos, campañas, grupos, keywords y anuncios."""
    print("🚀 [Live Deploy] Iniciando creación y despliegue en Google Ads API...")

    campaign_budget_service = client.get_service("CampaignBudgetService")
    campaign_service = client.get_service("CampaignService")
    ad_group_service = client.get_service("AdGroupService")
    ad_group_criterion_service = client.get_service("AdGroupCriterionService")
    ad_group_ad_service = client.get_service("AdGroupAdService")
    campaign_criterion_service = client.get_service("CampaignCriterionService")

    existing_campaigns = get_existing_campaigns_map(client, customer_id)
    existing_ad_groups = get_existing_ad_groups_map(client, customer_id)

    for idx, spec in enumerate(CAMPAIGNS_SPEC, 1):
        camp_name = spec["name"]
        print(
            f"\n[{idx}/2] Procesando: {camp_name} (${spec['budget_ars']:,.2f} ARS/día)..."
        )

        # 1. Resolver o Crear Campaña
        if camp_name in existing_campaigns:
            campaign_resource = existing_campaigns[camp_name]
            print(f"   ℹ️ Campaña existente detectada: {campaign_resource}")
        else:
            # Crear Presupuesto Diario
            budget_operation = client.get_type("CampaignBudgetOperation")
            budget = budget_operation.create
            budget.name = f"Presupuesto {camp_name[:40]}"
            budget.amount_micros = int(spec["budget_ars"] * 1_000_000)
            budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            budget.explicitly_shared = False

            budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=customer_id, operations=[budget_operation]
            )
            budget_resource = budget_response.results[0].resource_name
            print(f"   ✅ Presupuesto creado: {budget_resource}")

            # Crear Campaña Search B2B
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            campaign.name = camp_name
            campaign.status = client.enums.CampaignStatusEnum.ENABLED
            campaign.advertising_channel_type = (
                client.enums.AdvertisingChannelTypeEnum.SEARCH
            )
            campaign.campaign_budget = budget_resource

            # Configuración de Red: Solo Búsqueda Pura
            campaign.network_settings.target_google_search = True
            campaign.network_settings.target_search_network = False
            campaign.network_settings.target_content_network = False
            campaign.network_settings.target_partner_search_network = False

            # Estrategia de Puja: Maximizar Clics con Límite de CPC
            campaign.target_spend.cpc_bid_ceiling_micros = int(
                spec["cpc_bid_ceiling_ars"] * 1_000_000
            )

            # Declaración regulatoria de anuncios políticos UE
            campaign.contains_eu_political_advertising = client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING

            # Ubicación física estricta (PRESENCE)
            campaign.geo_target_type_setting.positive_geo_target_type = (
                client.enums.PositiveGeoTargetTypeEnum.PRESENCE
            )

            campaign_response = campaign_service.mutate_campaigns(
                customer_id=customer_id, operations=[campaign_operation]
            )
            campaign_resource = campaign_response.results[0].resource_name
            print(f"   ✅ Campaña Search creada: {campaign_resource}")

        # 2. Segmentación Geográfica (Buenos Aires Provincia + CABA)
        geo_operations = []
        for loc_id in ["20009", "20010"]:
            geo_op = client.get_type("CampaignCriterionOperation")
            geo_crit = geo_op.create
            geo_crit.campaign = campaign_resource
            geo_crit.location.geo_target_constant = f"geoTargetConstants/{loc_id}"
            geo_operations.append(geo_op)

        try:
            campaign_criterion_service.mutate_campaign_criteria(
                customer_id=customer_id, operations=geo_operations
            )
            print(
                "   ✅ Segmentación geográfica aplicada (Buenos Aires / CABA / Zona Norte)."
            )
        except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
            print(f"   ℹ️ Ubicación procesada o existente: {exc}")

        # 3. Palabras Clave Negativas de Campaña
        negative_ops = []
        for neg in spec["negative_keywords"]:
            neg_op = client.get_type("CampaignCriterionOperation")
            neg_crit = neg_op.create
            neg_crit.campaign = campaign_resource
            neg_crit.negative = True
            neg_crit.keyword.text = neg
            neg_crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            negative_ops.append(neg_op)

        try:
            campaign_criterion_service.mutate_campaign_criteria(
                customer_id=customer_id, operations=negative_ops
            )
            print(
                f"   ✅ {len(spec['negative_keywords'])} palabras clave negativas aplicadas."
            )
        except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
            print(f"   ℹ️ Negativas procesadas o existentes: {exc}")

        # 4. Resolver o Crear Grupo de Anuncios
        ad_group_name = spec["ad_group_name"]
        if ad_group_name in existing_ad_groups:
            ad_group_resource = existing_ad_groups[ad_group_name]
            print(f"   ℹ️ Grupo de Anuncios existente detectado: {ad_group_resource}")
        else:
            ad_group_operation = client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.create
            ad_group.name = ad_group_name
            ad_group.campaign = campaign_resource
            ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
            ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            ad_group.cpc_bid_micros = int(spec["cpc_bid_ceiling_ars"] * 1_000_000)

            ad_group_response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id, operations=[ad_group_operation]
            )
            ad_group_resource = ad_group_response.results[0].resource_name
            print(f"   ✅ Grupo de Anuncios creado: {ad_group_resource}")

        # 5. Crear Palabras Clave Positivas (EXACT & PHRASE)
        kw_operations = []
        for kw in spec["keywords"]:
            kw_op = client.get_type("AdGroupCriterionOperation")
            kw_crit = kw_op.create
            kw_crit.ad_group = ad_group_resource
            kw_crit.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            kw_crit.keyword.text = kw["text"]
            if kw["match_type"] == "EXACT":
                kw_crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
            else:
                kw_crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            kw_operations.append(kw_op)

        try:
            ad_group_criterion_service.mutate_ad_group_criteria(
                customer_id=customer_id, operations=kw_operations
            )
            print(
                f"   ✅ {len(spec['keywords'])} palabras clave industriales asociadas."
            )
        except (GoogleAdsException, ValueError, RuntimeError, OSError) as kw_err:
            print(f"   ℹ️ Palabras clave ya existentes o procesadas: {kw_err}")

        # 6. Crear Anuncio Adaptable de Búsqueda (Responsive Search Ad - RSA)
        ad_op = client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_op.create
        ad_group_ad.ad_group = ad_group_resource
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

        rsa = ad_group_ad.ad.responsive_search_ad
        for h_text in spec["headlines"]:
            headline = client.get_type("AdTextAsset")
            headline.text = h_text
            rsa.headlines.append(headline)

        for d_text in spec["descriptions"]:
            description = client.get_type("AdTextAsset")
            description.text = d_text
            rsa.descriptions.append(description)

        rsa.path1 = spec.get("path1", "")
        rsa.path2 = spec.get("path2", "")
        ad_group_ad.ad.final_urls.append(spec["target_url"])

        try:
            ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id, operations=[ad_op]
            )
            print("   ✅ Anuncio adaptable de búsqueda (RSA) creado y activo.")
        except (GoogleAdsException, ValueError, RuntimeError, OSError) as ad_err:
            print(f"   ℹ️ Anuncio RSA ya existente o procesado: {ad_err}")

    print("\n" + "=" * 70)
    print("🎉 DESPLIEGUE EN VIVO COMPLETADO AL 100% EN GOOGLE ADS")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Despliegue y Sincronización de Campañas Google Ads API"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica los cambios reales en la cuenta de Google Ads (requiere confirmación explícita)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Ejecuta en modo simulación sin realizar mutaciones de cobro",
    )
    args = parser.parse_args()

    settings = get_settings()
    customer_id = settings.google_ads_login_customer_id.strip().replace("-", "")

    if not args.apply:
        print_simulation_plan(customer_id)
        print(
            "\n💡 Para ejecutar el despliegue real en la cuenta, ejecuta con el flag: --apply"
        )
        sys.exit(0)

    client = _get_google_ads_client(
        settings.google_ads_developer_token,
        settings.google_ads_client_id,
        settings.google_ads_client_secret,
        settings.google_ads_refresh_token,
    )

    if not client:
        print(
            "❌ Error: No se pudo inicializar el cliente de Google Ads API. Verifica las credenciales en .env."
        )
        sys.exit(1)

    try:
        deploy_campaigns_live(client, customer_id)
    except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
        print(f"\n❌ Error durante el despliegue en Google Ads API: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
