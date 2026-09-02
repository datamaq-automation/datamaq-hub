# AGENTS.md — Datamaq Hub

API FastAPI que parsea recibos de sueldo en PDF (DGCyE PBA / Genérico). Clean Architecture + DDD temático, tipado estricto, Python 3.10+ (venv local: 3.14 en `venv/`). Documentación y comentarios en español.

## Comandos (siempre desde la raíz del repo)

- Servidor dev: `./run.sh` — activa `venv/`, setea `PYTHONPATH=src`, corre `uvicorn src.main:app --reload` en `:8000`.
- Verificación pre-push: `./scripts/pre-push.sh` — `python scripts/verify_architecture.py` → `ruff check .` → `ruff format --check .` → `pyright` → `pytest tests/test_empty_inits.py` → `pytest -n auto -q tests/unit/ tests/test_architecture_boundaries.py`.
- Suite completa: `./scripts/ci.sh` — AST guard + pytest completo + `__init__.py` + pyright/mypy.
- Test individual: `pytest tests/unit/test_value_objects.py::test_cuit_validation` (desde la raíz).
- **Especificaciones y Documentación:** Las especificaciones formales residen en `specs/` (`receipt_parser.md`, `api_cache.md`, `analytics_mcp.md`, `gbp_mcp.md`, `mail_reader.md`, `contacts_manager.md`, `calendar_manager.md`) y la documentación viva en `docs/` (`docs/README.md`, `docs/recibo_parser_plan.md`, `docs/analytics_and_ads.md`, `docs/mail_openclaw_integration.md`, `docs/contacts_calendar_openclaw.md`).

## Arquitectura y reglas de dependencia

- `src/domain/{tematica}/` — estructura plana: `entities.py`, `value_objects.py`, `services.py`, `ports.py`, `exceptions.py`. Dominio 100% puro: solo stdlib + `@dataclass(frozen=True)`; **terminantemente prohibido importar frameworks o librerías de terceros**.
  - **Inmutabilidad Temporal (Prohibición de Datos Volátiles Hardcodeados):** Prohibido asignar defaults monetarios, paritarios o períodos fijos en Value Objects/Entidades. Todo dato sujeto a paritaria/fecha debe modelarse con un `Port` (`ports.py`) y resolverse en `adapters/gateways/`.
- `src/application/` — `dtos/` (Pydantic v2 permitido **solo** aquí), `mappers/`, `use_cases/`. Solo importa de `domain/`. Prohibido importar frameworks web (`fastapi`, `starlette`) o librerías de infraestructura.
- `src/adapters/` — `controllers/`, `gateways/`, `presenters/`.
  - **Regla sagrada 1 (Inversión de Dependencias):** Nunca importa `src/infrastructure/`.
  - **Regla sagrada 2 (Agnosticismo Web):** Prohibido acoplar `controllers/` o `presenters/` a frameworks web (`fastapi`, `starlette`). Los controladores y presenters deben ser clases/funciones puras de Python agnósticas de transporte.
  - **Gateways:** Implementan exclusivamente los `ports.py` de dominio (pueden encapsular librerías especializadas como `pdfplumber` o loaders JSON de paritarias en `data/paritarias/`).
  - La DI vive en `controllers/dependencies.py` con `@lru_cache`.
- `src/infrastructure/` — organizado por librería externa:
  - `fastapi/` (`server.py` = `create_app()`, `routes/` con routers HTTP, endpoints `@router.post`, inyecciones `Depends`, manejo de `UploadFile` y middlewares web).
  - `pydantic/` (`config.py` = `Settings` con `pydantic-settings`, soporta `.env`, `get_settings()` cacheado).
  - `src/main.py` es el entrypoint ASGI (`app = create_app()`).
- **Principio Anti-Mimetismo (Regla sobre Código Legado):** Si un archivo preexistente en el repositorio viola estas reglas de pureza de capas (por ejemplo, importando `fastapi` en `adapters/controllers/`), **NUNCA repliques esa violación al crear código nuevo o modificarlo**. La regla arquitectónica siempre prevalece sobre el código legado.

## Convenciones que rompen el repo si se ignoran

- **Imports absolutos `from src....` — nunca relativos.** pytest/uvicorn corren desde la raíz; los `tests/__init__.py` vacíos son load-bearing para el modo de import de pytest.
- **Todos los `__init__.py` (`src/` y `tests/`) deben quedar en 0 bytes** — testeado por `tests/test_empty_inits.py`. README.md y CONVENTIONS.md dicen que re-exportan símbolos: documentación obsoleta, el test manda.
- Identificadores de dominio en español (`ReciboSueldo`, `Agente`, `CUIT`, `DNI`, `ImporteMonetario`, `TipoConcepto`, `TipoRecibo`).
- **Tipado Estricto de Contenedores (`default_factory`):** Todo `default_factory` en `@dataclass` o `Field()` debe estar parametrizado con su tipo genérico completo (ej. `field(default_factory=dict[str, Any])`, `Field(default_factory=list[ItemDTO])`). Prohibido usar callables genéricos sin parametrizar (`dict`, `list`).
- Excepciones de dominio (`DomainException` y subclases en `exceptions.py`) mapeadas a HTTP en `ErrorPresenter`; no exponer excepciones de librerías en la API.
- Commits: Conventional Commits (`feat:` `fix:` `refactor:` `test:` `docs:`) — ver CONVENTIONS.md.

## Tests

- `tests/unit/` — puros, sin PDF. `tests/integration/` — `TestClient` + gateways con PDF real. Fixtures en `tests/conftest.py` (`client`, `sample_pdf_path`, `sample_pdf_bytes`).
- Los tests de integración con PDF real dependen de `data/36528392-2026-08-13-17_12_03_336.pdf`, pero `data/` está en `.gitignore`: en un clone fresco el fixture hace `pytest.skip` y `test_parse_real_pdf_controller` retorna sin asertar — **skipped por diseño, no "arreglar"**. Si se regenera el fixture, los valores golden (14 liquidaciones, total 2585423.32) deben coincidir.
- pytest-xdist: correr con `-n auto` es la norma (pre-push y ci lo usan).

## Referencias
 
- `CONVENTIONS.md` — convenciones de estilo y git (los `__init__.py` deben quedar en 0 bytes).
- `specs/README.md` — especificaciones técnicas de subsistemas (`receipt_parser.md`, `api_cache.md`, `analytics_mcp.md`, `gbp_mcp.md`, `mail_reader.md`).
- `docs/README.md` — índice maestro de documentación viva SSOT (`docs/recibo_parser_plan.md`, `docs/analytics_and_ads.md`, `docs/mail_openclaw_integration.md`, etc.).
