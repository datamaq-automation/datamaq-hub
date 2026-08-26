# Spec: Caché Persistente de APIs Externas (SQLAlchemy + MySQL)

## 1. Objetivo y Contexto

### Alcance
Las respuestas de los servidores FastMCP (Google Ads, GA4 y Microsoft Clarity) se
consultan en tiempo real contra las APIs externas en cada invocación. Esto consume
cuotas, añade latencia y expone a errores de *rate-limit*.

**Solución:** capa de caché persistente en MySQL (schema dedicado `datamaq_hub`,
separado de `datamaq_leads` de `www-datamaq`) usando SQLAlchemy ORM. Las respuestas
se serializan a JSON con un TTL por tipo de endpoint.

### Límites (fuera de alcance)
- Migraciones versionadas (Alembic). Se usa `CREATE TABLE IF NOT EXISTS` idempotente.
- Invalidación manual / purga de entradas. El TTL es la única política de expiración.
- Caché distribuida o en memoria (Redis). Solo persistencia en MySQL.

### Decisión de arquitectura (corrige deuda del intento previo)
La implementación anterior ubicó `ApiCacheService` en `src/application/use_cases/`
importando `src.infrastructure.database`, lo que **rompe la pureza de la capa de
aplicación** (`tests/test_architecture_boundaries.py`) y la Regla Sagrada 1
(adapters nunca importa infrastructure). Este spec **reubica** la persistencia como
un **gateway** que encapsula SQLAlchemy directamente (mismo patrón que
`pdfplumber_extractor_gateway`), consumido vía un **Puerto de dominio** inyectado.

## 2. Dominio & Puertos

### `src/domain/cache/ports.py` — `ApiCachePort` (dominio 100% puro)

Interfaz abstracta (`abc.ABC`), sin dependencias externas ni frameworks:

| Método | Contrato |
|---|---|
| `get(key: str) -> Any \| None` | Retorna el valor deserializado si hay entrada vigente; `None` en miss, expirado o sin BD. |
| `set(key: str, value: Any, ttl_seconds: int \| None = None) -> None` | Persiste `value` serializado. `ttl_seconds=None` resuelve por prefijo de clave. No-op sin BD. |

### Regla de inmutabilidad temporal
Los TTL son períodos operativos sujetos a configuración. Quedan **prohibidos como
datos volátiles en Entidades/Value Objects**; se resuelven en el gateway
(`CACHE_TTL`), cumpliendo la regla "resolverse en adapters/gateways".

## 3. Casos de Uso & DTOs

### 3.1 `ApiCacheGateway` (`src/adapters/gateways/api_cache_gateway.py`)

Implementa `ApiCachePort`. Contiene además el ORM encapsulado:

- `Base` (DeclarativeBase) y modelo `ApiCacheEntry` (`__tablename__ = "api_cache"`):
  - `id` (PK autoincremento), `cache_key` (Text, unique, indexado),
  - `response_json` (Text, `length=16_777_215` — MEDIUMTEXT),
  - `created_at` / `expires_at` (`DateTime` naive UTC, `expires_at` indexado).
- `get_engine(database_url)` / `get_session_factory(database_url)` con `@cache`;
  **retornan `None`** si `database_url` está vacío (degradación elegante).
- `init_db(database_url)` → `Base.metadata.create_all(engine)` idempotente; no-op sin BD.
- Constructor: `ApiCacheGateway(database_url: str | None = None, ttl_by_prefix: dict[str, int] | None = None)`. Aplica
  **merge**: `{**CACHE_TTL, **(ttl_by_prefix or {})}` — lo configurado sobreescribe, lo
  ausente conserva el default aprobado.
- TTLs por prefijo — **defaults de fallback** (segundos, confirmados por el usuario
  el 2026-08-25), sobreescribibles por `Settings.cache_ttls` (JSON en `.env`):

| Prefijo de clave | TTL (s) | Duración |
|---|---|---|
| `google_ads:campaign_performance` | 14_400 | 4 horas |
| `google_ads:search_terms_report` | 43_200 | 12 horas |
| `google_ads:daily_budget_pacing` | 900 | 15 minutos |
| `ga4:top_pages` | 3_600 | 1 hora |
| `ga4:traffic_sources` | 3_600 | 1 hora |
| `ga4:conversions` | 3_600 | 1 hora |
| `ga4:geo_traffic` | 3_600 | 1 hora |
| `clarity:live_insights` | 7_200 | 2 horas |
| `clarity:dashboard_insights` | 7_200 | 2 horas |
| *(clave no registrada)* `DEFAULT_TTL` | 3_600 | 1 hora |

- Timestamps **UTC correctos**: generados con `datetime.now(timezone.utc)` y
  persistidos como *naive UTC* (`replace(tzinfo=None)`), compatible con MySQL
  `DATETIME` (no almacena offset) y SQLite. Prohibido `datetime.utcnow()`
  (deprecado en Python 3.12+). La expiración se compara en Python para evitar
  ambigüedad naive/aware entre dialectos.
- `json.dumps(..., ensure_ascii=False, default=str)`.
- `_resolve_ttl` consulta `self._ttl_by_prefix` (no la constante global); cae a
  `DEFAULT_TTL` para claves sin prefijo registrado.

### 3.2 Claves canónicas (contrato de integración)

| Gateway / método | Clave |
|---|---|
| `GoogleAdsGateway.get_campaign_performance` | `google_ads:campaign_performance:days_{days}` |
| `GoogleAdsGateway.get_search_terms_report` | `google_ads:search_terms_report:days_{days}:limit_{limit}` |
| `GoogleAdsGateway.get_daily_budget_pacing` | `google_ads:daily_budget_pacing` |
| `GA4Gateway.get_top_pages` | `ga4:top_pages:days_{days}:limit_{limit}:segment_{segment}` |
| `GA4Gateway.get_traffic_sources` | `ga4:traffic_sources:days_{days}:limit_{limit}` |
| `GA4Gateway.get_geo_traffic` | `ga4:geo_traffic:days_{days}:limit_{limit}` |
| `GA4Gateway.get_conversions` | `ga4:conversions:days_{days}` |
| `ClarityGateway.get_live_insights` | `clarity:live_insights` |
| `ClarityGateway.get_dashboard_insights` | `clarity:dashboard_insights:days_{days}` |

### 3.3 Inyección en gateways externos

Los 3 gateways (`GoogleAdsGateway`, `GA4Gateway`, `ClarityGateway`) reciben
`cache: ApiCachePort | None = None` en `__init__` (default → `ApiCacheGateway()`).

**Ensamblaje en FastMCP** (infrastructure lee Settings → inyecta a adapters, mismo
patrón que las credenciales):

```python
settings = get_settings()
_cache = ApiCacheGateway(
    database_url=settings.database_url,
    ttl_by_prefix=settings.cache_ttls or None,
)
_gateway = GoogleAdsGateway(..., cache=_cache)  # idem GA4Gateway / ClarityGateway
```

`adapters` no importa `src.infrastructure` (Regla Sagrada 1 intacta): los TTLs
fluyen por constructor desde la capa más externa.

**Completar ClarityGateway** (el intento previo importó `_cache` pero no lo usó):
`get_live_insights` y `get_dashboard_insights` deben hacer `get` → API → `set`.

### 3.4 Startup

`src/infrastructure/fastapi/server.py` usa un *lifespan* `@asynccontextmanager` que
ejecuta `init_db(settings.database_url)` (reemplaza `on_event("startup")`, deprecado).

## 4. Matriz de Pruebas (RED Suite)

Backend de tests: **SQLite en memoria** (`sqlite:///:memory:` + `StaticPool`) — sin
MySQL en CI. `sqlite3` es stdlib y SQLAlchemy lo soporta.

| # | Escenario Gherkin | Resultado esperado |
|---|---|---|
| R1 | **Dado** `DATABASE_URL` vacío, **Cuando** `get(clave)`, **Entonces** retorna `None` | None (sin excepción) |
| R2 | **Dado** `DATABASE_URL` vacío, **Cuando** `set(clave, valor)`, **Entonces** no persiste ni lanza | no-op |
| R3 | **Dado** tabla vacía, **Cuando** `get(clave_inexistente)`, **Entonces** retorna `None` | miss |
| R4 | **Dado** entrada vigente, **Cuando** `get(clave)`, **Entonces** retorna el valor deserializado | hit JSON |
| R5 | **Dado** entrada con `expires_at` en el pasado, **Cuando** `get(clave)`, **Entonces** retorna `None` | expirado |
| R6 | **Dado** clave inexistente, **Cuando** `set(clave, v)`, **Entonces** inserta fila con `expires_at = now + TTL` | insert |
| R7 | **Dado** clave existente, **Cuando** `set(clave, v2)`, **Entonces** actualiza `response_json`/`expires_at` (sin duplicar) | update |
| R8 | **Dado** clave con prefijo conocido, **Cuando** `_resolve_ttl`, **Entonces** retorna el TTL del prefijo | 14400/43200/900/3600/7200 |
| R9 | **Dado** clave sin prefijo registrado, **Cuando** `_resolve_ttl`, **Entonces** retorna 3600 | DEFAULT_TTL |
| R10 | **Dado** cualquier `set`, **Entonces** los timestamps se generan con `timezone.utc` (sin `datetime.utcnow`) y persisten como naive UTC | UTC correcto |
| R11 | **Dado** gateway externo con `FakeCache`, **Cuando** llamo 2 veces, **Entonces** la API externa se invoca 1 sola vez y la 2ª sirve caché | 1 call + hit |
| R12 | **Dado** el refactor, **Entonces** `test_architecture_boundaries.py` pasa (application no importa infrastructure) | sin violaciones |
| R13 | **Dado** `ttl_by_prefix` con 1 prefijo, **Cuando** `_resolve_ttl`, **Entonces** ese prefijo usa el valor configurado y otro prefijo conserva el default | override parcial |
| R14 | **Dado** constructor sin argumentos, **Cuando** `_resolve_ttl`, **Entonces** usa las constantes aprobadas | defaults de fallback |

### Contratos de tests (archivos)
- `tests/unit/test_api_cache_gateway.py` — R1–R10, R13–R14.
- `tests/unit/test_gateway_cache_integration.py` — R11 (FakeCache inyectado +
  monkeypatch de `_run_ga4_report` / `_get_google_ads_client` / `_clarity_api_request`).
- `tests/test_architecture_boundaries.py` — R12 (ya existente, sin cambios).

## 5. Criterios del Gauntlet

```bash
./scripts/pre-push.sh
pytest -n auto -q tests/unit/ tests/test_architecture_boundaries.py
```

| Etapa | Criterio |
|---|---|
| Integridad | `__init__.py` en 0 bytes (incluido el nuevo `src/domain/cache/__init__.py`) |
| Estilo | `ruff check .` y `ruff format --check .` → 0 errores |
| Tipado | `pyright` → 0 diagnósticos (sin `datetime.utcnow`; `# type: ignore` solo en imports de librerías de terceros sin stubs, ej. `google.ads`) |
| Tests | 100% aprobados, cobertura ≥ 85% |
| Fronteras | `test_architecture_boundaries.py` sin violaciones |

### Archivos del cambio
- **Nuevos:** `src/domain/cache/__init__.py`, `src/domain/cache/ports.py`,
  `src/adapters/gateways/api_cache_gateway.py`, `tests/unit/test_api_cache_gateway.py`,
  `tests/unit/test_gateway_cache_integration.py`.
- **Modificados:** `src/adapters/gateways/{google_ads,ga4,clarity}_gateway.py`,
  `src/infrastructure/fastapi/server.py`, `src/infrastructure/fastmcp/{google_ads,ga4,clarity}.py`,
  `src/infrastructure/pydantic/config.py`, `.env.example`.
- **Eliminados:** `src/application/use_cases/api_cache_service.py`,
  `src/infrastructure/database/` (4 archivos).
