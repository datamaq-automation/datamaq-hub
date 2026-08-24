# CONVENTIONS.md - Guía de Estilo y Convenciones de Desarrollo

## 1. Stack Tecnológico & Arquitectura
* **Lenguaje:** Python 3.10+ con tipado estricto (`typing`, `Annotated`, `TypeAlias`, `dataclasses`).
* **Arquitectura:** Clean Architecture (Robert C. Martin / Ports & Adapters) + Domain-Driven Design (DDD).
* **Framework Web:** FastAPI (asíncrono, OpenAPI autodocumentado).
* **Validación & Serialización:** Pydantic v2 (`BaseModel`, `Field`, `ConfigDict`).
* **Configuración:** `pydantic-settings` (`BaseSettings`, `SettingsConfigDict`).
* **Procesamiento de Documentos:** `pdfplumber` para extracción estructurada en memoria.
* **Testing:** `pytest` con `starlette.testclient.TestClient` / `httpx`.
* **Linter & Formatter:** `ruff` (reglas E, F, I, B, UP, RUF).

---

## 2. Estructura de Directorios (Clean Architecture & DDD Temático)
```
src/
├── domain/                                      # 1. Capa de Dominio (Organizada por Temática)
│   └── {tematica}/                              # Subcarpeta temática (ej. recibos/, liquidacion/)
│       ├── __init__.py                          # 0 bytes (load-bearing para pytest)
│       ├── entities.py                          # Entidades del dominio (ReciboSueldo, Agente, etc.)
│       ├── value_objects.py                     # Value Objects inmutables (CUIT, DNI, ImporteMonetario, Tipos)
│       ├── services.py                          # Servicios puros de dominio (Totales, Normalizador)
│       ├── ports.py                             # Interfaces abstractas (ReceiptParserPort, PDFExtractorPort)
│       └── exceptions.py                        # Excepciones de dominio
│
├── application/                                 # 2. Capa de Aplicación (Casos de Uso y DTOs)
│   ├── use_cases/                               # Orquestadores de negocio (ParseReceiptUseCase, ProjectSalaryUseCase)
│   ├── dtos/                                    # Data Transfer Objects (ReceiptResponseDTO, SimulationDTO, etc.)
│   └── mappers/                                 # Mapeadores Entidad <-> DTO (ReceiptMapper, SimulationMapper)
│
├── adapters/                                    # 3. Capa de Adaptadores (Interface Adapters)
│   ├── controllers/                             # Inbound: controladores puros agnósticos de transporte
│   ├── gateways/                                # Outbound: pdfplumber, JSON paritarias, parsers DGCyE/Genérico
│   └── presenters/                              # Presenters de salida y formato de errores
│
├── infrastructure/                              # 4. Capa de Infraestructura (Por Librería Externa)
│   ├── fastapi/                                 # Servidor FastAPI, middlewares y routers HTTP
│   │   └── routes/                              # Routers FastAPI (health, recibos, simulation)
│   ├── fastmcp/                                 # Servidores MCP (Clarity, GA4, Google Ads)
│   └── pydantic/                                # Settings con pydantic-settings
│
└── main.py                                      # Entrypoint ASGI (app = create_app())
```

---

## 3. Convenciones de Código y Buenas Prácticas
1. **Regla de Dependencia en Clean Architecture:**
   * Las capas internas (`domain`) nunca deben importar de capas externas (`application`, `adapters`, `infrastructure`).
   * `application` solo depende de `domain`.
   * `adapters` depende de `application` y `domain`.
   * `infrastructure` aísla frameworks y bibliotecas externas.
2. **Organización Temática del Dominio:**
   * Cada subdominio o bounded context vive en `src/domain/{tematica}/`.
   * Dentro de cada temática, los archivos siguen un naming uniforme: `entities.py`, `value_objects.py`, `services.py`, `ports.py`, `exceptions.py`.
3. **Tipado Estricto:**
   * Todas las funciones deben declarar tipos explícitos para parámetros y retornos.
   * Usar `Annotated` para dependencias de FastAPI.
4. **Inmutabilidad y Value Objects:**
   * Los Value Objects del dominio son inmutables (`@dataclass(frozen=True)`).
5. **Manejo de Errores Semántico:**
   * Levantar excepciones de dominio (`DomainException`, `ReceiptParsingError`, `InvalidPDFError`) que son capturadas y mapeadas a códigos HTTP en `ErrorPresenter` y middlewares.
6. **Testing & Cobertura:**
   * Tests unitarios organizados en `tests/unit/`.
   * Tests de integración organizados en `tests/integration/`.

---

## 4. Convenciones de Git y Commits
Seguir el estándar **Conventional Commits** de manera rigurosa:
* `feat:` Nueva funcionalidad o parser.
* `fix:` Corrección de bugs o errores de parsing.
* `refactor:` Mejoras en la estructura de código sin cambios en el comportamiento.
* `test:` Adición o actualización de tests unitarios/integración.
* `docs:` Documentación, OpenAPI y guías de uso interno.

---

## 5. Gobernanza Interna y Control de Calidad Obligatorio
Antes de integrar cambios al entorno de ejecución del Hub (repositorio interno), es obligatorio validar:
1. **Tipado Estricto con Pyright:** 0 errores de tipado estático con `pyright`.
2. **Autoformateo y Calidad de Código:** Limpieza impecable mediante `ruff check .` y `ruff format --check .`.
3. **Tests de Regresión:** La suite de pruebas debe pasar al 100% (incluyendo el Architecture Guard `test_architecture_boundaries.py` y `test_empty_inits.py`).
4. **Verificación Pre-push Automatizada:** Ejecutar `./scripts/pre-push.sh` localmente.
5. **Aislamiento en __init__.py:** Garantizar que todos los archivos `__init__.py` permanezcan vacíos (0 bytes) para evitar mimetismos en el descubrimiento de módulos por pytest.

