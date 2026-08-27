# Spec: Motor de Parseo y Liquidación de Recibos de Sueldo (Clean Architecture & DDD)

> **Subsistema:** Recibos de Sueldo & Liquidación Docente/LCT  
> **Estado:** Implementado / En Producción Interna  
> **Módulos:** `src/domain/recibos`, `src/domain/liquidacion`, `src/application/use_cases`, `src/adapters/gateways/receipt_parsers`  

---

## 1. Objetivo y Alcance

### 1.1 Alcance
El subsistema de recibos procesa archivos PDF de recibos de sueldo (particularmente DGCyE de la Provincia de Buenos Aires y recibos genéricos bajo Ley de Contrato de Trabajo LCT), extrayendo la información estructurada con tipado estricto y aplicando auditoría contable para la detección de desvíos en liquidaciones.

### 1.2 Límites Arquitectónicos
- Dominio 100% puro (`@dataclass(frozen=True)` y stdlib de Python).
- Extracción de PDF encapsulada en `pdfplumber_extractor_gateway.py` (Capa Adapters).
- Controladores y Presenters desacoplados de frameworks HTTP (transporte agnóstico).
- Endpoint FastAPI expuesto en `src/infrastructure/fastapi/routes/receipt_routes.py`.

---

## 2. Modelo de Dominio & Puertos

### 2.1 Bounded Context: `src/domain/recibos/`
- **Entidades:**
  - `ReciboSueldo`: Representación agregada del recibo (id, agente, empleador, items, subtotales, líquidos, metadata).
  - `Agente`: Persona humana titular del recibo (nombre, dni, cuil).
  - `Empleador`: Entidad empleadora (razón social, cuit, domicilio).
  - `ItemRecibo`: Línea individual de concepto (código, descripción, unidades, tipo, importe).
- **Value Objects:**
  - `CUIT` / `CUIL`: Validación algorítmica por Módulo 11 con formato `XX-XXXXXXXX-X`.
  - `DNI`: Formato numérico de documento de identidad.
  - `ImporteMonetario`: Manejo inmutable de montos y redondeo a 2 decimales.
  - `TipoConcepto`: Enum (`REMUNERATIVO`, `NO_REMUNERATIVO`, `DESCUENTO`).
  - `TipoRecibo`: Enum (`DGCYE_PBA`, `GENERICO`).
- **Servicios de Dominio:**
  - `TotalesCalculator`: Sumatoria pura y validación de consistencia contable (Bruto - Descuentos = Neto).
  - `TextNormalizer`: Limpieza y sanitización de cadenas extraídas por OCR o PDF parser.
- **Puertos (`ports.py`):**
  - `PDFExtractorPort`: Interfaz abstracta para extracción de texto estructurado por coordenadas/líneas.
  - `ReceiptParserPort`: Interfaz abstracta para parsers específicos según formato.

### 2.2 Bounded Context: `src/domain/liquidacion/`
- **Entidades:**
  - `LiquidacionSalarial`: Representación de liquidación proyectada por cargo, antigüedad y horas.
  - `CargoDocente`: Secuencia, establecimiento, índice de ruralidad/desfavorabilidad, situación de revista.
- **Puertos (`ports.py`):**
  - `ParitariaPort`: Carga de escalas salariales vigentes desde persistencia desacoplada (`data/paritarias/*.json`).

---

## 3. Casos de Uso & DTOs

### 3.1 `ParseReceiptUseCase` (`src/application/use_cases/parse_receipt.py`)
1. Recibe el stream/bytes del PDF y el nombre del archivo.
2. Invoca a `PDFExtractorPort` para extraer el texto crudo estructurado.
3. Consulta al `ParserRegistryGateway` para resolver el parser adecuado (`DGCyE` o `Genérico`).
4. Ejecuta el parseo y obtiene la entidad `ReciboSueldo`.
5. Ejecuta `TotalesCalculator` para validar integridad y subtotales.
6. Mapea la entidad a `ReceiptResponseDTO` mediante `ReceiptMapper`.

### 3.2 `ProjectSalaryUseCase` (`src/application/use_cases/project_salary.py`)
1. Recibe parámetros de simulación (cargo, antigüedad, horas, período paritario).
2. Consulta `ParitariaPort` para recuperar las grillas salariales del período.
3. Calcula básicos, sumas fijas y descuentos de ley.
4. Retorna `SimulationResponseDTO`.

---

## 4. Adaptadores & Gateways

- `PdfplumberExtractorGateway`: Implementa `PDFExtractorPort` usando `pdfplumber`.
- `DgcyeParserGateway`: Parser especializado en el layout tabular y desgloses de la DGCyE PBA.
- `GenericParserGateway`: Parser heurístico para recibos estándar de nómina LCT.
- `ParserRegistryGateway`: Identifica el tipo de recibo inspeccionando encabezados clave.
- `ParitariaJsonGateway`: Carga archivos JSON versionados en `data/paritarias/` (`202607.json`, `202608.json`).
