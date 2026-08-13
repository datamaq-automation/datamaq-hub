# CONVENTIONS.md - Guía de Estilo y Convenciones de Desarrollo

## 1. Stack Tecnológico & Arquitectura
* **Lenguaje:** Python 3.10+ con tipado estricto (`typing`, `Annotated`, `TypeAlias`).
* **Framework Web:** FastAPI (asíncrono, OpenAPI autodocumentado).
* **Validación & Serialización:** Pydantic v2 (`BaseModel`, `Field`, `ConfigDict`, `field_validator`, `model_validator`).
* **Procesamiento de Documentos:** `pdfplumber` para extracción estructurada y análisis posicional/espacial de PDFs.
* **Testing:** `pytest` con `httpx.AsyncClient` o `starlette.testclient.TestClient`.
* **Linter & Formatter:** `ruff` (reglas E, F, I, B, UP).

---

## 2. Estructura de Directorios (Capas Limpias)
```
src/
├── api/            # Controladores, routers y dependencias FastAPI
│   ├── routes.py
│   └── dependencies.py
├── schemas/        # Modelos de datos y DTOs Pydantic v2
│   ├── recibo.py
│   └── common.py
├── services/       # Lógica de negocio, extractores y parsers especializados
│   ├── pdf_extractor.py
│   ├── base_parser.py
│   ├── dgcye_parser.py
│   ├── generic_parser.py
│   └── parser_factory.py
├── utils/          # Funciones auxiliares puras, regex y validadores
│   ├── validators.py
│   └── text_helpers.py
├── config.py       # Configuración global de la app (pydantic-settings)
└── main.py         # Punto de entrada de FastAPI, middlewares y CORS
```

---

## 3. Convenciones de Código y Buenas Prácticas
1. **Tipado Estricto:**
   * Todas las funciones deben declarar tipos explícitos para parámetros y retornos (`def parse_pdf(file_bytes: bytes) -> ReciboSueldoResponse:`).
   * Usar `Optional[T]` o `T | None` consistentemente.
2. **Inmutabilidad y Validación:**
   * Utilizar Pydantic v2 para toda entrada/salida de la API.
   * Evitar manipular diccionarios planos (`dict`) sin esquema cuando se transfieran datos de negocio.
3. **Manejo de Errores:**
   * Levantar excepciones de dominio específicas (`ReceiptParsingError`, `InvalidPDFError`) en la capa de servicios.
   * Mapear las excepciones a respuestas HTTP enriquecidas en la capa `api/` con códigos semánticos (400, 422, 500).
4. **Funciones Puras en `utils/`:**
   * Los formateadores de moneda, parseadores de CUIT/CUIL y funciones regex no deben tener efectos secundarios ni depender de I/O.
5. **Testing & Cobertura:**
   * Cada parser o servicio nuevo debe tener su archivo de prueba correspondiente en `tests/` (`test_<nombre_servicio>.py`).
   * Los tests deben validar casos felices, datos incompletos y archivos corruptos.

---

## 4. Convenciones de Git y Commits
Seguir el estándar **Conventional Commits**:
* `feat:` Nueva funcionalidad o parser.
* `fix:` Corrección de bugs o errores de parsing.
* `refactor:` Mejoras en la estructura de código sin cambios en el comportamiento.
* `test:` Adición o actualización de tests unitarios/integración.
* `docs:` Documentación, OpenAPI y guías.
