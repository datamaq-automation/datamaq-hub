# Especificación Técnica: Tablero Kanban y Red PERT-CPM Dinámica

> **Ámbito:** Bounded Context `planificacion` en `datamaq-hub`.  
> **Patrón:** Clean Architecture + Domain-Driven Design (DDD) + Spec-Driven Development (SDD).  
> **Estado:** **Aprobado / Implementado**

---

## 1. Propósito y Alcance

Proveer un motor determinístico y agnóstico de infraestructura para la gestión de proyectos y planes de inserción laboral o técnica (inicialmente centrado en el plan de Vaca Muerta, escalable a cualquier plan de automatización o despliegue industrial).

El subsistema expone una API REST reactiva que combina:
1. **Tablero Kanban:** Agrupación dinámica de tareas en tres estados de ciclo de vida (`PENDIENTE`, `EN_PROCESO`, `COMPLETADA`).
2. **Análisis Algorítmico PERT-CPM:** Cálculo probabilístico de duraciones esperadas, varianzas, holguras totales, camino crítico, rutas subcríticas e intervalos de confianza al 95% ($\pm 1.96\sigma$).
3. **Diagrama Mermaid Dinámico:** Representación gráfica vectorial de la red de precedencias con estilizado condicional (camino crítico resaltado, hitos completados y duraciones).
4. **Persistencia Externa en YAML:** Gestión de planes sin datos hardcodeados en código Python (`data/pert/{id_plan}.yaml`).

---

## 2. Arquitectura y Modelo de Dominio (`src/domain/planificacion/`)

El dominio es 100% puro (solo Python Standard Library y `@dataclass(frozen=True)`):

### 2.1. Value Objects (`value_objects.py`)
- `EstadoTareaPlan(str, Enum)`: `PENDIENTE`, `EN_PROCESO`, `COMPLETADA`.
- `EstimacionPert`: Tupla `(optimista, mas_probable, pesimista)` con validación $o \le m \le p$.
  - Duración esperada: $T_e = \frac{o + 4m + p}{6}$
  - Varianza: $\sigma^2 = \left(\frac{p - o}{6}\right)^2$
- `TiemposCpm`: Tupla de tiempos CPM:
  - `early_start` ($ES$), `early_finish` ($EF$)
  - `late_start` ($LS$), `late_finish` ($LF$)
  - `holgura_total`: $H_T = LS - ES = LF - EF$

### 2.2. Entidades (`entities.py`)
- `TareaPlan`:
  - `id: str` (ej. `A1`, `B1`, `C2`)
  - `titulo: str`, `descripcion: str`, `fase: str`, `responsable: str`
  - `estado: EstadoTareaPlan`
  - `predecesores: tuple[str, ...]`
  - `estimacion: EstimacionPert`
  - `tiempos: TiemposCpm | None`
  - Propiedades: `es_critica` ($H_T = 0$), `es_subcritica` ($0 < H_T \le 1.0$).
- `TableroKanban`:
  - Agrupaciones: `pendientes`, `en_proceso`, `finalizadas`.
  - Métricas globales: duración esperada total, varianza acumulada en camino crítico, desviación estándar total, intervalo de confianza al 95%, camino crítico, camino subcrítico, porcentaje de avance.
  - Diagrama Mermaid: sintaxis generada para visualización gráfica.

### 2.3. Servicio de Dominio (`services.py`)
- `CalculadorPertCpmService`:
  - Ordenamiento topológico con detección determinística de ciclos (`CicloEnGrafoPertError`).
  - Forward Pass (cálculo de $ES$ y $EF$).
  - Backward Pass (cálculo de $LF$, $LS$ y holgura total).
  - Identificación del camino crítico ($H_T = 0$) y subcrítico ($0 < H_T \le 1.0$).
  - Cálculo de varianza total $\sigma_{total}^2 = \sum_{i \in CP} \sigma_i^2$ e intervalo de confianza del 95%: $[T_e - 1.96\sigma, T_e + 1.96\sigma]$.
  - Generación de código Mermaid `graph LR`.

### 2.4. Puertos (`ports.py`)
- `PlanificacionRepositoryPort`:
  - `obtener_tablero(id_plan: str) -> TableroKanban`
  - `actualizar_estado_tarea(id_tarea: str, nuevo_estado: EstadoTareaPlan, id_plan: str) -> TableroKanban`

---

## 3. Capa de Aplicación (`src/application/`)

- **DTOs (`dtos/planificacion_dtos.py`):**
  - `TareaPlanDTO`, `EstimacionPertDTO`, `TiemposCpmDTO`, `MetricasProyectoDTO`, `TableroKanbanDTO`, `CambiarEstadoTareaPlanDTO`.
- **Mappers (`mappers/planificacion_mapper.py`):**
  - `PlanificacionMapper.tablero_to_dto(tablero: TableroKanban) -> TableroKanbanDTO`.
- **Casos de Uso (`use_cases/planificacion/`):**
  - `ObtenerTableroKanbanPertUseCase`: Orquesta la carga y mapeo del tablero.
  - `ActualizarEstadoTareaPlanUseCase`: Valida la transición de estado y delega al repositorio.

---

## 4. Adaptadores (`src/adapters/`)

- **Gateway (`gateways/planificacion/yaml_planificacion_gateway.py`):**
  - Lee y parsea `data/pert/{id_plan}.yaml`.
  - Ejecuta `CalculadorPertCpmService` para hidratar las entidades con tiempos CPM y métricas.
  - Al mutar una tarea, persiste atómicamente el nuevo estado en el archivo YAML y actualiza la caché en memoria.
- **Controlador (`controllers/planificacion_controller.py`):**
  - Clase pura agnóstica de frameworks web.
- **Presenter (`presenters/error_presenter.py`):**
  - Mapeo de excepciones de dominio:
    - `PlanNoEncontradoError` ➔ HTTP 404 (`PLAN_NO_ENCONTRADO`).
    - `TareaPlanNoEncontradaError` ➔ HTTP 404 (`TAREA_PLAN_NO_ENCONTRADA`).
    - `TareaPlanInvalidaError` ➔ HTTP 422 (`TAREA_PLAN_INVALIDA`).
    - `CicloEnGrafoPertError` ➔ HTTP 400 (`CICLO_EN_GRAFO_PERT`).

---

## 5. Capa de Infraestructura (`src/infrastructure/fastapi/`)

### 5.1. Endpoints REST

#### `GET /api/v1/planificacion/kanban`
- **Query Params:**
  - `id_plan: str` (opcional, por defecto `"vaca_muerta"`).
- **Respuesta Exitosa (HTTP 200):**
```json
{
  "success": true,
  "data": {
    "id_plan": "vaca_muerta",
    "titulo_plan": "Inserción Laboral en Vaca Muerta (Cuenca Neuquina)",
    "descripcion_plan": "Ruta crítica y tablero de tareas...",
    "pendientes": [...],
    "en_proceso": [...],
    "finalizadas": [...],
    "metricas": {
      "duracion_esperada": 36.53,
      "varianza_total": 3.03,
      "desviacion_estandar": 1.74,
      "intervalo_confianza_95_min": 33.12,
      "intervalo_confianza_95_max": 39.94,
      "camino_critico": ["A1", "A2", "B1", "B2", "C1", "D1", "D2", "E1", "E2"],
      "camino_subcritico": ["C2"],
      "total_tareas": 14,
      "tareas_pendientes": 14,
      "tareas_en_proceso": 0,
      "tareas_completadas": 0,
      "porcentaje_avance": 0.0
    },
    "diagrama_mermaid": "graph LR\n..."
  }
}
```

#### `PATCH /api/v1/planificacion/tareas/{id_tarea}/estado`
- **Path Params:** `id_tarea: str` (ej. `A1`).
- **Query Params:** `id_plan: str` (opcional, por defecto `"vaca_muerta"`).
- **Body:**
```json
{
  "estado": "EN_PROCESO"
}
```
- **Respuesta Exitosa (HTTP 200):**
  - Devuelve el `TableroKanbanDTO` recalculado al instante.
