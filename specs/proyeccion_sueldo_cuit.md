# Especificación: Proyección Salarial Docente One-Click por CUIT

## 1. Objetivo y Contexto

Automatizar el cálculo y proyección del sueldo docente de la DGCyE PBA para un CUIT específico y período solicitado. Esta funcionalidad permite que sistemas externos (OpenClaw, dashboards) obtengan una estimación salarial precisa a partir de la información de designaciones vigentes y recibos históricos almacenados, sin requerir la entrada manual de la grilla de módulos.

**Problema:** El caso de uso actual `ProjectSalaryUseCase` requiere ingresar manualmente la lista de designaciones en el payload. Para automatizar las consultas, necesitamos inferir las designaciones vigentes en el mes, calcular sus días proporcionales reales (altas/bajas) y obtener la antigüedad acumulada desde el último recibo liquidado.

**Alcance:**
- Crear el caso de uso `ProyectarSueldoDocenteVigenteUseCase`.
- Consultar las designaciones del CUIT vigentes en el período solicitado (ej. `202608`) usando `DesignacionDocenteRepositoryPort`.
- Calcular los días trabajados proporcionales por cada designación en base a su `fecha_desde` y `fecha_hasta`.
- Extraer la antigüedad del docente a partir de su recibo más reciente en `ReciboRepositoryPort`.
- Resolver la paritaria correspondiente al período solicitado.
- Calcular los escenarios: Bruto/Neto Regular Asegurado, Devengado Proporcional Total, y Retroactivo Estimado.
- Exponer el endpoint `POST /api/v1/simulacion/docente/{cuit}`.

---

## 2. Lógica de Proyección y Días Proporcionales

### 2.1 Inferencia de Días Trabajados
Para un mes de liquidación dado (período `YYYYMM`, interpretado con mes comercial de 30 días):
- Si una designación tiene `fecha_desde` dentro del mes evaluado:
  $$\text{dia\_inicio} = \text{fecha\_desde.day}$$
  $$\text{dias\_trabajados} = 30 - \text{dia\_inicio} + 1$$
  *(Si es mayor a 30, se limita a 30; si es menor a 0, se limita a 0).*
- Si una designación tiene `fecha_hasta` dentro del mes evaluado:
  $$\text{dia\_fin} = \text{fecha\_hasta.day}$$
  $$\text{dias\_trabajados} = \text{dia\_fin}$$
  *(Limitado a un máximo de 30).*
- Si no hay novedades en el mes (la designación cubre todo el mes):
  $$\text{dias\_trabajados} = 30.0$$

### 2.2 Inferencia de Tipo de Cargo
- Se clasifica el cargo según el nivel registrado en la designación (`SM` para módulos de Secundaria, `PM` para módulos de Primaria/Media/Superior).

---

## 3. Contratos y DTOs

### 3.1 DTO de Entrada (`SimulacionSueldoCuitRequestDTO`)
No requiere payload en el body. Parámetros query opcionales:
- `periodo` (string, `YYYYMM`, opcional, default: mes actual).

### 3.2 DTO de Salida (`SimulacionSueldoCuitResponseDTO`)
```python
class ProyeccionEscenarioDTO(BaseModel):
    total_haberes: float
    total_descuentos: float
    total_liquido: float

class SimulacionSueldoCuitResponseDTO(BaseModel):
    cuit: str
    docente_nombre: str
    periodo_proyectado: str
    anios_antiguedad: int
    modulos_totales: float
    
    # Los 3 escenarios de la proyección
    escenario_base_asegurado: ProyeccionEscenarioDTO
    escenario_devengado_total: ProyeccionEscenarioDTO
    retroactivo_estimado: float
    
    # Desglose de cargos liquidados en el devengado total
    cargos_liquidados: list[CargoLiquidadoDTO]
```

---

## 4. Matriz de Pruebas (RED Suite)

| ID | Escenario | Entrada | Verificación |
|---|---|---|---|
| PSC-1 | CUIT sin designaciones vigentes | CUIT válido, período `202608` | Lanza `DocenteSinDesignacionesException` o retorna lista vacía. |
| PSC-2 | Cálculo de días proporcionales de alta | `fecha_desde = 2026-08-13` | `dias_trabajados == 18.0` |
| PSC-3 | Cálculo de días proporcionales de baja | `fecha_hasta = 2026-08-10` | `dias_trabajados == 10.0` |
| PSC-4 | Inferencia de antigüedad | Docente con recibo de 4 años | `anios_antiguedad == 4` (aplica 33%) |
| PSC-5 | Flujo completo con tope de 30 módulos | Docente con 31 módulos | Secuencia 20 liquidada con 1 módulo bonificable |
