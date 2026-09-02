# Spec: Servidor FastMCP de Google Business Profile (DataMaq Hub)

> **Subsistema:** Integración con la ficha de Google Business Profile (paquete local de Maps)
> **Estado:** Implementado / Pendiente de habilitación (requiere Basic API Access aprobado)
> **Módulos:** `src/domain/analytics`, `src/adapters/gateways`, `src/application/use_cases`, `src/infrastructure/fastmcp`, `scripts/`

---

## 1. Objetivo y Contexto

### 1.1 Alcance

Cuarto vertical de analítica del hub, junto a Google Ads, GA4 y Microsoft Clarity. Cubre la única fuente que mide el **paquete local de Maps**: impresiones y acciones sobre la ficha, términos de búsqueda con los que aparece, reseñas, y las dos escrituras que la Fase 4 del plan de posicionamiento local necesita automatizar — publicaciones semanales y respuestas a reseñas.

El plan de referencia es `docs/fase4_google_business_profile.md` del repositorio `www-datamaq`: §6 (calendario de publicaciones), §8 (reseñas), §9 (medición) y §10 (errores a evitar) son los que se traducen a código acá.

### 1.2 Límites

- **La ficha no es fuente de verdad del NAP.** `data/config/brand.yaml` de `www-datamaq` lo es (§3 del plan). Por eso **no se expone ninguna herramienta de mutación de la location** (`locations.patch`): cambiar nombre o dirección desde el hub sería, además, causal de suspensión de la ficha.
- El corte **descubrimiento vs. marca** que pide §9 ya no existe en la API (murió con la Insights API v4). Se aproxima clasificando términos que contienen la marca contra el resto.
- Fotos (§5) y configuración inicial de la ficha (§11) siguen siendo trabajo manual en la UI.

### 1.3 Decisión de arquitectura

Google no publica SDK de Python para estas APIs y el repositorio no tiene `google-api-python-client`. Se usa el patrón REST sobre `urllib` + canje de `refresh_token` ya presente en `gmail_api_gateway.py`, sin sumar dependencias. A diferencia de aquel, el gateway de GBP **nunca propaga excepciones**: devuelve dicts con discriminante `status`, que es la convención del resto de los gateways de analítica.

El vertical vive dentro de `src/domain/analytics/` y no en una temática propia, porque comparte `AnomalyAlert`, `AnomalyType` y `AnomalySeverity` con el digest consolidado.

---

## 2. Dominio & Puertos

**Puerto** (`src/domain/analytics/ports.py`): `GoogleBusinessProfileDataSourcePort` (Protocol), espejo 1:1 del gateway.

**Entidades** (`src/domain/analytics/entities.py`):
- `MetricaFicha` — valor diario de una métrica.
- `ResenaFicha` — reseña con `estrellas` y `tiene_respuesta`.
- `TerminoBusquedaFicha` — término con `es_de_marca`.
- `MarketingSnapshot` se amplía con `ficha_resumen`, `ficha_metricas`, `ficha_resenas` y `ficha_terminos`.

**Value Objects** (`src/domain/analytics/value_objects.py`): `ResumenFicha` (totales por eje + variación contra el período previo); nuevos miembros de `AnomalyType` (`FICHA_*`) y de `MarketingActionType` (`GBP_CREATE_POST`, `GBP_REPLY_REVIEW`).

**Servicio** (`src/domain/analytics/services.py`): `FichaLocalAnalysisService` con `resumir_metricas`, `clasificar_terminos` y `detectar_anomalias`. `MarketingActionGuardrailService` se extiende con `_validar_publicacion_ficha` y `_validar_respuesta_resena`.

**Excepciones**: `FichaGoogleException` y sus derivadas `PublicacionFichaInvalidaException` y `RespuestaResenaInvalidaException`.

### 2.1 Reglas de anomalía

| Regla | Severidad | Origen |
|---|---|---|
| Impresiones caen ≥25% contra el período previo | `warning` | §9 |
| Hay reseñas sin responder | `warning` | §8 (la tasa de respuesta es en sí misma señal) |
| Menos de 5 reseñas | `info` | §8 (piso competitivo del paquete local) |
| Rating promedio < 4.0 | `critical` | §8 |
| Más de 14 días sin publicar | `warning` | §10 ("publicar y abandonar") |

### 2.2 Guardrails de escritura

| Regla | Excepción |
|---|---|
| Publicación no vacía y ≤1500 caracteres | `PublicacionFichaInvalidaException` |
| `cta_url` con esquema `https` y host `datamaq.com.ar` | idem |
| `cta_url` con `utm_campaign=gbp` (§7, atribución en GA4) | idem |
| `cta_type` dentro del enum de la API | idem |
| `schedule_time` en RFC3339 | idem |
| Respuesta no vacía y ≤4096 caracteres | `RespuestaResenaInvalidaException` |
| No pisar una respuesta existente sin `overwrite=True` | idem |

---

## 3. Casos de Uso & DTOs

- **`GenerarAnalyticsDigestUseCase`** recibe un cuarto puerto **opcional** `gbp_port`. Lee la ficha sobre una ventana mínima de 28 días (`FICHA_DIAS_MINIMOS`) aunque el digest pida 1 día, porque la serie llega con retraso. Degrada a vacío ante cualquier `status` distinto de `success`.
- **`PublicarEnFichaGoogleUseCase`** (`src/application/use_cases/publicar_en_ficha_google.py`) es el único punto de escritura. Aplica los guardrails **antes** de tocar la red. Para responder una reseña consulta primero su estado real en la ficha, de modo que la regla de sobrescritura se evalúe contra Google y no contra lo que el agente afirme.
- **`ValidarAccionMarketingUseCase`** cubre las dos acciones nuevas sin cambios: el enum y el servicio de guardrails ya las contemplan.

**DTOs** (`src/application/dtos/analytics_dtos.py`): `ResumenFichaDTO`, `ResenaFichaDTO`, `TerminoBusquedaFichaDTO`, `GbpPostRequestDTO`, `GbpReviewReplyRequestDTO`; `AnalyticsDigestResponseDTO` suma `ficha_resumen`, `ficha_resenas` y `ficha_terminos`.

---

## 4. Servidor FastMCP

**Entrypoint:** `scripts/mcp_gbp_server.py` — `FastMCP("DataMaq Google Business Profile MCP")`
**Adaptador:** `src/infrastructure/fastmcp/gbp.py`
**Gateway:** `src/adapters/gateways/gbp_gateway.py`

| Herramienta | API | Endpoint |
|---|---|---|
| `get_gbp_status()` | Account Management v1 | `GET /v1/accounts` |
| `get_gbp_location_info()` | Business Information v1 | `GET /v1/locations/*` |
| `get_gbp_performance(days=30)` | Performance v1 | `:fetchMultiDailyMetricsTimeSeries` |
| `get_gbp_search_keywords(months=1, limit=25)` | Performance v1 | `/searchkeywords/impressions/monthly` |
| `get_gbp_reviews(limit=20)` | **v4 legacy** | `GET /v4/accounts/*/locations/*/reviews` |
| `create_gbp_post(summary, cta_url, cta_type, schedule_time)` | **v4 legacy** | `POST .../localPosts` |
| `reply_to_gbp_review(review_id, comment, overwrite)` | **v4 legacy** | `PUT .../reviews/*/reply` |

Reseñas y publicaciones sólo existen en la v4 legacy; no tienen reemplazo en las APIs v1.

### 4.1 Métricas diarias consultadas

`BUSINESS_IMPRESSIONS_{DESKTOP,MOBILE}_{MAPS,SEARCH}`, `WEBSITE_CLICKS`, `CALL_CLICKS`, `BUSINESS_DIRECTION_REQUESTS`, `BUSINESS_CONVERSATIONS`. Se excluyen `BUSINESS_BOOKINGS` y las de comida, que no aplican a un service-area business B2B.

### 4.2 Estados de respuesta

| `status` | Significado |
|---|---|
| `success` | Datos válidos |
| `missing_credentials` | Falta `GBP_CLIENT_ID`, `GBP_CLIENT_SECRET` o `GBP_REFRESH_TOKEN` |
| `missing_location` / `missing_account` | Falta `GBP_LOCATION_ID` / `GBP_ACCOUNT_ID` |
| `api_not_approved` | HTTP 429: el proyecto de GCP tiene quota 0 QPM |
| `auth_error` | HTTP 401/403: scope insuficiente o cuenta sin permisos sobre la ficha |
| `rejected` | Guardrail de dominio rechazó la escritura (no se llamó a la API) |
| `not_found` | La reseña no está entre las 50 más recientes |

---

## 5. Caché

Prefijos registrados en `src/adapters/gateways/api_cache_gateway.py`:

| Clave | TTL | Razón |
|---|---|---|
| `gbp:location_info` | 24 h | La ficha cambia muy poco |
| `gbp:performance` | 6 h | Serie diaria, llega con retraso |
| `gbp:search_keywords` | 24 h | Serie mensual |
| `gbp:reviews` | 30 min | Se invalida al responder |

`ApiCachePort` no expone borrado, así que el gateway lleva un registro de las claves que escribió y las expira con `set(key, None, ttl_seconds=0)` tras una respuesta a reseña. La invalidación es intra-proceso; entre procesos el TTL corto de `gbp:reviews` cierra la ventana.

---

## 6. Configuración

| Variable | Obligatoria | Notas |
|---|---|---|
| `GBP_CLIENT_ID` | No | Cae a `GOOGLE_ADS_CLIENT_ID` |
| `GBP_CLIENT_SECRET` | No | Cae a `GOOGLE_ADS_CLIENT_SECRET` |
| `GBP_REFRESH_TOKEN` | **Sí** | Propio: se emite por scope |
| `GBP_ACCOUNT_ID` | Sí para v4 | Acepta `123` o `accounts/123` |
| `GBP_LOCATION_ID` | **Sí** | Acepta `456` o `locations/456` |

Scope: `https://www.googleapis.com/auth/business.manage`, disponible como preset `gbp` en `scripts/authenticate_gmail_oauth.py`.

---

## 7. Runbook de habilitación

Secuencial; los pasos 1 a 4 son prerrequisitos duros de Google y no dependen de este código.

1. Crear y verificar la ficha siguiendo §11 del plan de Fase 4.
2. **Esperar 60 días** de ficha verificada y activa — condición que Google exige antes de otorgar acceso a la API.
3. Habilitar en el proyecto de GCP: `mybusinessaccountmanagement`, `mybusinessbusinessinformation`, `businessprofileperformance` y `mybusiness` (v4).
4. Enviar el *GBP API contact form* → "Application for Basic API Access", desde un email propietario de la ficha. Confirmar que la quota pasó de 0 a 300 QPM.
5. `python scripts/authenticate_gmail_oauth.py --scopes gbp --email <propietario>` → volcar `GBP_REFRESH_TOKEN` en `.env`.
6. `get_gbp_status()` para resolver y fijar `GBP_ACCOUNT_ID` y `GBP_LOCATION_ID`.

Hasta completar el paso 4 el servidor arranca y responde, pero toda herramienta degrada a `api_not_approved` o `missing_credentials`.

---

## 8. Endpoints REST espejo

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/analytics/gbp/performance?days=30` | Métricas de la ficha |
| `GET` | `/api/v1/analytics/gbp/reviews?limit=20` | Reseñas con estado de respuesta |

El digest (`/api/v1/analytics/digest`) incluye la sección de la ficha y sus anomalías cuando hay datos.

---

## 9. Tests

| Archivo | Cobertura |
|---|---|
| `tests/mcp/test_gbp.py` | Degradación sin credenciales, traducción de HTTP 429/403, parseo de series y reseñas, guardrails de escritura, invalidación de caché |
| `tests/unit/test_analytics_domain_services.py` | `FichaLocalAnalysisService` y guardrails de dominio |
| `tests/unit/test_generar_analytics_digest.py` | Digest con y sin puerto GBP, y con la API sin aprobar |
| `tests/integration/test_analytics_routes.py` | Los dos endpoints espejo |

Ninguno sale a la red: se inyectan puertos falsos o se hace `monkeypatch` de `_pedir` / `urlopen`.
