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
| **[`mail_reader.md`](mail_reader.md)** | Subsistema de Lectura de Correo (OpenClaw) | **Aprobado / En Implementación** | Contratos de dominio, gateway IMAP read-only, DTOs y endpoints de correo. |
| **[`contacts_manager.md`](contacts_manager.md)** | Módulo de Libreta de Contactos | **En Desarrollo** | Libreta de direcciones corporativa sincronizada con Roundcube. |
| **[`calendar_manager.md`](calendar_manager.md)** | Módulo de Calendario y Eventos | **Aprobado / Implementado** | Gestión de eventos, citas y disponibilidad horaria. |
| **[`horarios_docencia.md`](horarios_docencia.md)** | Horarios de Docencia y Compatibilidad | **Aprobado / Implementado** | Auditoría estatutaria DGCyE PBA, CRUD de designaciones y proyección de clases. |
| **[`endpoints_optimization.md`](endpoints_optimization.md)** | Optimización de Endpoints y VPS (OpenClaw) | **En Implementación** | Compresión gzip, caché SQLite WAL, modos compact/resumen y límites reducidos para ahorro de tokens. |

---

## Relación con `docs/`

- **`specs/*.md`**: Define los contratos técnicos, interfaces, DTOs y algoritmos formales de implementación de software.
- **`docs/*.md`**: Documentación viva (SSOT) de gobernanza, estrategia de negocio, configuración de credenciales, manuales de campañas y decisiones arquitectónicas (ADRs).
