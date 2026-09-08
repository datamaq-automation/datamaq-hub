# Plan de Mejoras: Módulo de Recibos de Sueldo Docentes DGCyE (Datamaq Hub)

## 1. Contexto y Diagnóstico Inicial

### 1.1 Localización del Servicio y Entorno
- **Instancia en producción/staging (VPS):** FastAPI escuchando en `127.0.0.1:8013` (detrás de workers uvicorn), persistiendo en `/var/www/datamaq-hub/data/leads.db`.
- **Repositorio Local:** `/home/agustin/proyectos_software/datamaq-hub`, rama `feature/recibos-mejoras-dgcye`.
- **Caso Real de Referencia:** Recibo `AGO/2026` del docente CUIT `20-36528392-4`, archivo PDF `data/36528392-2026-09-07.pdf` (id en VPS: `a6c1baa7-a9c2-4d97-8624-a68c98940e52`).
  - Total declarado en cabecera de líquidos: `$1.584.497,13`.
  - 11 líneas en resumen de líquidos:
    - `055 IS 0199` Sec `016`: 2 líneas (nominal `$457.570,43` + retroactivo `$24.270,92`).
    - `055 IS 0199` Sec `021`: 1 línea (`$315.953,81`).
    - `055 IS 0199` Sec `022`: 1 línea (`$315.953,81`).
    - `055 MT 0002` Sec `017`: 1 línea (`$114.033,94`).
    - `055 MT 0003` Sec `020`: 2 líneas (`$10.278,87` + `$67.474,01`).
    - `116 MT 0001` Sec `023`: 2 líneas (`$83.539,25` + `$74.588,56`).
    - `116 MT 0001` Sec `024`: 2 líneas (`$83.539,25` + `$37.294,28`).
  - Conciliación histórica actual: 9 líneas conciliadas (7 exactas + 2 retroactivas), 2 huérfanas de recibo (Sec `024` Escobar, `$120.833,53`), 8 designaciones vigentes sin liquidar en agosto.

### 1.2 Hallazgos de Dominio en el PDF DGCyE PBA
1. **Códigos de Establecimiento (`055 IS 0199` / `116 MT 0001`):**
   - Primer bloque de 3 dígitos (`055`, `116`): Código distrital DGCyE (055 = Tigre, 116 = Escobar).
   - Segundo bloque (`IS`, `MT`): Nivel o modalidad (`IS` = Instituto Superior / Superior Técnica, `MT` = Media Técnica / Secundaria Técnica).
   - Tercer bloque (`0199`, `0001`): Número identificador de la institución/escuela.
2. **Órdenes de Pago Presupuestarias (`00871`, `00877`) y Sufijos:**
   - `00871`: Orden de Pago de haberes docentes para cargos **Provisionales** (`SDOS PRO`).
   - `00877`: Orden de Pago de haberes docentes para cargos **Suplentes** (`SDOS SUP`).
   - `CAJ`: Modalidad de acreditación mediante cajero automático (Red Link / Banco Provincia).
3. **Desdoblamiento de Liquidaciones:**
   - Un mismo cargo/secuencia puede aparecer múltiples veces en el mismo recibo si percibe liquidación del período nominal concurrente con diferencias retroactivas de meses anteriores (ej: paritarias o ajustes de inasistencias).

---

## 2. Diseño de las 8 Mejoras (Arquitectura y Contratos)

### Mejora 1: Línea Estructurada con Taxonomía Tipada
- **Dominio (`src/domain/recibos/`):**
  - En `ResumenLiquidoItem`, enriquecer con campos estructurados opcionales (100% retrocompatible):
    - `distrito: str | None` (ej: `"055"`)
    - `tipo_nivel: str | None` (ej: `"IS"`, `"MT"`)
    - `escuela: str | None` (ej: `"0199"`, `"0001"`)
    - `secuencia: str`
    - `revista: str | None` (`"PRO"` o `"SUP"`)
    - `orden_pago: str | None` (ej: `"00871"`)
    - `periodo_liquidado: str` (formato `"YYYY-MM"` o `"MM / YYYY"`)
    - `fecha_pago: str` (formato `"DD/MM/YYYY"`)
    - `importe: float` (alias/espejo tipado de `liquido_pesos`)
    - `concepto_normalizado: str` (`"sueldo"`, `"retroactivo"`, `"SAC"`, `"otros"`)
  - En `dgcye_parser_gateway.py`: Al parsear la sección de líquidos y correlacionar con las liquidaciones de conceptos, tipar y clasificar el concepto normalizado según fecha devengada y códigos (0820/0821 -> SAC, periodo < mes_pago -> retroactivo, periodo == mes_pago -> sueldo, otros).
- **Aplicación (`src/application/dtos/receipt_dto.py`):**
  - Añadir los nuevos campos a `ResumenLiquidoItemDTO` con defaults `None` para preservar contratos vigentes.
- **Aceptación:** El recibo AGO/2026 re-parseado expone esos campos sin error y los campos legacy siguen idénticos.

### Mejora 2: Conciliación por Cargo (Agrupada por Escuela + Secuencia)
- **Dominio (`src/domain/recibos/`):**
  - En `entities.py`:
    - Modelo `CargoConciliado`:
      - `secuencia: str`
      - `escuela_codigo: str`
      - `id_designacion: str | None`
      - `revista_recibo: str`
      - `revista_designacion: str | None`
      - `modulos_recibo: float`
      - `modulos_designacion: float | None`
      - `importe_total: float` (suma de importes netos de todas las líneas del cargo)
      - `cantidad_lineas: int`
      - `estado: EstadoLineaConciliacion`
      - `lineas_explicadas: list[LineaConciliada]` (las N líneas componentes con sus periodos e importes)
      - `observacion: str`
    - Añadir a `ResultadoConciliacion`: `cargos_conciliados: list[CargoConciliado]` y `cargos_huerfanos_recibo: list[CargoConciliado]`.
  - En `services.py` (`ConciliadorReciboDocenteService`):
    - Agrupar líneas por clave `(escuela_codigo, secuencia)`.
    - La conciliación evalúa el cargo consolidado frente a las designaciones disponibles sin fragmentar la búsqueda en falsos huérfanos cuando un cargo se liquida en 2 o más líneas (ej. sec `016`).
- **Aplicación (`src/application/dtos/conciliacion_dto.py`):**
  - `CargoConciliadoDTO` expuesto en `ConciliacionResponseDTO.cargos_conciliados` conviviendo con `lineas_conciliadas` para retrocompatibilidad total.
- **Aceptación:** Sec `016` concilia como 1 cargo consolidado con 2 líneas explicadas (`$457.570,43` y `$24.270,92`).

### Mejora 3: Integridad de Cierre ($\sum \text{líneas} == \text{total}$)
- **Dominio (`src/domain/recibos/`):**
  - Extraer del PDF la línea `TOTAL <importe>` del resumen de líquidos.
  - En `TotalesConsolidados`:
    - `total_declarado: float | None = None`
    - `diferencia_cierre: float = 0.0`
    - `estado_cierre: str = "SIN_TOTAL"` (`"VALIDO"`, `"DISCREPANCIA"`, `"SIN_TOTAL"`)
  - Si el PDF no declara total, no bloquear el parsing y reportar `"SIN_TOTAL"`.
- **Persistencia y DTO:**
  - Columnas en DB y campos en `ReceiptResponseDTO` y `ConciliacionResponseDTO`: `estado_cierre`, `total_declarado`, `diferencia_cierre`.
- **Aceptación:** Recibo AGO/2026 reporta `estado_cierre: "VALIDO"`, `total_declarado: 1584497.13`, `diferencia_cierre: 0.0`.

### Mejora 4: Dedupe e Idempotencia por Fingerprint de Archivo
- **Dominio / Gateway (`sql_recibo_gateway.py`):**
  - Calcular fingerprint SHA-256 del contenido binario del PDF.
  - Guardar `pdf_hash` indexado en `recibos_sueldo`.
  - Migración segura no destructiva: `ALTER TABLE recibos_sueldo ADD COLUMN pdf_hash VARCHAR(64)`.
  - Si se reenvía un archivo con el mismo `pdf_hash` o combinación `(docente_cuit, mes_pago, pdf_hash)`:
    - Retornar el recibo existente con flag `es_duplicado: True` en metadata/DTO.
    - No insertar un nuevo registro en la base de datos.
- **Aceptación:** Dos llamadas consecutivas a `POST /api/v1/recibos/parse` con el mismo PDF resultan en exactamente 1 recibo en la base de datos.

### Mejora 5: Seguimiento Diferido de No Liquidados y Detección de 2 Períodos
- **Modelo de Datos y Persistencia:**
  - Nueva tabla/entidad `designaciones_no_liquidadas`:
    - `id: int (PK)`
    - `id_recibo_origen: str` (UUID del recibo auditado)
    - `id_designacion: str` (UUID de la designación vigente no liquidada)
    - `docente_cuit: str`
    - `mes_pago_no_liquidado: str` (ej: `"2026-08"`)
    - `escuela_codigo: str`
    - `secuencia: str`
    - `modulos: float`
    - `revista: str`
    - `periodos_consecutivos: int` (contador acumulativo)
    - `alerta_2_periodos: bool` (`True` si `periodos_consecutivos >= 2`)
    - `estado: str` (`"PENDIENTE"`, `"LIQUIDADA_POSTERIOR"`)
    - `resuelto_en_recibo_id: str | None`
    - `creado_en: datetime`
- **Lógica de Cruce Automático:**
  - Al conciliar período $N$, consultar registros previos en estado `"PENDIENTE"`. Si una designación que figuraba no liquidada en período $N-1$ aparece liquidada en el recibo de $N$, transicionar a `"LIQUIDADA_POSTERIOR"` vinculando el recibo actual.
  - Si sigue sin liquidarse, incrementar `periodos_consecutivos` y encender `alerta_2_periodos = True`.
- **Endpoints:**
  - `GET /api/v1/recibos/{id_recibo}/no-liquidados`
  - `GET /api/v1/recibos/no-liquidados` (con filtros `cuit`, `solo_alertas=true`).
- **Aceptación:** Consultable vía API; detecta y marca alertas al encadenar períodos sin cobro.

### Mejora 6: Alta de Huérfanas con Propuesta Revisable
- **Casos de Uso y Endpoints:**
  - `GET /api/v1/recibos/{id_recibo}/propuestas-huerfanas`:
    - Ejecuta/consulta la conciliación y retorna borradores estructurados listos para revisión docente:
      `[{"propuesta_id": "...", "secuencia": "024", "escuela": "11-ESCOBAR MT-0001", "periodo": "2026-06", "revista": "SUP", "monto": 37294.28, "modulos": 4.0, ...}]`.
  - `POST /api/v1/recibos/{id_recibo}/confirmar-propuestas-huerfanas`:
    - Recibe payload con `propuestas_confirmadas: list[PropuestaDesignacionConfirmadaDTO]`.
    - Valida datos en bulk e inserta únicamente las seleccionadas/editadas por el usuario en `horarios_designaciones`.
  - `POST /api/v1/recibos/{id_recibo}/crear-designaciones-huerfanas` existente:
    - Se mantiene 100% operativo sin cambios que rompan compatibilidad.
- **Aceptación:** Generación de propuestas revisables y creación selectiva bulk validada.

### Mejora 7: Desglose "Período Neto vs Arrastre"
- **Lógica Financiera:**
  - Descomponer el neto total del recibo en:
    - `importe_periodo_nominal`: Líneas cuyo devengado coincide con el `mes_pago` y conceptos corrientes.
    - `importe_retroactivos`: Líneas con devengado anterior al `mes_pago` o conceptos de retroactividad.
    - `importe_sac`: Conceptos de aguinaldo (`0820`, `0821`).
    - `importe_otros`: Otros conceptos o deducciones específicas.
- **Exposición:**
  - Campo `desglose: DesgloseFinancieroDTO` en `ReceiptResponseDTO`.
  - Endpoint dedicado: `GET /api/v1/recibos/{id_recibo}/desglose`.
- **Aceptación:** AGO/2026 desglosa con exactitud matemática el total neto ($1.584.497,13).

### Mejora 8: Export CSV del Conciliado
- **Endpoint:**
  - `GET /api/v1/recibos/{id_recibo}/conciliacion/export.csv`
- **Especificación Técnica:**
  - Content-Type: `text/csv; charset=utf-8`.
  - Content-Disposition: `attachment; filename="conciliacion_{id_recibo}_{mes_pago}.csv"`.
  - Separador: `;` (estándar regional argentino/hispano para compatibilidad nativa con Excel).
  - Columnas fijas:
    `tipo_registro;secuencia;escuela_codigo;periodo_liquidado;revista_recibo;revista_designacion;modulos_recibo;modulos_designacion;liquido_pesos;estado;es_retroactivo;id_designacion;observacion`
- **Aceptación:** Descarga HTTP 200 con archivo CSV bien formateado y parseable.

---

## 3. Matriz de Dependencias y Orden de Ejecución

1. **Paso 1:** Mejora 4 (Dedupe & Idempotencia) + Migración DB segura de `recibos_sueldo`.
2. **Paso 2:** Mejora 1 (Línea estructurada & Taxonomía de conceptos) + Mejora 3 (Integridad de cierre).
3. **Paso 3:** Mejora 2 (Conciliación por cargo con líneas explicadas).
4. **Paso 4:** Mejora 7 (Desglose Período Neto vs Arrastre / SAC).
5. **Paso 5:** Mejora 8 (Export CSV de conciliación).
6. **Paso 6:** Mejora 5 (Seguimiento diferido de no liquidados y alertas consecutivas).
7. **Paso 7:** Mejora 6 (Alta de huérfanas con propuesta revisable y confirmación bulk).
8. **Paso 8:** Verificación integral con test de integración AGO/2026, suite completa `./scripts/pre-push.sh` y validación de OpenAPI.

---

## 4. Estrategia de Migraciones y Preservación de Datos
- Las tablas existentes (`recibos_sueldo`, `horarios_designaciones`) no pierden columnas ni alteran sus tipos.
- SQLite admite `ALTER TABLE ... ADD COLUMN` sin recrear tablas ni bloquear datos.
- Las nuevas entidades (`designaciones_no_liquidadas`) se inicializan limpiamente con `Base.metadata.create_all(engine)`.
- Todo acceso a datos existentes preserva el formato JSON de recibos históricos ya guardados.
