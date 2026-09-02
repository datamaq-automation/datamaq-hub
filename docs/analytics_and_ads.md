# Guía y SSOT de Gobernanza Analítica, Google Ads, GA4, Clarity & MCPs — DataMaq

> **Proyecto:** DataMaq (`datamaq.com.ar`)  
> **Estado:** Documento Vivo (Living SSOT de Telemetría, Campañas & Analítica)  
> **Ámbito:** Gobernanza de cuentas Google, Google Ads API (**Basic Access Aprobado**), GA4, Microsoft Clarity, Servidores FastMCP y Automatización de Despliegues.  

---

## 1. Topología y Gobernanza de Cuentas

DataMaq opera con una separación clara de responsabilidades entre la cuenta de infraestructura técnica y la cuenta institucional comercial:

```
┌────────────────────────────────────────────────────────┐
│   🛠️ CONSOLA DE DESARROLLO (Google Cloud / GCP)       │
│                                                        │
│   • Cuenta: agustin.deoz@gmail.com                     │
│   • Proyecto GCP: 395333970129                         │
│   • Pantalla OAuth2 & Service Accounts                 │
└───────────────────────────┬────────────────────────────┘
                            │ (Credenciales & Tokens)
                            ▼
┌────────────────────────────────────────────────────────┐
│   🔗 VINCULACIÓN & ACCESOS CRUZADOS                    │
│                                                        │
│   1. Service Account GA4: ga4-analytics-reader...      │
│   2. Developer Token Aprobado: ETBq93xk... (Basic)     │
│   3. Propiedad GA4: 533265197 (Lector / Admin)         │
└───────────────────────────┬────────────────────────────┘
                            │ (Telemetría & Publicidad)
                            ▼
┌────────────────────────────────────────────────────────┐
│   💼 ENTORNO DE NEGOCIO & PUBLICIDAD                   │
│                                                        │
│   • Cuenta: contacto.datamaq@gmail.com                 │
│   • Google Ads ID: 405-777-8237 (ENABLED / SERVING)    │
│   • Microsoft Clarity ID: wx5hfvmv5y                   │
└────────────────────────────────────────────────────────┘
```

### Matriz de Permisos y Accesos Cruzados

| Servicio / Consola | Cuenta Propietaria | Identificador / Recurso | Rol Asignado & Estado |
|---|---|---|---|
| **Google Cloud Console (GCP)** | `agustin.deoz@gmail.com` | Proyecto: `395333970129` | Owner / OAuth2 Pantalla Activa |
| **Google Ads (`405-777-8237`)** | `contacto.datamaq@gmail.com` | Cuenta de Anuncios | **Basic Access APROBADO (15k ops/día)** |
| **Google Ads MCC (`131-878-0733`)** | `agustin.deoz@gmail.com` | Administrador MCC | Propietario del Developer Token `ETBq...` |
| **Google Analytics 4** | `contacto.datamaq@gmail.com` | Propiedad `533265197` | Service Account con rol Lector |
| **Microsoft Clarity** | `contacto.datamaq@gmail.com` | Proyecto `wx5hfvmv5y` | Administrador con Custom Tags (`lead_intent`) |
| **Google Search Console** | `contacto.datamaq@gmail.com` | `sc-domain:datamaq.com.ar` | Activación en curso (API + Service Account) |

---

## 2. Mapa Completo de Variables de Entorno (`.env`)

```ini
# ==============================================================================
# 1. FRONTEND / TRACKING EN PRODUCCIÓN (VPS DonWeb)
# ==============================================================================
GOOGLE_ANALYTICS_ID=G-ME5FC58TFL
GOOGLE_ADS_ID=AW-17968350814
GOOGLE_ADS_CONVERSION_ID=AW-17968350814/aMtOCJ3ert0cEN6M_fdC
GOOGLE_ADS_WHATSAPP_CONVERSION_ID=AW-17968350814/n-vPCJear90cEN6M_fdC
CLARITY_ID=wx5hfvmv5y
BASE_URL=https://datamaq.com.ar
APP_DATAMAQ_URL=https://app.datamaq.com.ar
DEBUG=False

# ==============================================================================
# 2. CONTACTO Y WHATSAPP DINÁMICO
# ==============================================================================
WHATSAPP_PHONE=541156297160
WHATSAPP_MESSAGE="Hola! Vi tu sitio datamaq.com.ar y quería consultarte sobre servicios de mantenimiento eléctrico industrial."

# ==============================================================================
# 3. NOTIFICACIONES & ALERTAS (TELEGRAM + EMAIL)
# ==============================================================================
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USERNAME=no-reply@datamaq.com.ar
SMTP_PASSWORD=your_smtp_password
NOTIFICATION_EMAIL=agustin@datamaq.com.ar

# ==============================================================================
# 4. BASE DE DATOS MySQL (LEADS & CACHÉ)
# ==============================================================================
DATABASE_URL=mysql+aiomysql://datamaq_leads:your_password@127.0.0.1:3306/datamaq_leads

# ==============================================================================
# 5. WATCHDOG DE OPERACIONES & ALERTAS
# ==============================================================================
WATCHDOG_BASE_URL=http://127.0.0.1:8001
WATCHDOG_CONSECUTIVE_FAILURES_REQUIRED=2

# ==============================================================================
# 6. CREDENCIALES MCP / GOOGLE ADS API (BASIC ACCESS APROBADO)
# ==============================================================================
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_oauth_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_oauth_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_oauth_refresh_token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=405-777-8237

# ==============================================================================
# 7. CREDENCIALES MCP / GOOGLE ANALYTICS 4 DATA API
# ==============================================================================
GOOGLE_APPLICATION_CREDENTIALS=/home/datamaq/.config/gcp/datamaq-ga4-key.json
GA4_PROPERTY_ID=533265197

# ==============================================================================
# 8. CREDENCIALES MCP / MICROSOFT CLARITY EXPORT API
# ==============================================================================
CLARITY_API_TOKEN=your_clarity_export_api_jwt_token
```

---

## 3. Estrategia de Campañas Google Ads (Etapa 2 — Búsqueda B2B Priorizada)

* **Presupuesto Total Diario:** **$1.500 ARS/día** (~$45.000 ARS/mes, configurable en `.env` vía `GOOGLE_ADS_DAILY_BUDGET_LIMIT_ARS`).
* **Estrategia de Puja:** Maximizar Clics con Techo de CPC Controlado a **$650 ARS**.
* **Red:** Red de Búsqueda de Google Únicamente (*Display y Socios Desactivados*).
* **Segmentación Geográfica:** AMBA & GBA Norte (Pilar, Garín, Tigre, Campana, San Martín, Vicente López, San Fernando, Malvinas Argentinas) con presencia física estricta (`PRESENCE`).
* **Horario de Publicación:** Lunes a Viernes de 07:30 a 17:30 hs.

```
Presupuesto Total: $1.500 ARS/día (Límite Inviolable)
├── 🥇 CAMPAÑA 1 (FOCO PRINCIPAL - 80%): $1.200 ARS/día → Calidad de Energía & Cero Multas Edenor (cos φ)
└── 🥈 CAMPAÑA 2 (SOPORTE - 20%):         $300 ARS/día   → Telemetría & Bajada de Datos OT a PC (Retrofit IoT)
```

---

### 🥇 CAMPAÑA 1 (FOCO PRINCIPAL): "Calidad de Energia — Cero Multas Edenor cos fi"

* **Presupuesto Asignado:** **$1.200 ARS/día** (Límite CPC: **$650 ARS**).
* **URL de Destino:** `https://datamaq.com.ar/?utm_source=google_ads&utm_medium=cpc&utm_campaign=calidad-energia#servicios`
* **Ruta visible:** `datamaq.com.ar/cero-multas/energia`

#### Palabras Clave de Intención Técnica y Búsqueda:
```text
"banco de capacitores trifasico"
"bancos de capacitores automaticos"
"multa factor de potencia edenor"
"correccion factor de potencia industrial"
"analizador de redes trifasico medicion"
"recargo reactiva edenor t3"
"mantenimiento banco de capacitores"
"banco de capacitores pilar"
"banco de capacitores garin"
"banco de capacitores"
"bancos de capacitores industriales"
"mantenimiento electrico industrial"
"tableros electricos industriales"
"medicion de factor de potencia"
"analisis de calidad de energia"
"compensacion de reactiva"
"calculo de capacitores para factor de potencia"
"como corregir el factor de potencia"
"como funciona un banco de capacitores"
"calculo banco de capacitores industrial"
"solucion multa factor de potencia edenor"
"compensacion reactiva industrial pyme"
[multa cos fi edenor]
[banco de capacitores industrial trifasico]
[recargo factor de potencia edenor t3]
[correccion factor de potencia]
[multa edenor factor de potencia]
```

#### Títulos de Anuncio Adaptable (Autoridad Técnica y Resolución):
1. `¿Multas cos fi en Edenor?` (25 car.)
2. `Cálculo Banco Capacitores` (24 car.)
3. `Cómo Corregir Reactiva` (21 car.)
4. `Diagnóstico en Planta 48hs` (26 car.)
5. `Ingenieros en Zona Norte` (23 car.)
6. `Medición con Powermeter` (22 car.)
7. `Elimine Penalidad Edenor` (23 car.)
8. `DataMaq Eficiencia Pyme` (22 car.)
9. `Atención en Pilar y Garín` (24 car.)
10. `Diagnóstico 100% Deducible` (26 car.)
11. `Banco de Capacitores` (20 car.)
12. `Factor de Potencia en 48hs` (25 car.)
13. `Atención Directa en Planta` (26 car.)
14. `Evite Recargos en Factura` (24 car.)
15. `Compensación de Reactiva` (24 car.)

#### Descripciones de Anuncio Adaptable:
1. `Elimine multas por factor de potencia en Edenor. Diagnóstico deducible 100% en planta.`
2. `Diagnóstico en planta en Zona Norte. Medición con analizador y solución en 48hs.`
3. `Evite penalidades millonarias. Financiación en cuotas y descuento Banco Provincia.`
4. `Instalación llave en mano de hardware Powermeter y telemetría de por vida.`

#### Extensiones de Anuncio (Assets Vinculados):
* **Sitelinks**:
  - *Diagnóstico en Planta*: `/contact` (Medición con analizador de redes en fábrica)
  - *Compensación cos fi*: `/#servicios` (Bancos automáticos trifásicos)
  - *Telemetría Industrial*: `/datos/maquinas` (Bajada de datos OT a PC)
* **Callouts**:
  - `Atención en Planta 48hs`
  - `Zona Norte: Pilar y Garín`
  - `Ingenieros Especialistas`
  - `Sin Abonos Mensuales`

---

### 🥈 CAMPAÑA 2 (SOPORTE): "Telemetria y Adquisicion de Datos — Retrofit IoT"

* **Presupuesto Asignado:** **$300 ARS/día** (Límite CPC: **$650 ARS**).
* **URL de Destino:** `https://datamaq.com.ar/?utm_source=google_ads&utm_medium=cpc&utm_campaign=retrofit-iot#servicios`
* **Ruta visible:** `datamaq.com.ar/datos/maquinas`

#### Palabras Clave:
```text
"mantenimiento electrico industrial"
"programacion plc siemens"
"servicio de programacion plc"
"automatizacion industrial pilar"
"automatizacion industrial garin"
"armado de tableros electricos industriales"
"integrador plc argentina"
"bajada de datos linea de produccion"
"monitoreo de inyectoras de plastico"
"conteo de piezas produccion"
"automatizacion industrial"
"telemetria industrial"
"monitoreo de maquinas"
"sensores industriales"
"sistema scada industrial"
"tableros de control industrial"
"retrofit iot maquinas industriales"
[telemetria industrial]
[monitoreo de maquinas industriales]
[automatizacion industrial argentina]
```

#### Extensiones de Anuncio (Assets Vinculados):
* **Sitelinks**:
  - *Diagnóstico en Planta*: `/contact` (Relevamiento de líneas de planta)
  - *Cero Multas Edenor*: `/#servicios` (Compensación de factor de potencia)
* **Callouts**:
  - `Base de Datos 100% Local`
  - `Sin Licencias Mensuales`
  - `Zona Norte: Garín y Pilar`
  - `Soporte Técnico Directo`

---

### 🚫 Palabras Clave Negativas Compartidas (Blindaje Anti-Capacitación Estricto):
```text
-gratis -curso -cursos -capacitacion -capacitaciones -taller -facultad -estudiante -profesor -alumno -examen -tutorial -pdf -arduino -raspberry -tesis -universidad -empleo -sueldo -curriculum -manual -que es -monografia -wikipedia -pasantia -bolsa de trabajo -salario -ejemplos
```

---

## 4. Servidores FastMCP & Watchdog en `datamaq-hub`

El Hub expone 3 servidores FastMCP modulares con caché persistente y fallback automático en memoria:

```
[ Agentes de IA / CLI / Watchdog ]
               │
      ┌────────┴────────┬────────────────┐
      ▼                 ▼                ▼
[ FastMCP Ads ]   [ FastMCP GA4 ]   [ FastMCP Clarity ]
      │                 │                │
      └────────┬────────┴────────────────┘
               ▼
   [ ApiCacheGateway (MySQL / In-Memory TTL) ]
```

### Herramientas Expuestas:
1. **Google Ads (`scripts/mcp_google_ads_server.py`):**
   - `get_google_ads_status()`: Validación de token y permisos de cuenta.
   - `get_campaign_performance(days=7)`: Impresiones, clics, costo ARS, conversiones y CPC.
   - `get_search_terms_report(days=7, limit=20)`: Búsquedas reales de usuarios para detectar nuevas negativas.
   - `get_daily_budget_pacing()`: Auditoría de gasto del día actual vs límite de $1.500 ARS.
2. **GA4 (`scripts/mcp_ga4_server.py`):**
   - `get_ga4_status()`: Estado de conexión con la propiedad `533265197`.
   - `get_ga4_top_pages(days=7, limit=10)`: Vistas de páginas y usuarios activos.
   - `get_ga4_traffic_sources(days=7, limit=10)`: Fuentes de tráfico (Direct, Organic, Ads, UTMs).
   - `get_ga4_geo_traffic(days=7, limit=15)`: Ciudades de origen (Garín, Olivos, Pilar, etc.).
   - `get_ga4_conversions(days=7)`: Eventos clave (`whatsapp_click`, `direct_contact`).
3. **Microsoft Clarity (`scripts/mcp_clarity_server.py`):**
   - `get_clarity_project_info()`: Info del proyecto y links directos.
   - `get_live_insights()`: Usuarios y métricas de fricción en tiempo real.
   - `get_intent_recording_urls()`: Enlaces web directos con filtros de Custom Tags:
     - `lead_intent:email_click`
     - `lead_intent:whatsapp_click`
     - `lead_intent:form_submit`

### 4.1 Motor Determinístico de Pre y Post Procesamiento (OpenClaw / Compound AI)

Para optimizar el consumo de la IA (**OpenClaw**) y garantizar 0% alucinación en métricas financieras y de tráfico, el backend implementa un pipeline determinístico bajo Clean Architecture (`src/domain/analytics/` y `src/application/use_cases/`):

1. **Pre-procesamiento (`GenerarAnalyticsDigestUseCase`):**
   - Ingesta multi-fuente transparente con caché persistente (`ApiCacheGateway`).
   - Cálculo exacto en Python de KPIs: CTR, CPC medio, CPA, tasa de conversión y pacing acumulado respecto al límite estricto de **$1.500 ARS/día**.
   - Detección automática de anomalías por reglas de negocio (`AnomalyDetectionService`): sobregasto, campañas activas sin impresiones, eventos de conversión registrados y consultas irrelevantes con desperdicio de clics.
   - Generación de un *Analytics Digest* ultra-compacto (reducción del 95% de tokens para OpenClaw) y resumen Markdown para alertas.
2. **Post-procesamiento & Guardrails (`ValidarAccionMarketingUseCase`):**
   - Evalúa de forma estricta cualquier propuesta de acción del agente (ej. ajustar presupuesto, variar CPC o agregar palabras negativas).
   - Bloquea físicamente cualquier intento de superar el presupuesto máximo de **$1.500 ARS/día** o un CPC mayor a **$500 ARS**.

---


## 5. Gobernanza de Conversión y Atribución B2B

El caso de **JTEKT Automotive** demostró que los compradores industriales combinan múltiples puntos de contacto: descubrimiento web en Zona Norte, consulta de servicios y contacto formal vía correo institucional (`info@datamaq.com.ar`).

| Tipo de Conversión | Canal de Captura | Destino de Alerta | Registro en DB | Atribución First-Touch |
|---|---|---|---|---|
| **Formulario Multi-Paso** | Web (`/contact`) | Telegram + Email + GA4 + Ads | MySQL (`Lead`) | Sí (30 días localStorage) |
| **Clic en WhatsApp** | Web (`wa.me` / FAB) | Telegram + GA4 + Ads | MySQL (`Lead`) | Sí (30 días localStorage) |
| **Clic en Email / Teléfono** | Web (`mailto:` / `tel:`) | Telegram + GA4 + Clarity | MySQL (`Lead`) | Sí (30 días localStorage) |
| **Copia de Email / Tel** | Web (Portapapeles) | Telegram + GA4 + Clarity | MySQL (`Lead`) | Sí (30 días localStorage) |
| **Envío Directo Outlook** | Cliente Externo | Buzón `info@datamaq.com.ar` | Manual / CRM | Correlación por IP/Geo/Hora |

---

## 6. Comandos de Verificación & Automatización

- **Verificación completa de métricas de MCP:**
  ```bash
  PYTHONPATH=. ./venv/bin/python scripts/check_mcp_metrics.py
  ```
- **Ejecución del Watchdog diario (Dry-Run / Live Telegram):**
  ```bash
  PYTHONPATH=. ./venv/bin/python scripts/analytics_watchdog.py
  ```
- **Despliegue y Sincronización de Campañas Google Ads (Dry-Run por defecto):**
  ```bash
  PYTHONPATH=. ./venv/bin/python scripts/deploy_google_ads_campaigns.py --dry-run
  ```
