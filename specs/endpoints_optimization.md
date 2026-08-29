# Spec: Optimización Integral de Endpoints y Hardware VPS para OpenClaw

> **Subsistema:** Presentación API (`src/infrastructure/fastapi`), DTOs de aplicación y operación de infraestructura.
> **Estado:** En Implementación

---

## 1. Contexto y Alcance

### 1.1 Objetivo
Reducir el consumo de tokens de OpenClaw en las consultas a la API (calendario, contactos,
analytics y recibos) y optimizar la operación en el VPS DonWeb (2 vCPUs, 4 GB RAM):
compresión gzip, caché SQLite WAL persistente cuando `DATABASE_URL` está vacío y 2 workers uvicorn.

### 1.2 Límites (fuera de alcance)
- Sin cambios en `src/domain/` ni en `ports.py` (dominio 100% puro intocado).
- Sin cambios en `src/adapters/controllers/dependencies.py`.
- Sin migraciones versionadas (Alembic).
- El cambio systemd (`--workers 2`) es operativo en el VPS (runbook); no aplica al Gauntlet.

### 1.3 Decisiones de diseño (DD)

| ID | Decisión |
|---|---|
| DD1 | `GZipMiddleware(minimum_size=1000)` en `create_app()` (`server.py`). |
| DD2 | Fallback de BD en lifespan: `_resolve_database_url(settings.database_url)` → `""` → `"sqlite:///data/datamaq_hub.db"`; PRAGMA `journal_mode=WAL` en engines SQLite de `api_cache_gateway.get_engine` y `init_horarios_db` (guard: `startswith("sqlite")` y `":memory:" not in url`). |
| DD3 | `GET /calendario/eventos`: `limit` default 20 (le=200), `compact: bool = True`. `CalendarEventCompactDTO` = `{id_evento, titulo, inicio, fin, estado, cuenta}`. |
| DD4 | `GET /contactos`: `limit` default 20, `compact: bool = False` (opt-in, no rompe consumidores). `ContactoCompactoDTO` = `{id_contacto, nombre, email, telefono, organizacion}` + `ContactListCompactResponseDTO{total, cuenta, contactos}`. |
| DD5 | `GET /analytics/ads/campaigns`: `summary: bool = True`. Agregación en `AnalyticsController.get_ads_campaigns`; **passthrough** si `status != "success"`. |
| DD6 | `POST /recibos/parse`: `solo_resumen: bool = False`. `ReceiptSummaryDTO` + `ReceiptMapper.to_summary(dto)`. |
| DD7 | Proyección compacta (DD3/DD4) implementada en las rutas (infrastructure), no en controllers (cero ripple en unit tests existentes). |
| DD8 | Response models como **unión de envelopes** (`APIResponseDTO[A] | APIResponseDTO[B]`) retornando la instancia tipada exacta → passthrough determinístico de Pydantic v2. |

---

## 2. Entidades y Puertos

**Sin cambios.** Dominio y `ports.py` intocados. Aplicación: solo DTOs nuevos (Pydantic, permitido en
`src/application/dtos/`) y un método mapper adicional.

---

## 3. DTOs, Casos de Uso y Cambios por Capa

### 3.1 DTOs nuevos (`src/application/dtos/`)

- `calendar_dto.py` → `CalendarEventCompactDTO` (`id_evento`, `titulo`, `inicio`, `fin`, `estado="CONFIRMED"`, `cuenta=""`).
- `contacts_dto.py` → `ContactoCompactoDTO` (`id_contacto`, `nombre`, `email=""`, `telefono=""`, `organizacion=""`).
- `contacts_dto.py` → `ContactListCompactResponseDTO` (`total`, `cuenta`, `contactos: list[ContactoCompactoDTO]`).
- `receipt_dto.py` → `ReceiptSummaryDTO`:
  - `total_haberes: float` · `total_descuentos: float` · `neto_a_cobrar: float` · `periodo: str`
  - `cargos: list[CargoDTO]` · `horas_totales: float` · `antiguedad_max_anios: int | None = None`

Todos con `model_config = ConfigDict(extra="ignore")`.

### 3.2 `ReceiptMapper.to_summary(dto: ReceiptResponseDTO) -> ReceiptSummaryDTO`

- `total_haberes` / `total_descuentos` / `neto_a_cobrar` ← `dto.totales` (haberes, descuentos, liquido).
- `periodo` ← `dto.agente.mes_pago`.
- `cargos` ← lista `CargoDTO` por cada `liquidacion.cargo` (reutiliza DTO existente).
- `horas_totales` ← `round(Σ carga_horaria, 2)`.
- `antiguedad_max_anios` ← max de `antiguedad_anios` no-None (`None` si vacío).

### 3.3 Controllers (`src/adapters/controllers/`, puros)

- `ReceiptController.parse_bytes(..., solo_resumen: bool = False)`:
  - `solo_resumen=True` → `APIResponseDTO[ReceiptSummaryDTO](success=True, data=ReceiptMapper.to_summary(receipt_dto))`.
  - `solo_resumen=False` → `ReceiptPresenter.present(...)` (inalterado).
- `AnalyticsController.get_ads_campaigns(days: int = 7, summary: bool = True)`:
  - `report = gateway.get_campaign_performance(days)`.
  - si `not summary or report.get("status") != "success"` → passthrough.
  - si no → `summary = {impressions, clicks, cost_ars, ctr_percent, conversions, cpc_avg_ars}`
    (CTR = clicks/impressions·100, CPC = cost/clicks, ceros defensivos) → payload
    `{status, customer_id, period_days, total_campaigns, summary}` (sin lista `campaigns`).

### 3.4 Rutas (`src/infrastructure/fastapi/routes/`)

| Ruta | Cambio |
|---|---|
| `calendar_routes.py` `/eventos` | `limit=Query(20, ge=1, le=200)`, `compact: bool = True`; response_model `APIResponseDTO[list[CalendarEventDTO]] \| APIResponseDTO[list[CalendarEventCompactDTO]]`; proyección `_proyectar_compacto()`. |
| `contacts_routes.py` `/contactos` | `limit=Query(20, ge=1, le=200)`, `compact: bool = False`; response_model `APIResponseDTO[ContactListResponseDTO] \| APIResponseDTO[ContactListCompactResponseDTO]`; proyección `_proyectar_compacto()`. |
| `receipt_routes.py` `/parse` | `solo_resumen: bool = False`; response_model `APIResponseDTO[ReceiptResponseDTO] \| APIResponseDTO[ReceiptSummaryDTO]`; pasa `solo_resumen` al controller. |
| `analytics_routes.py` `/ads/campaigns` | `summary: bool = Query(True)`; pasa a `controller.get_ads_campaigns(days=days, summary=summary)`. |

### 3.5 Infraestructura

- `server.py`: `GZipMiddleware(minimum_size=1000)`; helper puro `_resolve_database_url(raw: str) -> str`;
  lifespan usa `init_db(effective)` + `init_horarios_db(effective)` con `effective = _resolve_database_url(settings.database_url)`.
- `api_cache_gateway.py` `get_engine`: `event.listen(engine, "connect")` → `PRAGMA journal_mode=WAL`
  (solo SQLite file, no `:memory:`).
- `sql_designacion_docente_gateway.py` `init_horarios_db`: `PRAGMA journal_mode=WAL` en la conexión
  existente (mismo guard).
- `.env.example`: comentario documentando el fallback.

---

## 4. Matriz BDD/Gherkin y Tests RED

| # | Escenario | Resultado |
|---|---|---|
| R-S1 | **Dado** `create_app()`, **Cuando** inspecciono `user_middleware`, **Entonces** existe `GZipMiddleware` con `minimum_size=1000` | registrado |
| R-S2 | **Dado** `_resolve_database_url("")` **Entonces** → `"sqlite:///data/datamaq_hub.db"`; **Dado** URL mysql **Entonces** se conserva | fallback puro |
| R-S3 | **Dado** `get_engine("sqlite:///<tmp>/x.db")`, **Cuando** `PRAGMA journal_mode`, **Entonces** → `"wal"` | WAL activo |
| R-R1 | **Dado** `ReciboSueldo` con 2 liquidaciones, **Cuando** `ReceiptMapper.to_summary`, **Entonces** totales/horas (Σ)/antigüedad (max)/período/cargos correctos | mapper |
| R-R2 | **Dado** controller con use-case stub, **Cuando** `parse_bytes(..., solo_resumen=True)`, **Entonces** envelope con `ReceiptSummaryDTO` | resumen |
| R-R3 | **Dado** `solo_resumen=False`, **Entonces** envelope `ReceiptResponseDTO` actual | intacto |
| R-A1 | **Dado** reporte success con 2 campañas, **Cuando** `get_ads_campaigns(summary=True)`, **Entonces** `data.summary` consolida clics/impresiones/costo/CTR/conv/CPC y **no** hay clave `campaigns` | agregación |
| R-A2 | **Dado** `summary=False`, **Entonces** payload original con `campaigns` | passthrough |
| R-A3 | **Dado** `status != "success"`, **Entonces** passthrough sin agregar | passthrough |
| R-A4 | **Dado** campañas vacías, **Entonces** summary con ceros (sin ZeroDivision) | defensivo |
| R-C1 | **Dado** GET `/calendario/eventos` (default), **Entonces** `data[i]` claves exactas `{id_evento, titulo, inicio, fin, estado, cuenta}` | compact default |
| R-C2 | **Dado** GET `/calendario/eventos?compact=false`, **Entonces** claves completas `CalendarEventDTO` | full |
| R-C3 | **Dado** GET `/calendario/eventos?limit=20`, **Entonces** 200 | default 20 |
| R-K1 | **Dado** GET `/contactos` (default), **Entonces** claves completas | no rompe |
| R-K2 | **Dado** GET `/contactos?compact=true`, **Entonces** claves exactas `{id_contacto, nombre, email, telefono, organizacion}` | compact |
| R-RI1 | **Dado** sample PDF + `solo_resumen=true`, **Entonces** `data` claves exactas del `ReceiptSummaryDTO` (skip si falta fixture) | resumen |
| R-RI2 | **Dado** sample PDF (default), **Entonces** shape completo actual | intacto |
| R-G1 | **Dado** ruta test-only >1 KB + `Accept-Encoding: gzip`, **Entonces** `Content-Encoding: gzip` | gzip |
| R-G2 | **Dado** misma ruta sin header gzip, **Entonces** sin `Content-Encoding` | sin compresión |

### Archivos de tests

- **Nuevos:** `tests/unit/test_server_middleware.py` (R-S1..S3), `tests/unit/test_receipt_summary.py` (R-R1..R3),
  `tests/integration/test_server_gzip.py` (R-G1..G2).
- **Modificados:** `tests/unit/test_analytics_controller.py` (append R-A1..A4),
  `tests/integration/test_calendar_routes.py` (append R-C1..C3),
  `tests/integration/test_contacts_routes.py` (append R-K1..K2),
  `tests/integration/test_recibos_routes.py` (append R-RI1..RI2).

> **Regla de inmutabilidad:** no se relajan, comentan ni borran tests existentes. Los 226+ tests
> actuales deben seguir pasando (compatibilidad de defaults verificada en la fase de análisis).

---

## 5. Criterios del Gauntlet

```bash
./scripts/pre-push.sh
./scripts/ci.sh
pytest -n auto -q tests/unit/ tests/integration/ tests/test_architecture_boundaries.py
```

| Etapa | Criterio |
|---|---|
| Integridad | `__init__.py` en 0 bytes |
| Estilo | `ruff check .` y `ruff format --check .` → 0 errores |
| Tipado | `pyright` strict → 0 diagnósticos; `default_factory` parametrizados (`list[CargoDTO]`, etc.) |
| Suite | `pytest --cov=src --cov-fail-under=85` → 100% aprobados; tests previos intactos |
| Fronteras | `test_architecture_boundaries.py` sin violaciones (controllers puros: cero imports web) |

### Runbook VPS (fuera de Gauntlet)

1. `systemctl edit datamaq-hub.service` → añadir `--workers 2` al comando uvicorn.
2. `systemctl daemon-reload && systemctl restart datamaq-hub`.
3. Verificar: `ps aux | grep uvicorn` (2 workers) · `curl -H 'Accept-Encoding: gzip' -I http://127.0.0.1:8013/...`
   (`Content-Encoding: gzip`) · `journalctl -u datamaq-hub` sin warnings de BD (fallback SQLite WAL).

---

### Archivos del cambio

- **Nuevos:** `specs/endpoints_optimization.md`, `tests/unit/test_server_middleware.py`,
  `tests/unit/test_receipt_summary.py`, `tests/integration/test_server_gzip.py`.
- **Modificados (`src/`):** `src/infrastructure/fastapi/server.py`,
  `src/adapters/gateways/api_cache_gateway.py`, `src/adapters/gateways/sql_designacion_docente_gateway.py`,
  `src/infrastructure/fastapi/routes/{calendar,contacts,receipt,analytics}_routes.py`,
  `src/application/dtos/{receipt,calendar,contacts}_dto.py`,
  `src/application/mappers/receipt_mapper.py`,
  `src/adapters/controllers/{receipt,analytics}_controller.py`,
  `.env.example`.
