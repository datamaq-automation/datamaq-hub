# AGENTS.md - Directivas y Arquitectura de Software para Agentes de IA

Este repositorio implementa una estricta **Clean Architecture** (Robert C. Martin / Ports & Adapters) combinada con **Domain-Driven Design (DDD)** temático y tipado estricto en Python 3.10+.

---

## 1. Reglas de Dependencia y Capas

1. **`src/domain/{modulo_contexto}/` (Capa de Dominio):**
   * **Archivos obligatorios:** `__init__.py`, `entities.py`, `exceptions.py`, `ports.py`, `services.py`, `value_objects.py`.
   * **Restricción:** El dominio es **100% puro**. Prohibido importar frameworks o librerías externas. Únicamente la librería estándar de Python y dataclasses nativas inmutables (`@dataclass(frozen=True)`).
2. **`src/application/` (Capa de Aplicación):**
   * **Subcarpetas:** `dtos/`, `mappers/`, `use_cases/`.
   * **Nombrado plano:** `{contexto}_dtos.py`, `{contexto}_mappers.py`, `{contexto}_use_cases.py`.
   * **Uso de Pydantic:** Se permite Pydantic v2 **ÚNICAMENTE** dentro de `src/application/dtos/` para validación y serialización.
   * **Restricción:** Solo puede importar de `src/domain/`.
3. **`src/adapters/` (Capa de Adaptadores de Interfaz):**
   * **Subcarpetas:** `controllers/`, `gateways/`, `presenters/`.
   * **Regla Sagrada:** Los adaptadores **NUNCA** deben importar ni depender directamente de `src/infrastructure/`. Implementan los puertos (`ports.py`) de dominio y consumen casos de uso de aplicación.
4. **`src/infrastructure/` (Capa de Infraestructura):**
   * **Settings:** `src/infrastructure/settings/` con `__init__.py`, `logger.py` y `config.py` (usando `pydantic-settings`).
   * **Adaptadores de Infraestructura:** `fastapi/`, `opencv/`, `numpy/`, etc. Se inyectan en runtime hacia los adaptadores vía Inyección de Dependencias.

---

## 2. Inmutabilidad de Paquetes
* **TODOS los archivos `__init__.py` deben permanecer 100% VACÍOS (0 bytes).**
* Prohibido colocar imports implícitos, variables globales o `__all__` en los `__init__.py`. Las importaciones deben hacerse siempre de forma explícita directamente desde los módulos específicos.

---

## 3. Tipado Estricto (Pyright / Pylance Strict)
* Todas las funciones, métodos y atributos deben tener anotaciones de tipo explícitas (`-> None`, `-> int`, etc.).
* Utilizar `typing` moderno (`Annotated`, `TypeAlias`, `Sequence`, `Mapping`, `Optional`).

---

## 4. Scripts y Comandos de Calidad
* **Ejecución local:** `./run.sh`
* **Verificación pre-push:** `./scripts/pre-push.sh`
* **Integración continua:** `./scripts/ci.sh`
* **Test de inits vacíos:** `pytest tests/test_empty_inits.py`
