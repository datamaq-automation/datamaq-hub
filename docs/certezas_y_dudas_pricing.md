# Certezas y Dudas Estratégicas de Pricing y Monetización — DATAMAQ (2026)

> **Documento:** Marco Estratégico de Certezas, Dudas e Hipótesis de Mercado  
> **Área:** Dirección Ejecutiva (CEO - Bloque 1) y Fuentes de Ingresos (Bloque 5)  
> **Fecha de Actualización:** Agosto de 2026  
> **Marco Regulatorio:** Resolución ENRE 544/2024 · Esquema Tarifario Edenor / Edesur · Base COPIME 2026  

---

## Resumen Ejecutivo

El presente documento sistematiza los **fundamentos consolidados (Certezas)** y las **incógnitas operativas (Dudas e Hipótesis)** en torno a la estrategia de fijación de precios, arquitectura de datos y monetización de **DATAMAQ**.

Su propósito es servir como **Single Source of Truth (SSOT)** doctrinal para el Agente Principal (CEO) y los 8 subagentes del Canvas, garantizando que cada decisión de código, contenido, pauta publicitaria o negociación comercial esté anclada en datos reales y orientada al **Value-Based Pricing de Alto Ticket**.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               EL MAPA DE NAVEGACIÓN ESTRATÉGICO                                  │
├──────────────────────────────────────────────────┬───────────────────────────────────────────────┤
│            🛡️ CERTEZAS CONSOLIDADAS              │           ❓ DUDAS E HIPÓTESIS A VALIDAR      │
├──────────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 1. Arquitectura limpia (YAML + Pydantic + SaaS $0)│ 1. Elasticidad al ticket de consultoría T3 BT │
│ 2. Dolor regulatorio real (Res. ENRE 544/2024)   │ 2. Fricción en compra directa de hardware     │
│ 3. Matemática del Payback (32 a 90 días)         │ 3. Tasa de conversión a MRR DataMaq Insights  │
│ 4. OPEX ultraliviano y margen >80%               │ 4. Umbral óptimo del filtro de descarte       │
│ 5. Autoridad docente y protección de agenda      │ 5. Adopción de cuotas digitales (Pactar)      │
└──────────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

---

## PARTE I: CERTEZAS CONSOLIDADAS

Las siguientes certezas constituyen pilares inmutables del modelo. Han sido validadas tanto a nivel de código y arquitectura de software como en la estructura económica de la firma.

---

### EJE 1: Certezas de Arquitectura de Software y Código

#### C-01: El SaaS $0 como "Caballo de Troya" y Eliminador de Fricción
* **Principio:** La plataforma web de telemetría y dashboard es **100% gratuita ($0 de por vida)** para visualización básica y vitrina abierta.
* **Justificación de Negocio:** En el ecosistema PyME industrial argentino, imponer un abono mensual de software ($30–$50 USD/mes) genera resistencia de compra inmediata y alto *churn* administrativo. Al ofrecer la plataforma a $0, destruimos la barrera de entrada frente a SCADAs privativos y nos posicionamos como el **"Técnico de Cabecera"**.
* **Garantía de Software:** Incluye 60 días de Versión PRO con cada obra o consultoría. Al vencer, el cliente aporta a la Vitrina Pública Anónima o contrata el servicio ejecutivo.

#### C-02: Desacople Total de Datos (YAML SSOT + Pydantic DTOs + Dominio Puro)
* **Principio:** Cumplimiento estricto de las Reglas 2b y 3 de [AGENTS.md](file:///home/agustin/proyectos_software/www-datamaq/AGENTS.md):
  * **Datos de Contenido y Precios:** Residen exclusivamente en [data/content/pricing_structure.yaml](file:///home/agustin/proyectos_software/www-datamaq/data/content/pricing_structure.yaml) y [planes.yaml](file:///home/agustin/proyectos_software/www-datamaq/data/content/planes.yaml).
  * **Validación y Cálculo:** Se ejecutan en la capa de aplicación mediante DTOs fuertemente tipados con **Pydantic** ([src/application/dtos/pricing_dto.py](file:///home/agustin/proyectos_software/www-datamaq/src/application/dtos/pricing_dto.py)).
  * **Capa de Dominio:** Permanece 100% pura en la librería estándar de Python (`@dataclass(frozen=True)`), con cero dependencias de bases de datos o frameworks web.
* **Garantía de Integridad:** Cero datos de negocio hardcodeados en plantillas HTML ni en controladores FastAPI.

#### C-03: Tipado Estricto y Verificación Automatizada Obligatoria
* **Principio:** Todo cambio en la lógica de pricing o en los servicios debe pasar con **0 errores en Pyright/Pylance** y **450+ tests passing en Pytest** sin regresiones de cobertura.

---

### EJE 2: Certezas Regulatorias, Financieras y Unit Economics

#### C-04: La Asimetría del Dolor Regulatorio (Res. ENRE 544/2024)
* **Principio:** Las distribuidoras (Edenor / Edesur) aplican el **100% de los recargos por factor de potencia ($\cos \varphi < 0,95$)**.
* **El Riesgo de Inacción (Artículo 9):** Si el $\cos \varphi$ desciende por debajo de 0,60 (o la tangente de fi supera 1,34 en T3), la distribuidora adquiere la facultad reglamentaria de **suspender el suministro eléctrico**.
* **Impacto:** El dolor financiero para una fábrica no es una factura cara: es tener la planta parada 48 horas. DATAMAQ no vende instrumentos; **vende continuidad operativa y blindaje ante el regulador**.

#### C-05: La Matemática Demostrada del Payback Acelerado (2026)
* **Principio:** Gracias al nuevo cuadro tarifario 2026, los honorarios profesionales premium de DATAMAQ quedan completamente justificados ante un Directorio o Gerente Financiero (CFO):
  * **Caso T2 (PyME Metalúrgica Tigre):** Inversión total de ~$1.195.000 ARS vs. recargo mensual de ~$395.400 ARS $\rightarrow$ **Payback en 90 días (3 meses)**.
  * **Caso T3 BT (Inyectora de Plásticos Pilar):** Inversión total de ~$4.245.000 ARS vs. multa mensual de ~$3.931.900 ARS $\rightarrow$ **Payback en 32 días (~1 mes)**.
* **Conclusión:** El cliente amortiza la intervención en el primer trimestre exclusivamente con el dinero que deja de regalarle a la distribuidora.

#### C-06: Estructura de Costos Ultraliviana y Margen Operativo (>80%)
* **Principio:** Los costos fijos operativos de DATAMAQ son mínimos (**~$121.800 ARS/mes**, correspondientes a VPS DonWeb, póliza de Federación Patronal, dominios y cargas impositivas base).
* **Break-Even:** La facturación de **1 único servicio de peritaje o diagnóstico al bimestre** cubre el 100% del OPEX fijo. Todo ingreso adicional es margen operativo neto.

#### C-07: Palancas Comerciales de Cierre y Financiación
* **Peritaje Deducible ($55.000 ARS):** Actúa como filtro de compromiso económico y se descuenta al 100% del valor de la obra al aprobar la cotización.
* **Stacking de Descuentos (Hasta 25% OFF):** Bonificación comercial acumulable del **10% OFF para clientes de Banco Provincia (BAPRO)** y **15% OFF por adhesión al programa de Vitrina Pública (Open Telemetry)**.
* **Pactar Digital:** Financiamiento ágil en cuotas productivas con pagarés digitales **sin ticket mínimo**, permitiendo que la obra se pague sola con el flujo de ahorro mensual.

---

### EJE 3: Certezas de Posicionamiento, Autoridad y Gobernanza Canvas

#### C-08: El "Faro de Autoridad Docente" como Venta Silenciosa
* **Principio:** La autoridad técnica y pedagógica del titular (Agustín Bustos: docente ISFT 199 Tigre en Ciencia de Datos e IA, posgrado ITBA, UNPAZ) transforma a DATAMAQ de "proveedor transaccional" a **"Consultor de Cabecera"**.
* **El LMS Gratuito:** Capacita a los jefes de mantenimiento y técnicos de planta. Cuando surge una penalidad del ENRE, el personal aboga internamente por contratar a su propio docente.

#### C-09: Protección Estricta de la Agenda y Horas en Campo
* **Principio:** La docencia es la base segura y el pilar de estatus; el tiempo físico en planta se raciona estrictamente.
* **Regla:** Las visitas de peritaje en planta se coordinan **exclusivamente los días martes por la mañana**. La escasez de agenda refuerza la percepción de exclusividad y alto valor.

#### C-10: Filtro Asíncrono de Calificación en 3 Minutos
* **Principio:** Al recibir la factura de Edenor por WhatsApp, se evalúa:
  1. ¿Es tarifa T2 o T3? (Si es T1 o residencial $\rightarrow$ Descarte cortés / derivación a la web pública).
  2. ¿El monto de la multa o pérdida mensual es $\ge \$250.000\text{ ARS}$?
* **Resultado:** No se gasta tiempo técnico en prospectos que no presentan hemorragias financieras significativas.

#### C-11: Gobernanza del Canvas de 9 Bloques y Reglas Antialucinación
* **Principio:** Ningún agente de IA o documento puede inventar tarifas. Solo son válidas las cifras fijadas en [pricing_structure.yaml](file:///home/agustin/proyectos_software/www-datamaq/data/content/pricing_structure.yaml). En caso contrario, se declara `"A cotizar"`.

---

## PARTE II: DUDAS E HIPÓTESIS CRÍTICAS A VALIDAR EN CAMPO

Las siguientes son **incógnitas estratégicas abiertas**. Representan comportamientos del mercado y del cliente que deben contrastarse empíricamente durante el segundo semestre de 2026.

---

### ❓ Duda 1: Elasticidad y Aceptación del Ticket de Consultoría T3 BT ($650.000 ARS)
* **La Incógnita:** Al elevar los honorarios de consultoría de $220.000 a **$650.000 ARS** (alineados al valor hora COPIME de $34.337 ARS y al payback de 32 días), ¿el CFO de una PyME de Pilar o Garín aprobará el presupuesto en el primer contacto, o existirá fricción inicial por compararlo erróneamente con un electricista tradicional?
* **Hipótesis a Validar:** Si el informe técnico inicial cuantifica explícitamente los **$3.900.000 ARS/mes** que pierde la empresa y resalta el riesgo de corte del Artículo 9, la objeción de precio desaparece y el ticket de $650.000 ARS se percibe como una ganga.
* **Métrica de Control:** Tasa de aprobación de cotizaciones de consultoría T3 sin renegociación de honorarios (Meta: $\ge 60\%$).

---

### ❓ Duda 2: Fricción en el Esquema de Compra Directa de Hardware (Powermeter SAS)
* **La Incógnita:** Nuestro modelo estipula que el cliente adquiere el hardware directamente a Powermeter SAS a precio de lista oficial (para no inmovilizar capital ni cargar garantías), y DataMaq factura la obra WBS ($450k–$650k). ¿Perciben los clientes esto como máxima transparencia, o algunas administraciones PyME exigirán una única factura integral "llave en mano"?
* **Hipótesis a Validar:** La mayoría de las PyMEs industriales valora la transparencia de comprar al fabricante y no pagar sobreprecios de intermediación. Sin embargo, para los clientes que exijan factura única, se podría evaluar un canal con markup financiero del 15% para cubrir retenciones impositivas.
* **Métrica de Control:** Porcentaje de prospectos que solicitan facturación unificada de hardware vs. los que compran directo sin objeción.

---

### ❓ Duda 3: Conversión y Retención al MRR "DataMaq Insights" ($85k–$150k/mes)
* **La Incógnita:** Al finalizar los 60 días de Versión PRO incluida con la obra, ¿qué porcentaje de industrias contratará la suscripción mensual de reporte ejecutivo procesado con scripts de Python (*Sello de Salud Eléctrica para CFO*) vs. cuántas se conformarán con la visualización pública gratuita?
* **Hipótesis a Validar:** Las plantas T3 con auditorías de calidad frecuentes o gerencias contables estructuradas adoptarán el reporte recurrente para garantizar la no reaparición de multas antes del cierre de ciclo de Edenor.
* **Métrica de Control:** Tasa de conversión a *DataMaq Insights* al día 60 post-puesta en marcha (Meta: $\ge 25\%$ de las obras ejecutadas).

---

### ❓ Duda 4: Calibración del Umbral del Filtro de Descarte ($250.000 ARS/mes)
* **La Incógnita:** ¿El umbral de descarte tajante para multas menores a $250.000 ARS/mes resulta demasiado estricto, descartando clientes T2 chicos que podrían convertirse en obras mayores de automatización (Gateway/Automate) o predios compartidos?
* **Hipótesis a Validar:** El filtro es saludable para proteger la agenda docente y maximizar el valor de la hora de ingeniería. Los clientes con multas menores deben ser atendidos asíncronamente vía los cursos del LMS y la calculadora web.
* **Métrica de Control:** Cantidad de leads mensuales descartados y porcentaje de ellos que solicitan cotizaciones de hardware por cuenta propia tras usar la web.

---

### ❓ Duda 5: Adopción Real de la Financiación Digital con Pactar Digital
* **La Incógnita:** ¿Qué porcentaje de las PyMEs del GBA Norte prefiere financiar la intervención en cuotas mediante pagarés digitales con Pactar Digital frente a las que pagan de contado para capturar el 25% OFF acumulado (BAPRO + Vitrina)?
* **Hipótesis a Validar:** Las empresas con problemas de capital de trabajo optarán por Pactar Digital para que la cuota se pague con el ahorro de la multa; las empresas solventes preferirán el descuento agresivo del 25% de contado.
* **Métrica de Control:** Mix de pagos en los primeros 10 cierres (Meta: 40% Pactar Digital / 60% Contado con descuento).

---

### ❓ Duda 6: Demanda de Servicios Remotos Puros (Tele-Peritaje e In-Company)
* **La Incógnita:** ¿Existe un volumen significativo de demanda para el **Tele-Peritaje Forense ($150.000 ARS)** y la **Capacitación In-Company ($450.000 ARS)** en parques industriales fuera del corredor de Zona Norte (ej. Córdoba, Rosario, Mendoza) sin requerir presencia física?
* **Hipótesis a Validar:** Las empresas del interior del país que no tienen acceso a especialistas locales de telemetría Modbus/IoT pagarán con gusto un peritaje documental 100% remoto sobre sus últimas 12 facturas.
* **Métrica de Control:** Consultas orgánicas recibidas fuera del radio operativo de Zona Norte GBA.

---

## PARTE III: PROTOCOLO DE EXPERIMENTACIÓN Y VALIDACIÓN (PRIMERAS 10 COTIZACIONES)

Para despejar las dudas planteadas y calibrar los precios en tiempo real sin desestabilizar la arquitectura, se establece el siguiente protocolo de medición:

```mermaid
graph TD
    A["Lead Entrante por WhatsApp"] --> B["Auditoría Asíncrona (3 min)"]
    B -->|Multa < $250k o T1| C["Derivación a Web Pública & LMS ($0)"]
    B -->|Multa >= $250k (T2/T3)| D["Script Premium & Oferta Peritaje ($55k)"]
    D --> E["Registro en Bitácora de Experimentación"]
    E --> F["1. ¿Aceptó peritaje $55k deducible?"]
    E --> G["2. ¿Objeción al ticket de consultoría?"]
    E --> H["3. ¿Preferencia: Contado (25% OFF) o Pactar Digital?"]
    E --> I["4. ¿Compró hardware directo o pidió factura única?"]
    E --> J["5. Día 60: ¿Contrató DataMaq Insights MRR?"]
```

### Tabla de Seguimiento de Hipótesis

| Métrica / KPI | Hipótesis Esperada | Umbral de Alarma / Recalibración | Acción de Ajuste |
|---|---|---|---|
| **Conversión a Visita ($55k)** | $\ge 40\%$ de los calificados | $< 20\%$ | Reforzar el script de aversión a la pérdida (Riesgo corte Art. 9). |
| **Resistencia a Consultoría T3 ($650k)** | $< 25\%$ pide rebaja | $> 50\%$ pide rebaja | Empaquetar como "Pack Cero Multas Llave en Mano" sin desglosar honorarios. |
| **Fricción Hardware Directo** | $\ge 70\%$ compra directo a Powermeter | $> 40\%$ exige factura única | Incorporar canal de refacturación con +15% de markup administrativo. |
| **Adhesión a MRR DataMaq Insights** | $\ge 25\%$ al día 60 | $< 10\%$ | Bajar fee base a $65.000 ARS o sumar alertas de WhatsApp automáticas. |
| **Uso de Pactar Digital** | $30\% - 50\%$ de los proyectos | $< 10\%$ | Destacar más las cuotas fijas en el PDF de cotización formal. |

---

## Conclusión Ejecutiva

DATAMAQ posee una **arquitectura de software y modelo de negocio blindados**, donde la plataforma gratuita actúa como el mejor activo de adquisición y la ingeniería en campo captura rentabilidad de alto ticket. 

Las dudas existentes no son técnicas ni conceptuales, sino **variables de mercado y comportamiento del comprador** que se despejarán sistemáticamente mediante la aplicación estricta del protocolo de cotización en las próximas operaciones.
