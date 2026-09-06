# Búsqueda Laboral en Vaca Muerta — Datamaq Hub

> **Ámbito:** Guía operativa, fundamentos estratégicos y manual de uso del motor de búsqueda laboral para la cuenca neuquina (Vaca Muerta / Río Negro).  
> **Patrón:** Clean Architecture + DDD + Consultas Manuales bajo demanda.

---

## 1. Fundamento Estratégico y Diagnóstico de Mercado

Un análisis empírico de la demanda de trabajo formal en Argentina revela una particularidad crítica para las industrias extractivas:

1. **Inviabilidad de los portales masivos:**
   - Según la Clasificación Industrial Internacional Uniforme (CIIU), el sector 4 (**explotación de minas, canteras y extracción de hidrocarburos**) aporta apenas entre el **0.1% y el 0.3%** del total de avisos en portales de empleo masivos como ZonaJobs, Computrabajo o Bumeran.
   - Las grandes operadoras de Oil & Gas **no publican sus vacantes críticas en agregadores masivos**.
2. **Canales reales de contratación:**
   - **Sistemas ATS Propietarios:** Portales corporativos directos montados sobre SAP SuccessFactors, Taleo o Workday.
   - **Proveedores de Servicios Petroleros:** Empresas contratistas de campo (servicios de pozo, wireline, coiled tubing, compresión, mantenimiento de plantas).
   - **Vínculos institucionales y redes de la cuenca:** Colegios de ingenieros/técnicos locales, cámaras del sector (CEPH, CEOPE, IAPG) y sedes universitarias regionales.
3. **El perfil más demandado en la transformación industrial:**
   - La industria argentina no busca científicos de datos puramente teóricos en estructuras corporativas masivas; demanda **Analistas de Datos / Especialistas en Confiabilidad** con comprensión profunda del proceso físico (fierro, variadores, instrumentación, media tensión) capaces de convertir lecturas y telemetría en acciones concretas de negocio y mantenimiento (Asset Performance Management - APM).

---

## 2. Fuentes Conectadas (Multifuente)

Datamaq Hub implementa gateways dedicados que consultan directamente las APIs/endpoints de los ATS corporativos de las operadoras:

| Operadora | Gateway | Identificador | Enfoque Principal |
|---|---|---|---|
| **YPF S.A.** | `YpfTalentGateway` | `FuenteOferta.YPF` | Operaciones upstream, yacimientos no convencionales, plantas y refinerías. |
| **Tecpetrol (Grupo Techint)** | `TecpetrolTalentGateway` | `FuenteOferta.TECPETROL` | Fortín de Piedra (principal yacimiento de gas de Vaca Muerta) e infraestructura asociada. |
| **Pan American Energy (PAE)** | `PaeTalentGateway` | `FuenteOferta.PAE` | Operaciones en Lindero Atravesado, Bandurria Centro, Coirón Amargo y plantas de tratamiento. |
| **Vista Energy** | `VistaTalentGateway` | `FuenteOferta.VISTA` | Bajada del Palo Oeste/Este, Águila Mora y desarrollos de alta eficiencia en crudo no convencional. |

---

## 3. Perfil Profesional de Agustín Leonardo Bustos

El motor incorpora de forma nativa la factoría `obtener_perfil_agustin_bustos()` (`src/domain/empleo/entities.py`), sintetizada a partir de su trayectoria técnica:

- **Rol Principal:** Especialista en Confiabilidad Operacional y Desempeño de Activos (APM) / Mantenimiento Industrial.
- **Competencias Físicas e Industriales:** Mantenimiento electromecánico y eléctrico en plantas continuas, variadores de frecuencia (VFD: Siemens, Schneider, ABB), tableros BT, CCM, celdas MT (13.2kV), grupos electrógenos, instrumentación, neumática e hidráulica, compresores a tornillo, solar FV, LOTO y 5 Reglas de Oro.
- **Competencias Digitales e IoT:** Telemetría en tiempo real, Smart Meters, desarrollo de GMAO a medida, programación Python, Machine Learning e IA aplicada al diagnóstico de condición (CBM / Mantenimiento Predictivo).
- **Zonas Objetivo:** Añelo, Neuquén, Río Negro, Rincón de los Sauces, Plaza Huincul, Cutral Co, Catriel, Allen, Cipolletti.
- **Modalidades Admitidas:** Rotacional de yacimiento (diagramas 14x14, 7x7), presencial, híbrido o remoto.

---

## 4. Guía de Uso (100% Manual / Bajo Demanda)

Por diseño doctrinal, la búsqueda **no se ejecuta en segundo plano** ni envía alertas automáticas; se corre exclusivamente cuando el usuario lo decide.

### Opción A: Interfaz CLI por Terminal

El script [`scripts/buscar_empleo_vaca_muerta.py`](../scripts/buscar_empleo_vaca_muerta.py) permite realizar búsquedas inmediatas:

```bash
# 1. Búsqueda por defecto con tu perfil y las 4 fuentes
python scripts/buscar_empleo_vaca_muerta.py

# 2. Búsqueda refinando términos técnicos
python scripts/buscar_empleo_vaca_muerta.py -k confiabilidad telemetria scada

# 3. Filtrando por localidad específica dentro de la cuenca
python scripts/buscar_empleo_vaca_muerta.py -u Añelo

# 4. Ajustando el umbral de afinidad mínima (0 a 100)
python scripts/buscar_empleo_vaca_muerta.py -m 50.0
```

### Opción B: Endpoints de la API REST

El servidor expone rutas bajo `/api/v1/empleo`:

- **GET `/api/v1/empleo/vaca-muerta`**:
  - Parámetros opcionales: `q` (términos), `ubicacion`, `solo_vaca_muerta` (default: true), `min_score` (default: 0.0).
  - Ejemplo:
    ```bash
    curl -sS "http://localhost:8000/api/v1/empleo/vaca-muerta?q=confiabilidad&min_score=40" | jq
    ```

- **POST `/api/v1/empleo/vaca-muerta`**:
  - Permite enviar un cuerpo JSON con un perfil alternativo para simular otros perfiles de búsqueda.

---

## 5. Mantenimiento y Verificación

- La suite de pre-push verifica el bounded context de empleo:
  ```bash
  ./scripts/pre-push.sh
  ```
- Tests unitarios e integración:
  ```bash
  pytest tests/unit/test_empleo* tests/unit/test_ypf* tests/unit/test_tecpetrol* tests/unit/test_pae_vista* tests/integration/test_empleo*
  ```
