# Especificación Técnica: Subsistema de Lectura de Correo Electrónico (Mail Reader)

> **Ámbito:** Motor de consulta y lectura estructurada de correos electrónicos vía IMAP para OpenClaw e integraciones internas.  
> **Patrón:** Clean Architecture + Domain-Driven Design (DDD) Temático Plano + Spec-Driven Development (SDD).  
> **Estado:** Aprobado / En Implementación.

---

## 1. Modelo de Dominio (`src/domain/mail/`)

El bounded context `mail` es 100% puro (stdlib + dataclasses inmutables).

### 1.1 Value Objects (`value_objects.py`)
- `EmailAddress(value: str)`: Validación de formato estándar `user@domain.tld`.
- `EmailUID(value: str)`: Identificador único inmutable IMAP.
- `FolderName(value: str)`: Normalización y saneamiento de nombres de buzón IMAP (ej. `INBOX`, `Sent`).

### 1.2 Entidades (`entities.py`)
- `EmailFolder`:
  - `nombre: str`
  - `total_mensajes: int`
  - `no_leidos: int`
- `EmailAttachmentMetadata`:
  - `nombre: str`
  - `content_type: str`
  - `tamano_bytes: int`
- `EmailSummary`:
  - `uid: str`
  - `remitente: str`
  - `destinatarios: list[str]`
  - `asunto: str`
  - `fecha: str` (formato ISO 8601)
  - `leido: bool`
  - `tiene_adjuntos: bool`
  - `carpeta: str`
- `EmailDetail`:
  - `uid: str`
  - `remitente: str`
  - `destinatarios: list[str]`
  - `cc: list[str]`
  - `asunto: str`
  - `fecha: str` (formato ISO 8601)
  - `leido: bool`
  - `cuerpo_texto: str`
  - `cuerpo_html: str`
  - `adjuntos: list[EmailAttachmentMetadata]`
  - `carpeta: str`
- `UnreadSummary`:
  - `carpeta: str`
  - `total_no_leidos: int`
  - `ultimos_no_leidos: list[EmailSummary]`

### 1.3 Puertos (`ports.py`)
```python
from typing import Protocol
from src.domain.mail.entities import (
    EmailDetail,
    EmailFolder,
    EmailSummary,
    UnreadSummary,
)


class MailReaderPort(Protocol):
    def get_folders(self) -> list[EmailFolder]:
        """Obtiene la lista de carpetas disponibles con sus estadísticas."""
        ...

    def list_messages(
        self,
        folder: str = "INBOX",
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[list[EmailSummary], int, int]:
        """Lista mensajes de una carpeta retornando (mensajes, total_en_carpeta, total_no_leidos)."""
        ...

    def get_message_by_uid(self, uid: str, folder: str = "INBOX") -> EmailDetail | None:
        """Obtiene el detalle completo de un correo por su UID sin marcarlo como leído."""
        ...

    def get_unread_summary(
        self, folder: str = "INBOX", limit: int = 5
    ) -> UnreadSummary:
        """Obtiene un resumen rápido del estado de no leídos."""
        ...
```

### 1.4 Excepciones de Dominio (`exceptions.py`)
- `MailDomainException`: Clase base de excepciones de correo.
- `EmailNotFoundError`: Correo con el UID especificado no encontrado en la carpeta.
- `MailboxNotFoundError`: Carpeta IMAP solicitada inexistente.
- `MailConnectionError`: Error de conexión o timeout con el servidor IMAP.
- `MailAuthenticationError`: Falla de credenciales o autenticación IMAP.
- `AccountNotFoundError`:
  - Constructor: `AccountNotFoundError(account: str, available_accounts: list[str] | None = None)`.
  - Atributos: `account: str`, `available_accounts: list[str]`, `details: dict[str, Any] | None`.
  - `details` expone la clave `cuentas_disponibles: list[str]` para que agentes LLM (OpenClaw) puedan auto-corregirse.
  - Mensaje: `"La cuenta de correo '{account}' no está configurada en el sistema. Cuentas disponibles: [..]"`

---

## 2. Capa de Aplicación (`src/application/`)

### 2.1 DTOs (`dtos/mail_dto.py`)
- `EmailFolderDTO`: Representación de carpeta IMAP.
- `EmailAttachmentDTO`: Metadatos de archivo adjunto.
- `EmailSummaryDTO`: Vista resumida de correo para listados.
- `EmailDetailDTO`: Detalle completo con cuerpos texto/html y adjuntos.
- `UnreadSummaryDTO`: Resumen de no leídos.
- `MailInboxResponseDTO`: Contenedor paginado con `total`, `no_leidos`, `offset`, `limit` y `correos: list[EmailSummaryDTO]`.

### 2.2 Casos de Uso (`use_cases/`)
1. `ListMailFoldersUseCase`: Orquesta `MailReaderPort.get_folders()`.
2. `ListInboxMessagesUseCase`: Orquesta `MailReaderPort.list_messages()`.
3. `GetMailDetailUseCase`: Orquesta `MailReaderPort.get_message_by_uid()`.
4. `GetUnreadSummaryUseCase`: Orquesta `MailReaderPort.get_unread_summary()`.

---

## 3. Capa de Adaptadores (`src/adapters/`)

### 3.1 Gateway IMAP (`gateways/imap_mail_gateway.py`)
- Implementa `MailReaderPort`.
- Conexión vía `imaplib.IMAP4_SSL` (o `IMAP4` con TLS).
- Inspección estricta de sólo lectura: `EXAMINE` o `SELECT(readonly=True)`.
- Recuperación de datos con `BODY.PEEK[HEADER]` y `BODY.PEEK[]` para no alterar flags `\Seen`.
- Decodificación y parsing con `email.message` y `email.header.decode_header`.

### 3.2 Controlador (`controllers/mail_controller.py`)
- Agnóstico de transporte web.
- Expone métodos:
  - `get_folders() -> list[EmailFolderDTO]`
  - `get_inbox_messages(folder, limit, offset, unread_only) -> MailInboxResponseDTO`
  - `get_unread_summary(folder, limit) -> UnreadSummaryDTO`
  - `get_message_detail(uid, folder) -> EmailDetailDTO`

---

## 4. Capa de Infraestructura (`src/infrastructure/`)

### 4.1 Configuración (`pydantic/config.py`)
- `mail_imap_host: str = "127.0.0.1"`
- `mail_imap_port: int = 993`
- `mail_imap_user: str = ""`
- `mail_imap_pass: str = ""`
- `mail_imap_use_ssl: bool = True`
- `mail_imap_timeout_seconds: int = 10`
- `default_mail_account: str = "openclaw@datamaq.com.ar"`
- `mail_accounts: dict[str, MailAccountConfig]`

#### `get_mail_account_config(account_name: str | None = None) -> MailAccountConfig`
Resolución de la cuenta solicitada con normalización de alias y fallback inteligente:

1. **Normalización y Mapeo de Alias:** El target se normaliza a minúsculas. Alias semánticos comunes se resuelven a la cuenta `"abc"`: `docente`, `abc.gob.ar`, `gmail`, `google`. Búsqueda insensible a mayúsculas por clave de diccionario y por `config.user`.
2. **Inyección OAuth2:** Si la cuenta tiene `oauth2_refresh_token` pero carece de `oauth2_client_id` o `oauth2_client_secret`, hereda los valores globales `google_ads_client_id` y `google_ads_client_secret`.
3. **Fallback Inteligente:** Si `account_name` es `None` (o apunta a la cuenta base `openclaw@datamaq.com.ar` / `datamaq` / `default`), y las credenciales IMAP clásicas (`mail_imap_user`, `mail_imap_pass`) están vacías pero existen cuentas en `mail_accounts`, se selecciona automáticamente la **primera cuenta configurada** (ej. `"abc"`), en lugar de devolver una config IMAP sin credenciales.
4. **Excepción Enriquecida:** Si la cuenta solicitada no existe, lanza `AccountNotFoundError` con `available_accounts` = lista de claves en `mail_accounts`, expuesto en `details["cuentas_disponibles"]`.

### 4.2 Rutas FastAPI Multi-Cuenta (`fastapi/routes/mail_routes.py`)
- `GET /api/v1/mail/carpetas?account={account}`
- `GET /api/v1/mail/inbox?account={account}&limit=20&desde=0&sin_leer=false&carpeta=INBOX`
- `GET /api/v1/mail/inbox/sin-leer?account={account}&limit=5&carpeta=INBOX`
- `GET /api/v1/mail/inbox/{uid}?account={account}&carpeta=INBOX`
- `GET /api/v1/mail/{uid}?account={account}&carpeta=INBOX`

> **Soporte Multi-Cuenta:** Si se omite `account`, el servidor utiliza la cuenta predeterminada (`default_mail_account`). Permite consultar cuentas corporativas (`datamaq`) y docentes (`abc`) en paralelo.

### 4.3 Caché de Lecturas IMAP (`gateways/cached_mail_reader_gateway.py`)

El acceso IMAP es el cuello de botella del VPS (≈ 2.6 s por consulta). Para aliviar la
latencia sin comprometer corrección, el lector base (`ImapMailGateway`) se envuelve con
`CachedMailReaderGateway(reader, cache: ApiCachePort, account)`, inyectado en las rutas.

- **`get_unread_summary`**: clave `mail:unread_summary:{account}:{folder}`, TTL 60 s.
- **`get_folders`**: clave `mail:folders:{account}`, TTL 300 s.
- **Passthrough** (delegación directa, sin caché): `list_messages` y `get_message_by_uid`.
- Serializa entidades de dominio con `dataclasses.asdict`/reconstrucción en `get`.

---

## 5. Matriz de Pruebas

| Capa | Archivo de Prueba | Cobertura |
|---|---|---|
| Dominio | `tests/unit/test_mail_domain.py` | Value Objects, Entidades, Normalización y Sanitización |
| Aplicación | `tests/unit/test_mail_use_cases.py` | Orquestación de Casos de Uso con mock de `MailReaderPort` |
| Adaptadores | `tests/unit/test_imap_mail_gateway.py` | Gateway IMAP con mock de respuestas RFC 822 y flags PEEK |
| Config | `tests/unit/test_mail_config_resolution.py` | Resolución directa (`abc`), alias (`docente`, `abc.gob.ar`, `agustinbustos@abc.gob.ar`), fallback inteligente (default sin credenciales → primera cuenta) y `AccountNotFoundError` con `details["cuentas_disponibles"]` |
| Integración HTTP | `tests/integration/test_mail_routes.py` | Endpoints FastAPI con `TestClient` y validación de esquemas |
| Adaptadores (caché) | `tests/unit/test_cached_mail_reader_gateway.py` | Wrapper con `FakeReader` + `FakeCache`: hit/miss, serialización round-trip, passthrough, TTL por prefijo |

### Contratos de tests del wrapper cacheado (RED Suite)

| # | Escenario Gherkin | Resultado esperado |
|---|---|---|
| C1 | **Dado** caché con `mail:unread_summary:abc:INBOX` vigente, **Cuando** `get_unread_summary`, **Entonces** se sirve desde caché sin invocar al reader | hit |
| C2 | **Dado** caché vacía, **Cuando** `get_unread_summary`, **Entonces** delega al reader y luego hace `set` | miss + populate |
| C3 | **Dado** reader lanza excepción, **Cuando** `get_unread_summary`, **Entonces** propaga la excepción y NO hace `set` | no-populate on error |
| C4 | **Dado** caché con `mail:folders:abc` vigente, **Cuando** `get_folders`, **Entonces** se sirve desde caché sin invocar al reader | hit |
| C5 | **Dado** `list_messages` y `get_message_by_uid`, **Cuando** se invocan, **Entonces** delegan directo al reader sin tocar la caché | passthrough |
| C6 | **Dado** un `FakeCache` con contadores, **Entonces** los parámetros de la clave usan el prefijo registrado en `_ttl_by_prefix` | TTL resuelto por prefijo |
