# Ficha de Google Business Profile — Estado y Continuación

> **Ámbito:** Vertical de Google Business Profile (GBP) en `datamaq-hub` y su articulación con la Fase 4 de posicionamiento local de `www-datamaq`.
> **Estado:** Código implementado y desplegado — **inactivo por falta de ficha y de acceso a la API**.
> **Última actualización:** 2026-09-02
> **Spec técnica:** [`specs/gbp_mcp.md`](../specs/gbp_mcp.md)
> **Plan de negocio de referencia:** `www-datamaq/docs/fase4_google_business_profile.md`

---

## 1. Para retomar en 30 segundos

El hub tiene un cuarto vertical de analítica —Google Business Profile— completo, testeado y en producción. **No hace nada todavía**, y no es un bug: no existe la ficha de Google, y aunque existiera, Google exige 60 días de ficha verificada antes de dar acceso a la API.

Todo lo que se puede hacer sin la ficha, ya está hecho. Lo que falta es una secuencia de trámites y esperas (§4) que ninguna sesión de código puede acelerar.

| Pregunta | Respuesta |
|---|---|
| ¿Qué se hizo? | Vertical GBP completo: 7 tools MCP, dominio, guardrails, digest, watchdog, 2 endpoints REST, tests, spec |
| ¿Está desplegado? | Sí. Commit `e5c9790` en `main`, CI run `33687213624` en verde, jobs `ci` y `Deploy to VPS` OK |
| ¿Funciona? | No. Toda tool devuelve `missing_credentials`; el digest sale sin sección de ficha |
| ¿Por qué? | No hay ficha creada ni `GBP_REFRESH_TOKEN`, y el proyecto de GCP tiene quota 0 QPM |
| ¿Qué falta? | El runbook de §4, que empieza fuera del código: crear la ficha |
| ¿Hay que tocar código? | No para habilitarlo. Sí, opcionalmente, para lo de §7 |

---

## 2. Qué se construyó y dónde vive

### 2.1 Superficie MCP

Servidor `"DataMaq Google Business Profile MCP"` en `scripts/mcp_gbp_server.py`, con las tools en `src/infrastructure/fastmcp/gbp.py`.

| Tool | Qué hace |
|---|---|
| `get_gbp_status()` | Credenciales, cuentas visibles y si la ficha está resuelta |
| `get_gbp_location_info()` | Categorías, área de servicio, horario — para auditar la ficha contra el checklist §11 del plan |
| `get_gbp_performance(days=30)` | Impresiones Maps/Search, clics al sitio, llamadas, indicaciones, con período previo |
| `get_gbp_search_keywords(months=1, limit=25)` | Términos con los que aparece la ficha |
| `get_gbp_reviews(limit=20)` | Reseñas, puntuación y si están respondidas |
| `create_gbp_post(...)` | Publica (opcionalmente programada) — pasa por guardrails |
| `reply_to_gbp_review(...)` | Responde una reseña — pasa por guardrails |

### 2.2 Mapa de archivos

```
src/domain/analytics/
├── ports.py            GoogleBusinessProfileDataSourcePort
├── entities.py         MetricaFicha, ResenaFicha, TerminoBusquedaFicha
├── value_objects.py    ResumenFicha, AnomalyType.FICHA_*, MarketingActionType.GBP_*
├── services.py         FichaLocalAnalysisService + guardrails GBP
└── exceptions.py       FichaGoogleException y derivadas

src/adapters/gateways/gbp_gateway.py                  REST sobre urllib, 4 hosts de Google
src/application/use_cases/publicar_en_ficha_google.py Único punto de escritura
src/application/dtos/analytics_dtos.py                ResumenFichaDTO, ResenaFichaDTO, GbpPostRequestDTO…
src/infrastructure/fastmcp/gbp.py                     Tools MCP
scripts/mcp_gbp_server.py                             Entrypoint FastMCP

tests/mcp/test_gbp.py                                 19 tests del vertical
```

Puntos de integración modificados: `generar_analytics_digest.py` (cuarto puerto opcional), `analytics_digest.py`, `analytics_controller.py`, `analytics_routes.py`, `analytics_watchdog.py`, `api_cache_gateway.py` (TTLs `gbp:*`), `config.py`, `authenticate_gmail_oauth.py` (preset `gbp`).

### 2.3 Cómo verificar que sigue sano

```bash
./scripts/pre-push.sh                    # 0 pyright, ruff limpio, guards OK
./venv/bin/python -m pytest -n auto -q   # 395 tests
PYTHONPATH=. ./venv/bin/python scripts/mcp_gbp_server.py
```

---

## 3. Por qué está bloqueado

Tres condiciones encadenadas, ninguna resoluble desde el código:

1. **No existe la ficha.** La Fase 4 de `www-datamaq` figura como pendiente de ejecución, y una búsqueda web el 2026-09-02 no encontró ninguna ficha pública de DataMaq en Garín.
2. **Google exige 60 días.** El prerrequisito de Basic API Access es una ficha verificada y activa durante 60+ días, más un sitio web que la represente.
3. **Quota 0 QPM hasta la aprobación.** Antes del alta, toda llamada devuelve HTTP 429. El gateway lo traduce a `status: "api_not_approved"` con la guía de habilitación en el mensaje.

**Estado verificado del proyecto de GCP** (`datamaq-505320`, tomado de `~/.config/gcp/datamaq-ga4-key.json`): no hay `gcloud` CLI en la máquina local y el único token OAuth del repo tiene scope `adwords`, así que **el estado de aprobación no se pudo verificar programáticamente**. Se comprueba a ojo acá:

```
https://console.cloud.google.com/apis/api/businessprofileperformance.googleapis.com/quotas?project=datamaq-505320
```

`0 QPM` = no aprobado · `300 QPM` = aprobado.

---

## 4. Runbook de habilitación

Estrictamente secuencial. Los pasos 1 a 4 son trámites y esperas.

- [ ] **1. Crear y verificar la ficha** siguiendo §11 del plan de Fase 4 (`www-datamaq/docs/fase4_google_business_profile.md`): NAP de §3, service-area business con dirección oculta, las 10 localidades de §4.3, categoría primaria *Servicio de ingeniería eléctrica*.
- [ ] **2. Esperar 60 días** de ficha verificada y activa. Prerrequisito duro de Google.
- [ ] **3. Habilitar las 4 APIs** en el proyecto `datamaq-505320`:
  `mybusinessaccountmanagement` · `mybusinessbusinessinformation` · `businessprofileperformance` · `mybusiness` (v4, para reseñas y publicaciones)
- [ ] **4. Solicitar Basic API Access** con el *GBP API contact form*, desde un email propietario de la ficha. Confirmar que la quota pasó a 300 QPM.
- [ ] **5. Obtener el refresh token** (requiere navegador, no se puede por SSH):
      ```bash
      ./venv/bin/python scripts/authenticate_gmail_oauth.py --scopes gbp --email <propietario-de-la-ficha>
      ```
      El script imprime `GBP_REFRESH_TOKEN=…`. Volcarlo en `.env` local **y** en el del VPS — ver [`credenciales_entornos.md`](credenciales_entornos.md) §7.
- [ ] **6. Resolver los identificadores:**
      ```bash
      ./venv/bin/python -c "from src.infrastructure.fastmcp.gbp import get_gbp_status; print(get_gbp_status())"
      ```
      Volcar `GBP_ACCOUNT_ID` y `GBP_LOCATION_ID` en ambos `.env`.
- [ ] **7. Verificar en vivo:**
      ```bash
      ssh vps 'systemctl restart datamaq-hub.service'
      ssh vps 'curl -s http://127.0.0.1:8013/api/v1/analytics/gbp/performance | head -c 300'
      ssh vps 'curl -s "http://127.0.0.1:8013/api/v1/analytics/digest?format=text"' | grep "Ficha de Google"
      ./venv/bin/python scripts/analytics_watchdog.py --dry-run --json
      ```

> **Primera escritura, con cuidado.** Probar `create_gbp_post(..., schedule_time=<futuro>)` y borrar la publicación desde la UI antes de que salga. Evita ensuciar una ficha nueva mientras se valida el circuito.

---

## 5. Decisiones tomadas (y por qué)

| Decisión | Razón | Reversible |
|---|---|---|
| Sin dependencias nuevas: REST sobre `urllib` | GBP no tiene SDK de Python y el repo no trae `google-api-python-client`. Se copió el patrón de `gmail_api_gateway.py` | Sí, sumando la dependencia |
| OAuth de usuario, no service account | Las APIs de GBP no aceptan service accounts. El refresh token se emite por scope, así que `business.manage` no invalida los de Gmail ni Ads | No — es limitación de Google |
| El vertical vive en `src/domain/analytics/` | Comparte `AnomalyAlert`, `AnomalyType` y `AnomalySeverity` con el digest. Una temática propia obligaría a duplicarlos | Sí, con refactor |
| **No se expone mutación de la location** | `brand.yaml` de `www-datamaq` es la fuente de verdad del NAP (§3 del plan). Cambiar nombre o dirección desde la API es además causal de suspensión (§10) | Deliberado — no revertir sin discutirlo |
| Identificadores de dominio en español | Regla 10 de `AGENTS.md` + regla anti-mimetismo, aunque el módulo `analytics` heredado usa inglés (`CampaignMetric`) | Sí, rename mecánico |
| El puerto GBP es **opcional** en el digest | Retrocompatibilidad: el digest funciona igual sin ficha. Hay un test que lo fija | Sí |
| Ventana mínima de 28 días para la ficha | El digest suele pedirse con `days=1` y la serie de GBP llega con retraso. Constante `FICHA_DIAS_MINIMOS` | Sí |

---

## 6. Cosas que sorprenden de la API

Vale dejarlas anotadas para no redescubrirlas:

- **Reseñas y publicaciones sólo existen en la v4 legacy** (`mybusiness.googleapis.com/v4`). No tienen reemplazo en las APIs v1. La superficie está repartida en **cuatro hosts** distintos.
- **El corte descubrimiento vs. marca de §9 del plan ya no existe.** Murió con la Insights API v4. Se aproxima clasificando términos que contienen "datamaq" contra el resto — es una heurística, no el dato de Google.
- **La API omite `value` cuando la métrica del día es 0.** Hay que tratar la ausencia como cero, no como dato faltante. Cubierto por test.
- **Los términos de búsqueda vienen como `value` exacto o como `threshold`** cuando el volumen es bajo. El gateway lo expone en el campo `es_umbral`.
- **`readMask` es obligatorio** en Business Information; sin él la llamada falla. Está en la constante `LOCATION_READ_MASK`.
- **`ApiCachePort` no tiene borrado.** El gateway registra las claves que escribió y las expira con `set(key, None, ttl_seconds=0)` tras responder una reseña. La invalidación es intra-proceso; entre procesos cierra el TTL de 30 min de `gbp:reviews`.

---

## 7. Pendientes conocidos

### 7.1 Los cuatro servidores MCP no levantan con `mcp 2.1.0` — preexistente

`mcp.server.fastmcp` ya no existe en la versión instalada; pasó a `mcp.server.mcpserver`. Los cuatro servidores (Clarity, GA4, Ads y GBP) degradan a `mcp = None` e imprimen `"FastMCP no disponible."`.

**No es una regresión de este trabajo** — es anterior, y el servidor de GBP replica el patrón existente a propósito, por consistencia. En producción el consumo real va por el espejo REST (`/api/v1/analytics/*`) y por el watchdog, que no dependen de FastMCP, así que no hay impacto operativo.

Arreglarlo es un cambio aparte que toca los cuatro entrypoints. Verificar antes con:
```bash
./venv/bin/python -c "import pkgutil, mcp.server; print([m.name for m in pkgutil.iter_modules(mcp.server.__path__)])"
```

### 7.2 Oportunidades una vez que la ficha esté viva

- **Regla de inactividad sin alimentar.** `FichaLocalAnalysisService.detectar_anomalias` acepta `dias_desde_ultima_publicacion`, pero nadie se lo pasa: haría falta un `list_gbp_posts` sobre `localPosts.list` de la v4. La regla ya está implementada y testeada, sólo le falta el dato.
- **Automatizar el calendario de §6.** Las 9 guías de la Fase 3 dan dos meses de publicaciones semanales. Con `create_gbp_post` y `schedule_time` se pueden programar todas de una, tomando los títulos y URLs de la tabla de §6 del plan.
- **Cerrar el circuito en `www-datamaq`** (§7 del plan, otro repositorio): sumar la URL de la ficha a `brand.sameAs` en `data/config/brand.yaml`, y apuntar `hasMap` al perfil real en `templates/seo/localidad.html` e `templates/index.html`, que hoy generan una búsqueda genérica de Maps.

---

## 8. Referencias

| Recurso | Dónde |
|---|---|
| Spec técnica del vertical | [`specs/gbp_mcp.md`](../specs/gbp_mcp.md) |
| Plan de negocio de la Fase 4 | `www-datamaq/docs/fase4_google_business_profile.md` |
| Analítica: las otras tres fuentes | [`analytics_and_ads.md`](analytics_and_ads.md) |
| Sincronización de credenciales local ↔ VPS | [`credenciales_entornos.md`](credenciales_entornos.md) |
| Commit del vertical | `e5c9790` |
| CI del despliegue | https://github.com/datamaq-automation/datamaq-hub/actions/runs/33687213624 |
