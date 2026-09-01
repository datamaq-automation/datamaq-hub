# Documentación Central (SSOT) — DataMaq Hub

> **Ecosistema DataMaq:** *"Ingeniería de datos: de la planta a la oficina"*  
> **Ámbito:** Single Source of Truth (SSOT) de arquitectura, analítica y gobernanza técnica de `datamaq-hub`.  

---

## 🧭 Mapa de Navegación de `docs/`

```
docs/
├── README.md                                  # Índice maestro y mapa de navegación
│
├── 🏛️ Arquitectura & Core Engine
│   ├── recibo_parser_plan.md                  # Diseño Clean Architecture + DDD del Motor de Recibos
│   └── adr/
│       └── 2026-08-25_api_cache_gateway_sqlalchemy.md # ADR: Capa de caché con SQLAlchemy y fallback in-memory
│
├── 🤖 Agentes IA & Integraciones
│   └── mail_openclaw_integration.md           # SSOT: Integración OpenClaw y endpoints de sólo lectura de correo
│
├── 📊 Analítica, FastMCP & Telemetría
│   └── analytics_and_ads.md                   # SSOT unificado: Google Ads (Basic Access Aprobado), GA4, Clarity, Watchdog y Atribución
│
└── 🔐 Operaciones & Despliegue
    ├── credenciales_entornos.md               # Runbook: sincronización de .env local ↔ VPS, rotación de tokens OAuth
    └── vps_replica_runbook.md                 # Runbook: réplica de datos VPS (SSOT) ➔ local
```

---

## 📚 Índice Detallado de Documentos

| Documento | Ámbito / Propósito | Estado |
|---|---|---|
| **[`recibo_parser_plan.md`](recibo_parser_plan.md)** | Plan de implementación Clean Architecture, capas del dominio `recibos` y `liquidacion`, DTOs y adaptadores. | **Vigente** |
| **[`adr/2026-08-25_api_cache_gateway_sqlalchemy.md`](adr/2026-08-25_api_cache_gateway_sqlalchemy.md)** | Registro de decisión arquitectónica para la persistencia desacoplada de respuestas de APIs externas. | **Aprobado** |
| **[`mail_openclaw_integration.md`](mail_openclaw_integration.md)** | Integración segura de sólo lectura sobre buzones IMAP para el agente OpenClaw. | **SSOT Activo** |
| **[`contacts_calendar_openclaw.md`](contacts_calendar_openclaw.md)** | Libreta de contactos y eventos para OpenClaw. | **SSOT Activo** |
| **[`analytics_and_ads.md`](analytics_and_ads.md)** | Guía integral de cuentas Google, Google Ads (**Basic Access Aprobado**), GA4, Clarity, Watchdog y gobernanza de atribución B2B. | **SSOT Activo** |
| **[`oportunidades_de_mejora.md`](oportunidades_de_mejora.md)** | Hoja de ruta estratégica y oportunidades de alto impacto en automatización, leads y FastMCP. | **Vigente** |
| **[`credenciales_entornos.md`](credenciales_entornos.md)** | Runbook operativo: qué variables sincronizar entre local y VPS (y cuál **no**), auditoría de drift sin exponer secretos, y rotación del `GOOGLE_ADS_REFRESH_TOKEN` y la credencial GA4. | **SSOT Activo** |
| **[`vps_replica_runbook.md`](vps_replica_runbook.md)** | Runbook de sincronización unidireccional de datos persistentes desde el VPS (SSOT) hacia la réplica local. | **SSOT Activo** |

---

> ℹ️ *Nota de Ecosistema:* La documentación doctrinal de pricing, planes comerciales y estrategia de inversión de capital reside en [`www-datamaq/docs/`](../../www-datamaq/docs/).
