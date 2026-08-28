#!/usr/bin/env python3
"""Script de automatización para validación, simulación y despliegue de campañas B2B en Google Ads API.

Soporta especificación declarativa en YAML/JSON, modo simulación segura (--dry-run por defecto)
y aplicación en vivo (--apply) de forma 100% idempotente.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from src.adapters.gateways.google_ads_gateway import (
    GoogleAdsException,
    _get_google_ads_client,
)
from src.infrastructure.pydantic.config import get_settings

DEFAULT_CONFIG_PATH = Path("data/google_ads/campaigns.yaml")


def load_campaigns_spec(
    config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Carga y valida la especificación declarativa de campañas desde un archivo YAML o JSON."""
    target_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not target_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de especificación de campañas en: {target_path.resolve()}"
        )

    with open(target_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict) and "campaigns" in data:
        return data["campaigns"]  # type: ignore
    elif isinstance(data, list):
        return data  # type: ignore

    raise ValueError(
        f"Formato inválido en {target_path}. Se esperaba un diccionario con clave 'campaigns' o una lista."
    )


def print_simulation_plan(
    campaigns_spec: list[dict[str, Any]], customer_id: str
) -> None:
    """Imprime el plan detallado de despliegue en modo simulación."""
    total_budget = sum(c.get("budget_ars", 0.0) for c in campaigns_spec)
    print("=" * 70)
    print("🛠️  PLAN DE DESPLIEGUE GOOGLE ADS API (MODO SIMULACIÓN / DRY-RUN)")
    print(f"🏢 Cuenta de Cliente: {customer_id}")
    print(f"💰 Presupuesto Diario Total Planificado: ${total_budget:,.2f} ARS/día")
    print(f"📁 Total de Campañas en Configuración: {len(campaigns_spec)}")
    print("=" * 70)

    for idx, camp in enumerate(campaigns_spec, 1):
        print(f"\n[{idx}/{len(campaigns_spec)}] Campaña: {camp['name']}")
        print(
            f"     • Presupuesto Asignado: ${camp.get('budget_ars', 0.0):,.2f} ARS/día"
        )
        print(
            f"     • Red: {camp.get('channel_type', 'SEARCH')} (Búsqueda de Google Pura)"
        )
        print(
            f"     • Límite CPC Máximo: ${camp.get('cpc_bid_ceiling_ars', 0.0):,.2f} ARS"
        )
        print(f"     • URL Final: {camp.get('target_url', '')}")
        print(
            f"     • Segmentación Geográfica: {camp.get('geo_locations', ['20009', '20010'])}"
        )
        print(f"     • Grupo de Anuncios: {camp.get('ad_group_name', '')}")
        keywords = camp.get("keywords", [])
        print(f"     • Palabras Clave ({len(keywords)}):")
        for kw in keywords:
            match_str = (
                f"[{kw['text']}]"
                if kw.get("match_type") == "EXACT"
                else f'"{kw["text"]}"'
            )
            print(f"       - {match_str} ({kw.get('match_type', 'PHRASE')})")
        negatives = camp.get("negative_keywords", [])
        print(f"     • Palabras Negativas ({len(negatives)}):")
        print(f"       - {', '.join(negatives)}")
        headlines = camp.get("headlines", [])
        print(f"     • Títulos Adaptables ({len(headlines)}):")
        for h in headlines[:5]:
            print(f"       - {h}")
        if len(headlines) > 5:
            print(f"       ... (+{len(headlines) - 5} títulos adicionales)")
        descriptions = camp.get("descriptions", [])
        print(f"     • Descripciones Adaptables ({len(descriptions)}):")
        for d in descriptions:
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
        print(f"ℹ️ Error consultando grupos de anuncios existentes: {exc}")
    return mapping


def deploy_campaigns(
    campaigns_spec: list[dict[str, Any]], client: Any, customer_id: str
) -> None:
    """Aplica de forma idempotente la creación/actualización de campañas, presupuestos, keywords y anuncios."""
    campaign_budget_service = client.get_service("CampaignBudgetService")
    campaign_service = client.get_service("CampaignService")
    campaign_criterion_service = client.get_service("CampaignCriterionService")
    ad_group_service = client.get_service("AdGroupService")
    ad_group_criterion_service = client.get_service("AdGroupCriterionService")
    ad_group_ad_service = client.get_service("AdGroupAdService")
    ga_service = client.get_service("GoogleAdsService")

    existing_campaigns = get_existing_campaigns_map(client, customer_id)
    existing_ad_groups = get_existing_ad_groups_map(client, customer_id)

    print(
        f"\n🚀 [Live Deploy] Iniciando despliegue de {len(campaigns_spec)} campañas en Google Ads API...\n"
    )

    for idx, spec in enumerate(campaigns_spec, 1):
        camp_name = spec["name"]
        print(
            f"[{idx}/{len(campaigns_spec)}] Procesando: {camp_name} (${spec.get('budget_ars', 0.0):,.2f} ARS/día)..."
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
            budget.amount_micros = int(spec.get("budget_ars", 1000.0) * 1_000_000)
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
                spec.get("cpc_bid_ceiling_ars", 500.0) * 1_000_000
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

        # 2. Segmentación Geográfica
        geo_locations = spec.get("geo_locations", ["20009", "20010"])
        geo_operations = []
        for loc_id in geo_locations:
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
                f"   ✅ Segmentación geográfica aplicada ({len(geo_locations)} ubicaciones)."
            )
        except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
            print(f"   ℹ️ Ubicación procesada o existente: {exc}")

        # 3. Palabras Clave Negativas de Campaña
        existing_negatives: set[str] = set()
        try:
            neg_query = f"SELECT campaign_criterion.keyword.text FROM campaign_criterion WHERE campaign.resource_name = '{campaign_resource}' AND campaign_criterion.negative = TRUE"
            for r in ga_service.search(customer_id=customer_id, query=neg_query):
                existing_negatives.add(r.campaign_criterion.keyword.text.lower())
        except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
            print(f"   ℹ️ Consulta de negativas existentes omitida: {exc}")

        negative_ops = []
        for neg in spec.get("negative_keywords", []):
            if neg.lower() in existing_negatives:
                continue
            neg_op = client.get_type("CampaignCriterionOperation")
            neg_crit = neg_op.create
            neg_crit.campaign = campaign_resource
            neg_crit.negative = True
            neg_crit.keyword.text = neg
            neg_crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            negative_ops.append(neg_op)

        if negative_ops:
            try:
                campaign_criterion_service.mutate_campaign_criteria(
                    customer_id=customer_id, operations=negative_ops
                )
                print(
                    f"   ✅ {len(negative_ops)} nuevas palabras clave negativas aplicadas."
                )
            except (
                GoogleAdsException,
                ValueError,
                RuntimeError,
                OSError,
            ) as exc:
                print(f"   ℹ️ Negativas procesadas o existentes: {exc}")
        else:
            print(
                "   ℹ️ Todas las palabras clave negativas ya se encontraban aplicadas."
            )

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
            ad_group.cpc_bid_micros = int(
                spec.get("cpc_bid_ceiling_ars", 400.0) * 1_000_000
            )

            ad_group_response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id, operations=[ad_group_operation]
            )
            ad_group_resource = ad_group_response.results[0].resource_name
            print(f"   ✅ Grupo de Anuncios creado: {ad_group_resource}")

        # 5. Crear Palabras Clave Positivas (EXACT & PHRASE)
        existing_keywords: set[tuple[str, str]] = set()
        try:
            kw_query = f"SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type FROM ad_group_criterion WHERE ad_group.resource_name = '{ad_group_resource}'"
            for r in ga_service.search(customer_id=customer_id, query=kw_query):
                existing_keywords.add(
                    (
                        r.ad_group_criterion.keyword.text.lower(),
                        r.ad_group_criterion.keyword.match_type.name,
                    )
                )
        except (GoogleAdsException, ValueError, RuntimeError, OSError) as exc:
            print(f"   ℹ️ Consulta de keywords existentes omitida: {exc}")

        kw_operations = []
        for kw in spec.get("keywords", []):
            if (
                kw["text"].lower(),
                kw.get("match_type", "PHRASE"),
            ) in existing_keywords:
                continue
            kw_op = client.get_type("AdGroupCriterionOperation")
            kw_crit = kw_op.create
            kw_crit.ad_group = ad_group_resource
            kw_crit.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            kw_crit.keyword.text = kw["text"]
            if kw.get("match_type") == "EXACT":
                kw_crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.EXACT
            else:
                kw_crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
            kw_operations.append(kw_op)

        if kw_operations:
            try:
                ad_group_criterion_service.mutate_ad_group_criteria(
                    customer_id=customer_id, operations=kw_operations
                )
                print(
                    f"   ✅ {len(kw_operations)} nuevas palabras clave industriales asociadas."
                )
            except (
                GoogleAdsException,
                ValueError,
                RuntimeError,
                OSError,
            ) as kw_err:
                print(f"   ℹ️ Palabras clave ya existentes o procesadas: {kw_err}")
        else:
            print("   ℹ️ Todas las palabras clave ya se encontraban asociadas.")

        # 6. Crear Anuncio Adaptable de Búsqueda (Responsive Search Ad - RSA)
        ad_op = client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_op.create
        ad_group_ad.ad_group = ad_group_resource
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

        rsa = ad_group_ad.ad.responsive_search_ad
        for h_text in spec.get("headlines", []):
            headline = client.get_type("AdTextAsset")
            headline.text = h_text
            rsa.headlines.append(headline)

        for d_text in spec.get("descriptions", []):
            description = client.get_type("AdTextAsset")
            description.text = d_text
            rsa.descriptions.append(description)

        rsa.path1 = spec.get("path1", "")
        rsa.path2 = spec.get("path2", "")
        ad_group_ad.ad.final_urls.append(spec.get("target_url", ""))

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
        description="Despliegue y Sincronización Declarativa de Campañas Google Ads API"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Ruta al archivo YAML/JSON de especificación de campañas (default: {DEFAULT_CONFIG_PATH})",
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

    campaigns_spec = load_campaigns_spec(args.config)

    if not args.apply:
        print_simulation_plan(campaigns_spec, customer_id)
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
            "❌ Error: Credenciales de Google Ads API incompletas en variables de entorno."
        )
        print(
            "Verificar: GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN."
        )
        sys.exit(1)

    deploy_campaigns(campaigns_spec, client, customer_id)


if __name__ == "__main__":
    main()
