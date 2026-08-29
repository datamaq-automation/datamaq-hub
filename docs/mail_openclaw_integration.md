# Guía y SSOT de Integración: OpenClaw ↔ Correo Electrónico (Mail Reader) — DataMaq Hub

> **Proyecto:** DataMaq (`datamaq-hub`)  
> **Estado:** Documento Vivo (Living SSOT de Integración de Agentes y Servicios de Correo)  
> **Ámbito:** Acceso de sólo lectura para OpenClaw al buzón de correos electrónicos vía IMAP / Dovecot (cuenta corporativa) y Gmail REST API OAuth2 (cuenta docente ABC) a través de Datamaq Hub API en loopback.

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

### 3.1 Cuenta Corporativa (IMAP / Dovecot Local)

```ini
# === CONFIGURACIÓN DE CORREO IMAP (Lectura para OpenClaw) ===
MAIL_IMAP_HOST=127.0.0.1
MAIL_IMAP_PORT=993
MAIL_IMAP_USER=openclaw@datamaq.com.ar
MAIL_IMAP_PASS=TU_PASSWORD_IMAP_AQUI
MAIL_IMAP_USE_SSL=true
MAIL_IMAP_TIMEOUT_SECONDS=10
```

La cuenta corporativa (`openclaw@datamaq.com.ar`) se resuelve contra el Dovecot local mediante IMAP con autenticación básica.

### 3.2 Cuenta Docente ABC (OAuth2 / Gmail REST API)

La cuenta docente (`agustinbustos@abc.gob.ar`) usa **Google OAuth2 (Gmail REST API)**. Las credenciales (`oauth2_client_id`, `oauth2_client_secret`, `oauth2_refresh_token`) se declaran bajo la clave `MAIL_ACCOUNTS` con el alias `abc`:

```ini
# === SERVIDOR DE CORREO IMAP (Cuenta Comercial - Dovecot Local) ===
MAIL_IMAP_HOST=127.0.0.1
MAIL_IMAP_PORT=993
MAIL_IMAP_USER=openclaw@datamaq.com.ar
MAIL_IMAP_PASS=TU_PASSWORD_DOVECOT_SI_APLICA
MAIL_IMAP_USE_SSL=true
MAIL_IMAP_TIMEOUT_SECONDS=10

# === SOPORTE MULTI-CUENTA DE CORREO (Docente ABC PBA) ===
DEFAULT_MAIL_ACCOUNT=openclaw@datamaq.com.ar
MAIL_ACCOUNTS={"abc": {"host": "imap.gmail.com", "port": 993, "user": "agustinbustos@abc.gob.ar", "oauth2_client_id": "TU_CLIENT_ID.apps.googleusercontent.com", "oauth2_client_secret": "TU_CLIENT_SECRET", "oauth2_refresh_token": "1//TU_REFRESH_TOKEN_OFFLINE", "use_ssl": true, "timeout_seconds": 15}}
```

> [!NOTE]
> **Estrategia de Cuenta por Defecto (`DEFAULT_MAIL_ACCOUNT`):**
> - **Opción A (recomendada):** Mantener `DEFAULT_MAIL_ACCOUNT=openclaw@datamaq.com.ar` como buzón corporativo. OpenClaw consulta explícitamente `?account=abc` para tareas docentes y sin parámetro para la cuenta comercial.
> - **Opción B:** Configurar `DEFAULT_MAIL_ACCOUNT=abc` si se desea que toda consulta sin parámetros apunte al correo docente ABC.

> [!IMPORTANT]
> El `refresh_token` es un token **offline permanente** de Google que ya fue generado y verificado localmente mediante el flujo OAuth2 interactivo (`scripts/authenticate_gmail_oauth.py`). No es necesario repetir el consentimiento interactivo en Google Cloud: basta con replicar la entrada `MAIL_ACCOUNTS` en el `.env` del VPS.

### 3.3 Medidas de Seguridad en el VPS

El archivo `.env` de producción debe residir en `/var/www/datamaq-hub/.env` con permisos restrictivos:

```bash
sudo chown datamaq:datamaq /var/www/datamaq-hub/.env
sudo chmod 600 /var/www/datamaq-hub/.env
```

---

## 3.4 Runbook de Despliegue y Diagnóstico en VPS

Secuencia ordenada para aprovisionar, validar y activar las credenciales de un buzón en el VPS.

### Paso 1 — Editar el `.env`

```bash
sudo -u datamaq vim /var/www/datamaq-hub/.env
```

Agregar la clave `MAIL_ACCOUNTS` con el alias y las credenciales del buzón correspondiente (ver §3.2).

### Paso 2 — Diagnóstico CLI previo al reinicio

```bash
cd /var/www/datamaq-hub
source venv/bin/activate
python scripts/verify_mail_connection.py --account abc
```

**Resultado esperado:**
```
🔍 Probando conexión IMAP para la cuenta: abc
  • API:      Gmail REST API (OAuth2)
  • Usuario:  agustinbustos@abc.gob.ar (Google OAuth2 (Gmail REST API))
  • Timeout:  15s
✅ Conexión y autenticación exitosa!
  • Total de carpetas encontradas: 13
    - [INBOX] ...
```

### Paso 3 — Reinicio del servicio

```bash
sudo systemctl restart datamaq-hub
sudo systemctl status datamaq-hub --no-pager
```

El daemon debe quedar en estado `active (running)` y escuchando en `127.0.0.1:8013`.

### Paso 4 — Verificación HTTP en loopback

```bash
# 1. Listar carpetas de la cuenta ABC
curl -sS "http://127.0.0.1:8013/api/v1/mail/carpetas?account=abc" | jq .

# 2. Resumen de correos no leídos
curl -sS "http://127.0.0.1:8013/api/v1/mail/inbox/sin-leer?account=abc" | jq .

# 3. Listar últimos 5 correos
curl -sS "http://127.0.0.1:8013/api/v1/mail/inbox?account=abc&limit=5" | jq .
```

### Paso 5 — Verificación end-to-end con OpenClaw

Enviar al agente el mensaje *"revisá si hay novedades en el mail abc"* y confirmar que responde con el resumen de no leídos sin errores de credenciales (`MAIL_AUTHENTICATION_ERROR` / `ACCOUNT_NOT_FOUND`).

---



## 4. Catálogo de Endpoints de Correo

Todos los endpoints están montados bajo el prefijo `/api/v1/mail`:

### 1. `GET /api/v1/mail/carpetas`
Lista todas las carpetas IMAP disponibles en el servidor con sus estadísticas.

**Parámetros Query:**
- `account` (str, default: `DEFAULT_MAIL_ACCOUNT`): Alias de la cuenta de correo (`abc`, `datamaq`, etc.).

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
- `account` (str, default: `DEFAULT_MAIL_ACCOUNT`): Alias de la cuenta de correo (`abc`, `datamaq`, etc.).
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
- `account` (str, default: `DEFAULT_MAIL_ACCOUNT`): Alias de la cuenta de correo (`abc`, `datamaq`, etc.).
- `limit` (int, default: 5): Cantidad máxima de correos no leídos recientes a incluir en la lista breve.
- `carpeta` (str, default: "INBOX"): Nombre de la carpeta.

### 4. `GET /api/v1/mail/inbox/{uid}`
Retorna el detalle completo de un correo específico por su UID.

**Parámetros de Ruta:**
- `uid` (str): Identificador único IMAP del correo.

**Parámetros Query:**
- `account` (str, default: `DEFAULT_MAIL_ACCOUNT`): Alias de la cuenta de correo (`abc`, `datamaq`, etc.).
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

La cuenta de correo se selecciona mediante el parámetro query `?account={alias}` (`abc`, `datamaq`, etc.). Si se omite, se usa la cuenta definida en `DEFAULT_MAIL_ACCOUNT` (ver §3.2, Opción A/B).

```bash
# Consultar resumen de no leídos (cuenta por defecto / corporativa)
curl -sS http://127.0.0.1:8013/api/v1/mail/inbox/sin-leer

# Consultar resumen de no leídos de la cuenta docente ABC
curl -sS "http://127.0.0.1:8013/api/v1/mail/inbox/sin-leer?account=abc"

# Listar últimos 5 correos de la cuenta ABC
curl -sS "http://127.0.0.1:8013/api/v1/mail/inbox?account=abc&limit=5"

# Obtener detalle de un correo específico
curl -sS "http://127.0.0.1:8013/api/v1/mail/inbox/1052?account=abc"
```

En los prompts a OpenClaw se debe especificar explícitamente la cuenta para tareas que no son la corporativa:
- *"revisá si hay novedades en el mail **abc**"*  → invoca `?account=abc`.
- *"revisá el correo comercial"* (sin parámetro)  → usa la cuenta corporativa por defecto.

---

## 6. Caché TTL y Optimización de Latencia para OpenClaw

El acceso IMAP/Gmail es el cuello de botella dominante en el VPS (≈ 2.6 s por consulta).
Para que OpenClaw responda instantáneamente al revisar el correo, las lecturas se
envuelven en una capa de caché transparente: el patrón decorador
`CachedMailReaderGateway` sobre el puerto `MailReaderPort`.

### 6.1 Arquitectura (patrón Decorador)

```
Cliente (OpenClaw/curl)
   │
   ▼
CachedMailReaderGateway  ──► ApiCachePort (ApiCacheGateway)
   │                             ├─ L1: memoria del proceso (ultra rápida)
   │                             └─ L2: api_cache (SQLite WAL persistente)
   ▼
MailReaderPort base (ImapMailGateway / GmailApiGateway)  ──► IMAP/Gmail
```

- **Fichero de implementación:** `src/adapters/gateways/cached_mail_reader_gateway.py`.
- **Ensamblaje:** `get_configured_mail_controller` (en `mail_routes.py`) crea el lector
  base, lo envuelve con `CachedMailReaderGateway(reader, cache, account)` y lo pasa al
  controlador. La caché usa `resolve_database_url(settings.database_url)`: con
  `DATABASE_URL` vacío (caso típico del VPS) cae al archivo SQLite WAL
  `data/datamaq_hub.db` (decisión de fallback centralizada en `api_cache_gateway.py`).
- **Serialización:** las entidades de dominio (`EmailFolder`, `UnreadSummary`,
  `EmailSummary`) se serializan con `dataclasses.asdict` en `set` y se reconstruyen en
  el `get`; no depende del `json.dumps(default=str)` del gateway de caché.

### 6.2 Claves Canónicas & TTLs

| Método cacheado | Clave | TTL |
|---|---|---|
| `get_unread_summary` | `mail:unread_summary:{account}:{folder}` | 60 segundos |
| `get_folders` | `mail:folders:{account}` | 300 segundos |

Los TTLs se resuelven por prefijo en `CACHE_TTL` de `api_cache_gateway.py`;
`list_messages` y `get_message_by_uid` son **passthrough** (delegación directa): el
contenido volátil del inbox y el detalle por UID NO se cachean para garantizar
frescura y privacidad.

### 6.3 Rendimiento verificado en VPS (donde)

| Medición | Latencia |
|---|---|
| Primer acceso (miss → poblado de caché en SQLite WAL) | ≈ 2.5–2.8 s (IMAP) |
| Segundo acceso consecutivo (hit) | **≈ 3–11 ms** |

Reducción de latencia de **≈ 99.8 %** (de 2.587 ms a ~10.9 ms en el diagnóstico, y
~3 ms en hits `curl` consecutivos). La caché persiste entre reinicios del servicio en
`api_cache` (`data/datamaq_hub.db`), y expira por TTL sin purga manual.

> [!NOTE]
> **Cuenta en la clave de caché:** se usa el `account_config.user` de la cuenta
> resuelta (el email). Así la caché se comparte entre alias semánticos de la misma
> cuenta (`docente`, `abc.gob.ar`, `gmail` → misma `user` → misma clave), maximizando
> la tasa de hit sin romper corrección.
