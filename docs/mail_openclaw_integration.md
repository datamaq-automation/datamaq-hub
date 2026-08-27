# Guía y SSOT de Integración: OpenClaw ↔ Correo Electrónico (Mail Reader) — DataMaq Hub

> **Proyecto:** DataMaq (`datamaq-hub`)  
> **Estado:** Documento Vivo (Living SSOT de Integración de Agentes y Servicios de Correo)  
> **Ámbito:** Acceso de sólo lectura para OpenClaw al buzón de correos electrónicos vía IMAP / Dovecot a través de Datamaq Hub API en loopback.

---

## 1. Contexto y Objetivos de la Integración

El agente de inteligencia artificial **OpenClaw** opera en un entorno enjaulado y restringido en el VPS DonWeb (`User=openclaw`, `127.0.0.1:18789`). Por motivos de seguridad y defensa en profundidad:
- OpenClaw **no tiene acceso directo** al sistema de archivos de correo (`/home/datamaq/mail`), sockets UNIX ni puertos de bases de datos.
- OpenClaw interactúa con los subsistemas internos exclusivamente a través de la API REST de **Datamaq Hub** (`http://127.0.0.1:8013`), cuya allowlist está configurada en `/home/openclaw/.openclaw/exec-approvals.json` con el patrón `.*127\.0\.0\.1:8013.*`.

El módulo `mail` de Datamaq Hub expone endpoints desacoplados bajo Clean Architecture que permiten a OpenClaw:
1. Inspeccionar las carpetas IMAP disponibles (`INBOX`, `Sent`, `Drafts`, `Trash`, etc.) y la cantidad de mensajes totales y no leídos.
2. Listar correos de la bandeja de entrada (o carpetas específicas) con paginación (`limit`, `desde`) y filtro por no leídos (`sin_leer`).
3. Obtener resúmenes rápidos de correos no leídos para alertas o resúmenes periódicos.
4. Consultar el contenido completo de un correo por su `UID` (asunto, remitente, destinatarios, fecha, cuerpo en texto plano y HTML, y metadatos de adjuntos).

---

## 2. Topología de Red y Seguridad

```
┌────────────────────────────────────────────────────────────────┐
│                      VPS DonWeb (Linux)                        │
│                                                                │
│  ┌──────────────────────────────┐                              │
│  │   OpenClaw Gateway (Node)    │ (User: openclaw, UID 983)    │
│  │   127.0.0.1:18789            │ Enjaulado / ProtectHome      │
│  └──────────────┬───────────────┘                              │
│                 │ HTTP GET (Allowlist loopback)                │
│                 ▼                                              │
│  ┌──────────────────────────────┐                              │
│  │   Datamaq Hub API (FastAPI)  │ (User: datamaq)              │
│  │   127.0.0.1:8013             │ Clean Architecture + DDD     │
│  └──────────────┬───────────────┘                              │
│                 │ IMAP4_SSL (127.0.0.1:993 / SELECT readonly)  │
│                 ▼                                              │
│  ┌──────────────────────────────┐                              │
│  │   Dovecot IMAP Server        │                              │
│  │   Buzón: /home/datamaq/mail  │                              │
│  └──────────────────────────────┘                              │
└────────────────────────────────────────────────────────────────┘
```

### Reglas de Seguridad No Negociables
1. **Garantía Estricta de Sólo Lectura (Read-Only Guarantee):**
   - El gateway `ImapMailGateway` abre el buzón exclusivamente mediante `EXAMINE` o `SELECT(mailbox, readonly=True)`.
   - La recuperación de contenido utiliza `BODY.PEEK[HEADER]` y `BODY.PEEK[]`.
   - **Efecto:** La lectura de correos por parte de OpenClaw nunca altera los flags de estado en el servidor (un mensaje no leído permanece como `\Unseen` para los usuarios humanos de Roundcube).
2. **Aislamiento de Red:**
   - La API escucha exclusivamente en `127.0.0.1:8013` (loopback). No está expuesta a través del proxy inverso público ni por DNS exterior.
3. **Manejo de Credenciales:**
   - Las credenciales IMAP se definen en el archivo `.env` de producción (`/var/www/datamaq-hub/.env`) con permisos `600` para el usuario `datamaq`.

---

## 3. Configuración del Entorno (`.env`)

```ini
# === CONFIGURACIÓN DE CORREO IMAP (Lectura para OpenClaw) ===
MAIL_IMAP_HOST=127.0.0.1
MAIL_IMAP_PORT=993
MAIL_IMAP_USER=openclaw@datamaq.com.ar
MAIL_IMAP_PASS=TU_PASSWORD_IMAP_AQUI
MAIL_IMAP_USE_SSL=true
MAIL_IMAP_TIMEOUT_SECONDS=10
```

---

## 4. Catálogo de Endpoints de Correo

Todos los endpoints están montados bajo el prefijo `/api/v1/mail`:

### 1. `GET /api/v1/mail/carpetas`
Lista todas las carpetas IMAP disponibles en el servidor con sus estadísticas.

**Ejemplo de respuesta (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "nombre": "INBOX",
      "total_mensajes": 42,
      "no_leidos": 3
    },
    {
      "nombre": "Sent",
      "total_mensajes": 150,
      "no_leidos": 0
    }
  ]
}
```

### 2. `GET /api/v1/mail/inbox`
Lista correos de la bandeja de entrada o de una carpeta seleccionada.

**Parámetros Query:**
- `limit` (int, default: 20, max: 100): Cantidad máxima de correos a retornar.
- `desde` (int, default: 0): Desplazamiento / offset para paginación.
- `sin_leer` (bool, default: false): Si es `true`, filtra solo los correos no leídos.
- `carpeta` (str, default: "INBOX"): Nombre de la carpeta a consultar.

**Ejemplo de respuesta (200 OK):**
```json
{
  "success": true,
  "data": {
    "carpeta": "INBOX",
    "total": 42,
    "no_leidos": 3,
    "offset": 0,
    "limit": 20,
    "correos": [
      {
        "uid": "1052",
        "remitente": "cliente@empresa.com",
        "destinatarios": ["contacto@datamaq.com.ar"],
        "asunto": "Consulta presupuesto telemetría",
        "fecha": "2026-08-27T08:30:00-03:00",
        "leido": false,
        "tiene_adjuntos": true,
        "carpeta": "INBOX"
      }
    ]
  }
}
```

### 3. `GET /api/v1/mail/inbox/sin-leer`
Retorna rápidamente el conteo de correos no leídos y los últimos $N$ mensajes sin leer.

**Parámetros Query:**
- `limit` (int, default: 5): Cantidad máxima de correos no leídos recientes a incluir en la lista breve.
- `carpeta` (str, default: "INBOX"): Nombre de la carpeta.

### 4. `GET /api/v1/mail/inbox/{uid}`
Retorna el detalle completo de un correo específico por su UID.

**Parámetros de Ruta:**
- `uid` (str): Identificador único IMAP del correo.

**Parámetros Query:**
- `carpeta` (str, default: "INBOX"): Carpeta donde se aloja el mensaje.

**Ejemplo de respuesta (200 OK):**
```json
{
  "success": true,
  "data": {
    "uid": "1052",
    "remitente": "cliente@empresa.com",
    "destinatarios": ["contacto@datamaq.com.ar"],
    "cc": [],
    "asunto": "Consulta presupuesto telemetría",
    "fecha": "2026-08-27T08:30:00-03:00",
    "leido": false,
    "cuerpo_texto": "Hola equipo DataMaq,\n\nQuisiéramos solicitar cotización...",
    "cuerpo_html": "<p>Hola equipo DataMaq,<br><br>Quisiéramos solicitar cotización...</p>",
    "adjuntos": [
      {
        "nombre": "especificacion_tecnica.pdf",
        "content_type": "application/pdf",
        "tamano_bytes": 1048576
      }
    ],
    "carpeta": "INBOX"
  }
}
```

---

## 5. Ejemplos de Invocación desde OpenClaw

OpenClaw puede consultar los endpoints mediante `curl` o mediante llamadas HTTP en sus herramientas internas:

```bash
# Consultar resumen de no leídos
curl -sS http://127.0.0.1:8013/api/v1/mail/inbox/sin-leer

# Listar últimos 5 correos recibidos
curl -sS "http://127.0.0.1:8013/api/v1/mail/inbox?limit=5"

# Obtener detalle de un correo específico
curl -sS http://127.0.0.1:8013/api/v1/mail/inbox/1052
```
