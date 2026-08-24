# Datamaq Hub - Receipt Parser API (Repositorio Interno)

> **Ecosistema DataMaq:** *"Ingeniería de datos: de la planta a la oficina"*  
> **Ámbito:** Motor de procesamiento, extracción y estructuración automatizada de recibos de sueldo en PDF. Componente backend de infraestructura y soporte interno del grupo para la prevención de desvíos financieros en la liquidación de haberes y la automatización del control de costos administrativos de PyMEs y personal educativo.  
> **Diseño:** Clean Architecture (Ports & Adapters) + Domain-Driven Design (DDD) con organización temática plana y tipado estricto.

---

## 1. Ecosistema DataMaq (Tétrada de Repositorios)

La plataforma tecnológica de DataMaq se organiza en cuatro proyectos desacoplados con responsabilidades especializadas:

| Repositorio | Rol en la Arquitectura | Ruta Absoluta Local | Ruta Absoluta VPS (DonWeb) | Repositorio GitHub | Dominio / URL Pública |
|---|---|---|---|---|---|
| **`www-datamaq`** | Web institucional, SEO local, captura de leads, pricing y LMS (SSR) | `/home/agustin/proyectos_software/www-datamaq` | `/var/www/www-datamaq` *(puerto 8001)* | `git@github.com:datamaq-automation/www-datamaq.git` | [https://datamaq.com.ar](https://datamaq.com.ar) |
| **`app-datamaq`** | Dashboard SPA de telemetría, visualización interactiva y vitrina pública | `/home/agustin/proyectos_software/app-datamaq` | `/var/www/app-datamaq` | `git@github.com:datamaq-automation/app-datamaq.git` | [https://app.datamaq.com.ar](https://app.datamaq.com.ar) |
| **`datamaq-telemetry`** | Ingesta de tramas hardware Powermeter, Time-Series y WebSockets | `/home/agustin/proyectos_software/datamaq-telemetry` | `/var/www/datamaq-telemetry` *(puerto 8885)* | `git@github.com:datamaq-automation/datamaq-telemetry.git` | [https://api.datamaq.com.ar](https://api.datamaq.com.ar) |
| **`datamaq-hub`** | Herramientas internas, parseo de recibos y servidores FastMCP de analítica | `/home/agustin/proyectos_software/datamaq-hub` | `/var/www/datamaq-hub` | `git@github.com:datamaq-automation/datamaq-hub.git` | Uso interno / Local |

---

## 2. Estructura del Proyecto

* **[docs/](docs)**: Suite canónica de documentación viva (SSOT):
  * **[srs.md](docs/srs.md)**: Requisitos del sistema, propuesta de valor ("Máquinas + Datos + Dinero"), modelo SaaS $0 y catálogo comercial.
  * **[specs.md](docs/specs.md)**: Arquitectura Hexagonal/DDD real, Critical CSS, observabilidad (`X-Request-ID`), integración del ecosistema y testing.
  * **[ops.md](docs/ops.md)**: Manual de operaciones en VPS DonWeb, Systemd, Nginx, despliegues seguros y gestión de incidentes.
  * **[todo.md](docs/todo.md)**: Registro de Certezas vigentes (C-01 a C-14) y roadmap técnico.
  * **[analytics_and_ads.md](docs/analytics_and_ads.md)**: Gobernanza de cuentas Google, tracking de conversiones, Google Ads, GA4, Clarity y MCPs.
  * **[google_ads_campaigns_setup.md](docs/google_ads_campaigns_setup.md)**: Ficha técnica de carga de campañas SEM (Search B2B GBA Norte, keywords y negativas).
  * **[prompt_investigacion_profunda_gemini.md](docs/prompt_investigacion_profunda_gemini.md)**: Prompt maestro de Deep Research para posicionamiento B2B, embudo asíncrono y pricing.
  * **[informe_estrategico_gemini_2026.md](docs/informe_estrategico_gemini_2026.md)**: Informe estratégico integral sobre posicionamiento, marco ENRE 544/2024, Payback y monetización remota.
  * **[CHANGELOG.md](docs/CHANGELOG.md)**: Historial cronológico de hitos, refactorizaciones y decisiones de negocio.
* **[src/](src)**: Código fuente organizado en capas limpias (`domain`, `application`, `adapters`, `infrastructure`).


## 🏛️ Arquitectura del Sistema

```
src/
├── domain/                                      # 1. Capa de Dominio (Organizada por Temática)
│   ├── recibos/                                 # Bounded context: Recibos de Sueldo
│   │   ├── __init__.py                          # 0 bytes (load-bearing para pytest)
│   │   ├── entities.py                          # Entidades (ReciboSueldo, Agente, Empleador, etc.)
│   │   ├── value_objects.py                     # Value Objects inmutables (CUIT, DNI, ImporteMonetario, Tipos)
│   │   ├── services.py                          # Servicios puros (TotalesCalculator, TextNormalizer)
│   │   ├── ports.py                             # Interfaces abstractas (ReceiptParserPort, PDFExtractorPort)
│   │   └── exceptions.py                        # Excepciones de dominio
│   └── liquidacion/                             # Bounded context: Liquidación / Proyección Salarial
│       ├── __init__.py                          # 0 bytes (load-bearing para pytest)
│       ├── entities.py                          # Entidades de liquidación y proyección
│       ├── value_objects.py                     # Value Objects de liquidación
│       ├── services.py                          # Servicios de cálculo salarial
│       ├── ports.py                             # Interfaces (ParitariaPort, etc.)
│       └── exceptions.py                        # Excepciones de dominio de liquidación
│
├── application/                                 # 2. Capa de Aplicación (Casos de Uso y DTOs)
│   ├── use_cases/                               # Casos de uso (ParseReceiptUseCase, ProjectSalaryUseCase)
│   ├── dtos/                                    # Data Transfer Objects (ReceiptResponseDTO, SimulationDTO, etc.)
│   └── mappers/                                 # Mapeadores Entidad <-> DTO (ReceiptMapper, SimulationMapper)
│
├── adapters/                                    # 3. Capa de Adaptadores (Interface Adapters)
│   ├── controllers/                             # Inbound: controladores puros agnósticos de transporte
│   ├── gateways/                                # Outbound: pdfplumber, JSON paritarias, parsers DGCyE/Genérico
│   └── presenters/                              # Presenters de salida y formato de errores
│
├── infrastructure/                              # 4. Capa de Infraestructura (Por Librería Externa)
│   ├── fastapi/                                 # Servidor FastAPI, middlewares CORS y routers HTTP
│   │   └── routes/                              # Routers FastAPI (health, recibos, simulation)
│   ├── fastmcp/                                 # Servidores MCP (Clarity, GA4, Google Ads)
│   └── pydantic/                                # Settings con pydantic-settings
│
└── main.py                                      # Entrypoint ASGI: app = create_app()
```

---

## 🚀 Características Principales y Mitigación de Desvíos

- **Clean Architecture & DDD Temático Plano:** Desacoplamiento total entre lógica de negocio, casos de uso, adaptadores y librerías externas para un mantenimiento evolutivo de mínimo impacto y cero bugs en producción.
- **Detección Automática de Formato:** Identifica automáticamente el tipo de recibo de sueldo (DGCyE PBA vs Genérico).
- **Parser Especializado DGCyE (Buenos Aires):**
  - Extracción de cabecera de empleador y datos del agente (Nombre, DNI, CUIL, Mes de pago).
  - Parseo de la tabla de resumen de **LÍQUIDOS** con desglose por establecimiento, secuencia, fechas y órdenes de pago.
  - Desglose detallado multi-establecimiento (distrito, categoría, desfavorabilidad, etc.) y multi-cargo (secuencia, situación de revista, carga horaria, inasistencias) para auditar desvíos.
  - Clasificación tipada de conceptos en **Remunerativo**, **No Remunerativo** y **Descuento**.
  - Subtotales por secuencia y validación de totales consolidados para detectar errores de imputación contable.
- **Parser Genérico Extensible:** Soporte para recibos de sueldo tradicionales según la Ley de Contrato de Trabajo (LCT) para unificación contable.
- **Validaciones Rigurosas:** Validación de CUIT/CUIL con algoritmo Módulo 11 y formateo `XX-XXXXXXXX-X` para prevenir registros corruptos en base de datos.
- **Documentación Interactiva Interna:** Swagger UI (`/docs`) y ReDoc (`/redoc`) autodocumentados para el equipo de desarrollo de la tríada de repositorios.

---

## ⚙️ Instalación y Requisitos

### Requisitos
- Python 3.10 o superior.

### 1. Inicializar Entorno Virtual
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🧪 Ejecución de Tests

Para ejecutar la suite completa de tests unitarios e integración con `pytest`:
```bash
pytest -v
```

Para verificar calidad de código y formateo con `ruff`:
```bash
ruff check .
ruff format --check .
```

---

## 🌐 Iniciar el Servidor de Desarrollo

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 📡 Ejemplo de Uso de la API

### Endpoint: `POST /api/v1/recibos/parse`

```bash
curl -X POST "http://localhost:8000/api/v1/recibos/parse" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/36528392-2026-08-13-17_12_03_336.pdf"
```
