# Especificaciones Técnicas (Specs) — DataMaq Hub

> **Ámbito:** Especificaciones formales de subsistemas y componentes técnicos de `datamaq-hub`.  
> **Patrón:** Spec-Driven Development (SDD) + Clean Architecture.  

---

## Índice de Especificaciones Técnicas

| Especificación | Componente / Subsistema | Estado | Descripción |
|---|---|---|---|
| **[`receipt_parser.md`](receipt_parser.md)** | Motor de Recibos y Liquidación | **Aprobado / Implementado** | Contratos de dominio, parsers DGCyE/Genérico, DTOs y casos de uso. |
| **[`api_cache.md`](api_cache.md)** | Capa de Caché Persistente e In-Memory | **Aprobado / Implementado** | Gateway SQLAlchemy + fallback en memoria con TTL por endpoint para MCPs. |
| **[`analytics_mcp.md`](analytics_mcp.md)** | Servidores FastMCP & Watchdog | **Aprobado / Implementado** | Integración de Google Ads API (Basic Access), GA4, Microsoft Clarity y Alertas. |

---

## Relación con `docs/`

- **`specs/*.md`**: Define los contratos técnicos, interfaces, DTOs y algoritmos formales de implementación de software.
- **`docs/*.md`**: Documentación viva (SSOT) de gobernanza, estrategia de negocio, configuración de credenciales, manuales de campañas y decisiones arquitectónicas (ADRs).
