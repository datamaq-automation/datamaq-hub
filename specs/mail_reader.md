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

### 4.2 Rutas FastAPI Multi-Cuenta (`fastapi/routes/mail_routes.py`)
- `GET /api/v1/mail/carpetas?account={account}`
- `GET /api/v1/mail/inbox?account={account}&limit=20&desde=0&sin_leer=false&carpeta=INBOX`
- `GET /api/v1/mail/inbox/sin-leer?account={account}&limit=5&carpeta=INBOX`
- `GET /api/v1/mail/inbox/{uid}?account={account}&carpeta=INBOX`
- `GET /api/v1/mail/{uid}?account={account}&carpeta=INBOX`

> **Soporte Multi-Cuenta:** Si se omite `account`, el servidor utiliza la cuenta predeterminada (`default_mail_account`). Permite consultar cuentas corporativas (`datamaq`) y docentes (`abc`) en paralelo.

---

## 5. Matriz de Pruebas

| Capa | Archivo de Prueba | Cobertura |
|---|---|---|
| Dominio | `tests/unit/test_mail_domain.py` | Value Objects, Entidades, Normalización y Sanitización |
| Aplicación | `tests/unit/test_mail_use_cases.py` | Orquestación de Casos de Uso con mock de `MailReaderPort` |
| Adaptadores | `tests/unit/test_imap_mail_gateway.py` | Gateway IMAP con mock de respuestas RFC 822 y flags PEEK |
| Integración HTTP | `tests/integration/test_mail_routes.py` | Endpoints FastAPI con `TestClient` y validación de esquemas |
