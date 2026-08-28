# Oportunidades de Mejora y Hoja de Ruta — `datamaq-hub`

> **Proyecto:** DataMaq Hub (`datamaq-hub`)  
> **Estado:** Documento Vivo de Estrategia Técnica, Arquitectura & Automatización  
> **Ámbito:** Core Backend FastAPI, Clean Architecture + DDD, Integraciones OpenClaw, Roundcube MySQL, FastMCP y Telemetría.

---

## 🏛️ 1. Automatización e Ingesta de Leads (`www-datamaq` ➔ `datamaq-hub`)

### A. Webhook de Ingesta y Auto-Registro de Contactos
- **Problema / Oportunidad:** Actualmente los leads enviados en el formulario web se almacenan localmente en la base de datos de `www-datamaq`.
- **Mejora:** Crear un endpoint receptor en `datamaq-hub` (`POST /api/v1/leads/ingest`):
  1. **Alta Inmediata en Libreta**: Inserta el contacto con vCard completa en la tabla `roundcube.contacts` del VPS.
  2. **Agenda de Seguimiento**: Crea automáticamente un evento recordatorio o tarea comercial en el calendario de Roundcube (`roundcube.events`) asignado a OpenClaw.
  3. **Alertas Push**: Envía un mensaje instantáneo al bot de Telegram del equipo técnico con los datos del prospecto.

---

## 📱 2. Integración y Exportación para WhatsApp Business

### A. Descarga y Exportación de Libreta vCard 3.0 (`.vcf`)
- **Mejora:** Implementar el endpoint `GET /api/v1/contactos/export/vcard`:
  - Genera un archivo `.vcf` consolidado y estandarizado con todos los contactos corporativos.
  - Permite importar con un solo toque la libreta completa en la aplicación de WhatsApp Business del teléfono móvil corporativo.

### B. Sincronización en Tiempo Real vía CardDAV
- Documentar y habilitar el conector CardDAV nativo de Roundcube para sincronizar automáticamente el teléfono Android (DAVx⁵) o iPhone con la base de datos central de contactos de Datamaq Hub.

### C. Webhook de WhatsApp Cloud API (Captura Pasiva de Prospectos)
- Endpoint `POST /api/v1/whatsapp/webhook` para registrar automáticamente a cualquier cliente nuevo que inicie una conversación con el número oficial de WhatsApp Business de DataMaq.

---

## 🔔 3. Alertas Proactivas y Notificaciones (Telegram Bot)

### A. Monitor Inteligente de Operaciones
- Implementar un servicio de alertas proactivas en `datamaq-hub` que notifique a Telegram:
  - **Leads Entrantes**: Alerta con nombre, teléfono, empresa y consulta.
  - **Correos Prioritarios**: Alerta ante correos no leídos de clientes clave en la bandeja de entrada IMAP.
  - **Pacing de Google Ads**: Alerta preventiva si el gasto diario de la cuenta de Google Ads se acerca al límite de $1.500 ARS/día.
  - **Agenda del Día**: Briefing matutino automático con las clases docentes y reuniones programadas.

---

## 🤖 4. Consolidación de FastMCP para Asistentes AI

### A. Servidor MCP Unificado de DataMaq
- Integrar en un único servidor FastMCP (`src/infrastructure/fastmcp/server.py`):
  - **Herramientas de Correo**: Listar carpetas, buscar mensajes no leídos, leer cuerpo de emails.
  - **Herramientas de Contactos**: Buscar, crear y actualizar clientes en Roundcube.
  - **Herramientas de Calendario**: Consultar disponibilidad, agendar reuniones y sincronizar clases docentes.
  - **Herramientas de Marketing**: Auditar gasto de Google Ads, conversiones de GA4 y enlaces a grabaciones de Clarity.
- Permite a **OpenClaw**, Claude Desktop o Cursor operar directamente sobre toda la infraestructura corporativa de DataMaq con control estricto de permisos.

---

## 🔒 5. Resiliencia, Backups y Seguridad de Datos

### A. Backups Automáticos de Bases de Datos
- Automatizar dump periódico cifrado de las bases MySQL de producción (`roundcube`, `datamaq_hub`, `datamaq_leads`) hacia almacenamiento secundario.

### B. Rotación de Logs y Métricas de Rendimiento
- Configurar rotación de logs de systemd/uvicorn y métricas de latencia por endpoint con Prometheus/Grafana o middleware liviano de telemetría.
