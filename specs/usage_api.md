# Especificación: Endpoint de Consulta de Usage y Balance de APIs

## 1. Objetivo y Contexto

Proveer un endpoint centralizado en la API del Hub (`GET /api/v1/analytics/usage`) que permita consultar de forma unificada el consumo y balance de las dos APIs de modelos de lenguaje utilizadas en el sistema:
1. **DeepSeek API:** Balance disponible y moneda consultando el endpoint oficial de facturación (`/user/balance`).
2. **AGY (Antigravity CLI):** Cantidad total acumulada de tokens de entrada (input), salida (output) y caché consumidos por las sesiones de Antigravity, obtenidos mediante el análisis determinístico de los archivos de registro locales (`~/.gemini/antigravity-cli/log/*.log`).

---

## 2. Modelo de Dominio y DTOs

### 2.1 DTOs de Aplicación (`src/application/dtos/analytics_dtos.py`)

```python
from pydantic import BaseModel, Field


class TokenUsageDTO(BaseModel):
    input_tokens: int = Field(description="Total de tokens de entrada consumidos")
    output_tokens: int = Field(description="Total de tokens de salida consumidos")
    cached_tokens: int = Field(description="Total de tokens de caché consumidos")


class DeepSeekUsageDTO(BaseModel):
    is_available: bool = Field(
        description="Indica si la API de DeepSeek está disponible/configurada"
    )
    balance: float = Field(description="Saldo disponible en la cuenta")
    currency: str = Field(description="Moneda del saldo (usualmente USD)")


class UsageResponseDTO(BaseModel):
    deepseek: DeepSeekUsageDTO = Field(description="Uso y balance de DeepSeek API")
    agy: TokenUsageDTO = Field(
        description="Consumo acumulado de tokens de Antigravity CLI"
    )
```

---

## 3. Puertos y Gateways

### 3.1 Puertos de Dominio (`src/domain/analytics/ports.py` o similar)
Se definirá un puerto para la obtención de métricas de APIs:
```python
from abc import ABC, abstractmethod
from src.application.dtos.analytics_dtos import UsageResponseDTO


class APIUsageRepositoryPort(ABC):
    @abstractmethod
    def obtener_usage_consolidado(self) -> UsageResponseDTO:
        pass
```

### 3.2 Gateway (`src/adapters/gateways/api_usage_gateway.py`)
Implementa `APIUsageRepositoryPort` realizando las siguientes acciones:
- **DeepSeek:** HTTP GET con urllib/requests a `https://api.deepseek.com/user/balance` usando la cabecera `Authorization: Bearer <DEEPSEEK_API_KEY>`.
- **AGY Logs:** Escaneo de los directorios de logs por defecto:
  1. `~/.gemini/antigravity-cli/log/*.log` (resuelto dinámicamente usando `os.path.expanduser("~")`).
  2. Fallbacks opcionales en caso de no existir o no tener permisos de lectura (ej. `/root/.gemini/antigravity-cli/log/*.log` y `/home/agustin/.gemini/antigravity-cli/log/*.log`).
  3. Sumarización acumulativa usando expresiones regulares para capturar el formato `Usage: <input> in / <output> out · cache <cached> cached`.

---

## 4. Matriz de Pruebas (RED Suite)

- **Unitarias:**
  - `test_parse_tokens_helper`: Valida la conversión correcta de cadenas como `"72k"`, `"1.5m"`, `"848"` a enteros (`72000`, `1500000`, `848`).
  - `test_api_usage_gateway_deepseek_missing_key`: Si `DEEPSEEK_API_KEY` no está configurada, el gateway debe retornar `is_available = False` con balance `0.0`.
- **Integración:**
  - `test_analytics_usage_endpoint`: Realiza una petición GET a `/api/v1/analytics/usage` y valida la forma de la respuesta (HTTP 200 y éxito de la estructura).
