# ADR: SQLAlchemy de caché vive en `adapters/gateways`, no en `infrastructure`

- **Fecha:** 2026-08-25
- **Estado:** Aceptado
- **Decisión:** Implementar la caché persistente como `ApiCacheGateway` en
  `src/adapters/gateways/api_cache_gateway.py`, encapsulando SQLAlchemy
  directamente, en lugar de un servicio de aplicación + capa `infrastructure/database`.

## Contexto

El intento previo ubicó `ApiCacheService` en `src/application/use_cases/`
importando `src.infrastructure.database`. Esto violaba la pureza de la capa de
aplicación (`tests/test_architecture_boundaries.py`) y la Regla Sagrada 1
(adapters nunca importa infrastructure).

## Decisión

SQLAlchemy (motor, sesión, modelo ORM, `init_db`) queda encapsulado dentro del
gateway, que implementa el puerto de dominio `ApiCachePort`. Es el mismo patrón
que `pdfplumber_extractor_gateway` encapsula `pdfplumber`.

## Justificación

1. **Pureza de capas:** el dominio solo expone `ApiCachePort` (abc puro); la
   aplicación no toca persistencia; los adapters no importan infrastructure.
2. **Desacoplamiento de los gateways externos:** `GoogleAdsGateway`, `GA4Gateway`
   y `ClarityGateway` dependen solo de `ApiCachePort` (inyección opcional con
   default). No quedan atados a un ORM concreto.
3. **Sustituibilidad:** cambiar de ORM solo modifica `api_cache_gateway.py`; el
   resto del sistema habla con el puerto.
4. **Consistencia:** la configuración (`database_url`, `ttl_by_prefix`) fluye por
   constructor desde la capa más externa (FastMCP / startup de FastAPI), sin que
   el gateway lea Settings directamente.

## Consecuencias

- `src/infrastructure/database/` y `src/application/use_cases/api_cache_service.py`
  se eliminan.
- El ORM queda acoplado a la capa de adapters (aceptado: los gateways ya
  encapsulan librerías especializadas).
- Los TTL siguen la regla de inmutabilidad temporal: defaults de fallback en el
  gateway, sobreescribibles vía `Settings.cache_ttls`.
