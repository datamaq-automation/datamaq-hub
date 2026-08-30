# Especificación: Inversión de Dependencias (DIP) de Logging en Gateways y Use Cases

## 1. Objetivo y Contexto

Desacoplar la capa de adaptadores (`src/adapters/gateways/`) y de aplicación (`src/application/use_cases/`) de la librería concreta `logging` de Python, canalizando todos los registros a través de un puerto de dominio puro (`LoggerPort`) inyectado por constructor (DIP).

**Problema:** 10 gateways y 2 use cases importan `logging` a nivel de módulo (`logger = logging.getLogger(__name__)`), violando la dirección de dependencias de Clean Architecture. La auditoría `agy-opt audit-dip` reporta estas dependencias como violaciones DIP.

**Alcance:**
- Definir `LoggerPort` (Protocol) y `NullLogger` (no-op) en dominio puro.
- Definir `StandardLogger` en infraestructura (envuelve `logging.getLogger`).
- Refactorizar los 12 componentes para recibir `logger: LoggerPort | None = None` por constructor, con fallback seguro a `NullLogger()`.
- Resolver `agy-opt audit-dip` en 0 violaciones.

**Fuera de alcance:** No se modifica la semántica de los mensajes de log ni el comportamiento observable de los gateways/usecases. No se cambian firmas de métodos públicos distintos de `__init__`.

## 2. Dominio & Puertos

### 2.1 `LoggerPort` (Protocol)

```python
from typing import Protocol

class LoggerPort(Protocol):
    """Contrato de logging puro para Clean Architecture (métodos no-op en NullLogger)."""

    def debug(self, message: str, *args: object) -> None: ...
    def info(self, message: str, *args: object) -> None: ...
    def warning(self, message: str, *args: object) -> None: ...
    def error(self, message: str, *args: object) -> None: ...
    def exception(self, message: str, *args: object) -> None: ...
```

### 2.2 `NullLogger` (implementación no-op)

Clase concreta que implementa `LoggerPort` sin efectos secundarios. Es el fallback seguro cuando no se inyecta logger (tests unitarios, dependencias mínimas).

## 3. Infraestructura

### 3.1 `StandardLogger`

```python
class StandardLogger(LoggerPort):
    """Adaptador de infraestructura que envuelve logging.getLogger(name)."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
    # delega debug/info/warning/error/exception a self._logger
```

## 4. Matriz de Pruebas (RED Suite)

| ID | Escenario | Verificación |
|---|---|---|
| LP-1 | `NullLogger` acepta llamadas `debug/info/warning/error/exception` sin levantar excepción | No-op silencioso |
| LP-2 | `LoggerPort` es un Protocol con los 5 métodos | `isinstance`/`hasattr` estructural |
| SL-1 | `StandardLogger` delega a `logging.getLogger(name)` | Captura vía handler en memoria |
| SL-2 | `StandardLogger.exception` propaga con traceback | Nivel ERROR emitido |

## 5. Criterios del Gauntlet

1. `agy-opt audit-dip` → `✅ [DIP 100% VÁLIDO]`.
2. `./scripts/pre-push.sh` → 0 violaciones arquitectura, 0 errores ruff, 0 errores pyright, `__init__.py` 0 bytes, tests 100%.
3. `pytest tests/integration/` → verde.
4. Cobertura `pytest --cov=src --cov-fail-under=85` ≥ 85%.
