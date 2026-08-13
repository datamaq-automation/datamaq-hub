# Datamaq Hub - Receipt Parser API

API REST profesional construida con **FastAPI**, **Pydantic v2** y **pdfplumber** para el procesamiento, extracción y estructuración automatizada de recibos de sueldo en PDF (incluyendo soporte integral para recibos multi-cargo/multi-secuencia de la **DGCyE PBA** y recibos estándar del sector privado/público).

---

## 🚀 Características Principales

- **Detección Automática de Formato:** Identifica automáticamente el tipo de recibo de sueldo (DGCyE PBA vs Genérico).
- **Parser Especializado DGCyE (Buenos Aires):**
  - Extracción completa de cabecera de organismo empleador y datos del agente (Nombre, DNI, CUIL, Mes de pago).
  - Parseo de la tabla de resumen de **LÍQUIDOS** con desglose por establecimiento, secuencia, fechas y órdenes de pago.
  - Desglose detallado multi-establecimiento (distrito, categoría, desfavorabilidad, secciones, etc.) y multi-cargo (secuencia, situación de revista, carga horaria, inasistencias).
  - Clasificación tipada de conceptos:
    - **Remunerativo** (Básico, Antigüedad, Bonificación, SAC).
    - **No Remunerativo** (FONID, Conectividad).
    - **Descuento** (IPS, IOMA, Paros, Sindicatos).
  - Subtotales por secuencia y validación de totales consolidados.
- **Parser Genérico Extensible:** Soporte para recibos de sueldo tradicionales según la Ley de Contrato de Trabajo (LCT).
- **Validaciones Rigurosas:** Validación de CUIT/CUIL con algoritmo Módulo 11, validación de DNI y normalización de importes monetarios en pesos argentinos.
- **Documentación Interactiva:** Swagger UI (`/docs`) y ReDoc (`/redoc`) autodocumentados.

---

## 📁 Estructura del Proyecto

```
datamaq-hub/
├── data/                               # Muestras de recibos en PDF
│   └── 36528392-2026-08-13-17_12_03_336.pdf
├── docs/                               # Planes y documentación arquitectónica
│   └── recibo_parser_plan.md
├── src/
│   ├── api/
│   │   ├── dependencies.py             # Inyección de dependencias
│   │   └── routes.py                   # Endpoints REST (/api/v1/recibos/parse, /api/v1/health)
│   ├── schemas/
│   │   ├── common.py                   # Envoltorios de respuesta y errores estándar
│   │   └── recibo.py                   # Modelos fuertemente tipados en Pydantic v2
│   ├── services/
│   │   ├── base_parser.py              # Interfaz abstracta y excepciones de dominio
│   │   ├── dgcye_parser.py             # Parser para DGCyE PBA
│   │   ├── generic_parser.py           # Parser genérico estándar
│   │   ├── parser_factory.py           # Factory y detector automático de recibos
│   │   └── pdf_extractor.py            # Extracción en memoria con pdfplumber
│   ├── utils/
│   │   ├── text_helpers.py             # Normalización de texto y parseo de monedas
│   │   └── validators.py               # Validador de CUIT/CUIL Módulo 11 y DNI
│   ├── config.py                       # Configuración con pydantic-settings
│   └── main.py                         # Entrada FastAPI, middlewares CORS y error handlers
├── tests/
│   ├── conftest.py                     # Fixtures y TestClient
│   ├── test_api.py                     # Tests de integración de la API
│   ├── test_dgcye_parser.py            # Test con recibo real DGCyE (4 páginas, 14 secuencias)
│   ├── test_generic_parser.py          # Tests del parser genérico
│   └── test_validators.py              # Tests de helpers y validadores
├── CONVENTIONS.md                      # Convenciones y directrices de desarrollo
├── requirements.txt                    # Dependencias del proyecto
└── README.md
```

---

## ⚙️ Instalación y Requisitos

### Requisitos
- Python 3.10 o superior.

### 1. Clonar e Inicializar Entorno Virtual
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🧪 Ejecución de Tests

Para ejecutar la suite completa de tests automatizados con `pytest`:
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

### Respuesta de Ejemplo (Estructurada)

```json
{
  "success": true,
  "data": {
    "tipo_recibo": "DGCYE_PBA",
    "empleador": {
      "organismo_o_empresa": "PROVINCIA DE BUENOS AIRES - DIRECCION GENERAL DE CULTURA Y EDUCACION",
      "dependencia": "DIRECCION GENERAL DE ADMINISTRACION",
      "cuit": "30-62739371-3"
    },
    "agente": {
      "nombre_completo": "BUSTOS AGUSTÍN",
      "tipo_documento": "DNI",
      "numero_documento": "36528392",
      "sexo": "M",
      "cuil": "20-36528392-4",
      "mes_pago": "07 / 2026"
    },
    "resumen_liquidos": [
      {
        "establecimiento_codigo": "055 IS 0199",
        "secuencia": "016",
        "periodo_liquidado": "07 / 2026",
        "fecha_pago": "07/08/2026",
        "orden_pago_codigo": "00769",
        "orden_pago_descripcion": "SDOS PRO JUL/2026 CAJ",
        "liquido_pesos": 446146.21
      }
    ],
    "liquidaciones": [
      {
        "establecimiento": {
          "codigo": "IS-0199",
          "distrito": "05-TIGRE",
          "categoria": "IS-0199",
          "desfavorabilidad": 0,
          "secciones": 23,
          "es_carcel": false,
          "doble_escolaridad": false,
          "turnos": 1,
          "nombre": "INSTITUTO SUPERIOR DE FORMACIO"
        },
        "cargo": {
          "secuencia": "016",
          "situacion_revista": "PROV.",
          "cargo_real": "SM",
          "carga_horaria": 7.0,
          "antiguedad_anios": 4,
          "dias_trabajados": 30.0,
          "inasistencias": 3.0,
          "periodo_liquidado": "202607",
          "orden_pago": "00769"
        },
        "conceptos": [
          {
            "codigo": "0220",
            "descripcion": "ANTIGUEDAD",
            "haberes": 99086.59,
            "descuentos": null,
            "tipo": "remunerativo"
          },
          {
            "codigo": "0510",
            "descripcion": "BASICO PROVISIONALES",
            "haberes": 300262.38,
            "descuentos": null,
            "tipo": "remunerativo"
          },
          {
            "codigo": "1060",
            "descripcion": "I.P.S.",
            "haberes": null,
            "descuentos": 93425.16,
            "tipo": "descuento"
          },
          {
            "codigo": "2575",
            "descripcion": "BON NO REM COMP.FONID/CONECTIV",
            "haberes": 23731.31,
            "descuentos": null,
            "tipo": "no_remunerativo"
          }
        ],
        "subtotal_haberes": 647573.48,
        "subtotal_descuentos": 201427.27,
        "liquido_calculado": 446146.21
      }
    ],
    "totales": {
      "total_haberes_remunerativos": 2865985.49,
      "total_haberes_no_remunerativos": 71754.24,
      "total_haberes": 2937739.73,
      "total_descuentos": 352316.41,
      "total_liquido": 2585423.32
    },
    "metadata": {
      "total_paginas": 4,
      "total_secuencias_liquidadas": 14,
      "total_items_resumen": 14,
      "filename": "36528392-2026-08-13-17_12_03_336.pdf"
    }
  }
}
```
