# Datamaq Hub - Receipt Parser API

API REST profesional construida con **FastAPI**, **Pydantic v2** y **pdfplumber** para el procesamiento, extracción y estructuración automatizada de recibos de sueldo en PDF, diseñada bajo los principios de **Clean Architecture (Robert C. Martin / Ports & Adapters)** y **Domain-Driven Design (DDD)** con organización temática del dominio.

---

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

## 🚀 Características Principales

- **Clean Architecture & DDD Temático:** Desacoplamiento total entre lógica de negocio, casos de uso, adaptadores y librerías externas.
- **Detección Automática de Formato:** Identifica automáticamente el tipo de recibo de sueldo (DGCyE PBA vs Genérico).
- **Parser Especializado DGCyE (Buenos Aires):**
  - Extracción de cabecera de empleador y datos del agente (Nombre, DNI, CUIL, Mes de pago).
  - Parseo de la tabla de resumen de **LÍQUIDOS** con desglose por establecimiento, secuencia, fechas y órdenes de pago.
  - Desglose detallado multi-establecimiento (distrito, categoría, desfavorabilidad, etc.) y multi-cargo (secuencia, situación de revista, carga horaria, inasistencias).
  - Clasificación tipada de conceptos en **Remunerativo**, **No Remunerativo** y **Descuento**.
  - Subtotales por secuencia y validación de totales consolidados.
- **Parser Genérico Extensible:** Soporte para recibos de sueldo tradicionales según la Ley de Contrato de Trabajo (LCT).
- **Validaciones Rigurosas:** Validación de CUIT/CUIL con algoritmo Módulo 11 y formateo `XX-XXXXXXXX-X`.
- **Documentación Interactiva:** Swagger UI (`/docs`) y ReDoc (`/redoc`) autodocumentados.

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
