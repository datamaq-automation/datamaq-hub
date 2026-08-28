# Spec: Servidores FastMCP de Analítica, Telemetría & Watchdog (DataMaq Hub)

> **Subsistema:** Integración FastMCP, Google Ads, GA4, Microsoft Clarity y Watchdog  
> **Estado:** Implementado / Aprobado (Google Ads Basic Access Activo)  
> **Módulos:** `src/adapters/gateways`, `src/infrastructure/fastmcp`, `scripts/`  

---

## 1. Objetivo y Contexto

El subsistema de analítica y FastMCP de `datamaq-hub` expone herramientas estandarizadas mediante el **Model Context Protocol (MCP)** para permitir que agentes autónomos de IA y scripts de monitoreo auditen el rendimiento de marketing digital, la experiencia de usuario (UX) y el gasto publicitario de DataMaq sin intervención manual.

---

## 2. Componentes y Servidores FastMCP

### 2.1 Google Ads FastMCP (`scripts/mcp_google_ads_server.py`)
- **Adaptador:** `src/adapters/gateways/google_ads_gateway.py`
- **Herramientas Expuestas:**
  - `get_google_ads_status()`: Estado de credenciales, Developer Token (`Basic Access activo`) y cuenta de cliente (`405-777-8237`).
  - `get_campaign_performance(days: int = 7)`: Impresiones, clics, costo en ARS, conversiones y CPC medio por campaña con GAQL dinámico (`TODAY`, `LAST_7_DAYS`, `LAST_30_DAYS`).
  - `get_search_terms_report(days: int = 7, limit: int = 20)`: Términos reales de búsqueda que dispararon anuncios.
  - `get_daily_budget_pacing()`: Gasto del día actual vs límite estricto de seguridad (**$1.500 ARS/día**).

### 2.2 Google Analytics 4 FastMCP (`scripts/mcp_ga4_server.py`)
- **Adaptador:** `src/adapters/gateways/ga4_gateway.py`
- **Herramientas Expuestas:**
  - `get_ga4_status()`: Validación de la Service Account en GCP (`datamaq-ga4-key.json`) y Property ID (`533265197`).
  - `get_ga4_top_pages(days: int = 7, limit: int = 10, segment: str = "all")`: Páginas más visitadas y vistas activas.
  - `get_ga4_traffic_sources(days: int = 7, limit: int = 10)`: Desglose por fuente, medio y campaña UTM.
  - `get_ga4_geo_traffic(days: int = 7, limit: int = 15)`: Ciudades y regiones geográficas de origen.
  - `get_ga4_conversions(days: int = 7)`: Eventos clave (`whatsapp_click`, `direct_contact`, `page_view`, etc.).

### 2.3 Microsoft Clarity FastMCP (`scripts/mcp_clarity_server.py`)
- **Adaptador:** `src/adapters/gateways/clarity_gateway.py`
- **Herramientas Expuestas:**
  - `get_clarity_project_info()`: Información del proyecto `wx5hfvmv5y` y URLs directas.
  - `get_live_insights()`: Métricas agregadas de comportamiento (dead clicks, rage clicks, scroll depth).
  - `get_dashboard_insights(num_of_days: int = 3)`: Resumen de comportamiento de los últimos N días.
  - `get_intent_recording_urls()`: Enlaces web directos con filtros de Custom Tags (`lead_intent:email_click`, `lead_intent:whatsapp_click`, `lead_intent:form_submit`).
  - `get_recording_url(filter_tag: str = "")`: Generador de enlaces parametrizados.

### 2.4 Analytics Digest & Guardrails FastMCP (`src/infrastructure/fastmcp/analytics_digest.py`)
- **Adaptador / Use Cases:** `src/application/use_cases/generar_analytics_digest.py`, `src/application/use_cases/validar_accion_marketing.py`
- **Herramientas Expuestas:**
  - `get_analytics_digest(days: int = 1)`: Retorna el resumen consolidado pre-procesado, KPIs calculados (CTR, CPC, CPA, Pacing), lista de anomalías y enlaces a grabaciones de intención (reducción del 95% de tokens para OpenClaw).
  - `validate_marketing_action(action_type: str, params: dict | None)`: Valida determinísticamente que una acción propuesta por un agente cumpla con los límites estrictos de seguridad ($1.500 ARS/día, CPC máximo acotado).

---

## 3. Endpoints REST de la API (`/api/v1/analytics`)

- `GET /api/v1/analytics/digest`: Snapshot consolidado y enriquecido con detección determinística de anomalías.
- `POST /api/v1/analytics/actions/validate`: Guardrails duros de post-procesamiento para acciones de agentes.
- `GET /api/v1/analytics/summary`: Resumen de telemetría multi-fuente.
- `GET /api/v1/analytics/ads/pacing`: Auditoría de presupuesto acumulado.
- `GET /api/v1/analytics/ads/campaigns`: Rendimiento por campaña.
- `GET /api/v1/analytics/ads/search-terms`: Búsquedas reales de usuarios.
- `GET /api/v1/analytics/ga4/conversions`: Eventos de conversión web.
- `GET /api/v1/analytics/clarity/live`: Grabaciones de UX y live insights.

---

## 4. Watchdog & Alerting en Background (`scripts/analytics_watchdog.py`)

- Script CLI/cron desacoplado que orquesta `GenerarAnalyticsDigestUseCase`.
- Monitorea diariamente el pacing de Ads ($1.500 ARS/día), conversiones en GA4 y usuarios de Clarity con matemática exacta y detección de anomalías.
- Formatea un informe ejecutivo en Markdown y lo envía a Telegram si `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` están configurados.
- Soporta flags `--dry-run`, `--json`, `--budget-limit`.

