# Especificación Técnica: Contacts Manager (Libreta de Contactos Corporativa)

## 1. Identificación y Propósito
- **ID:** `SPEC-CONT-001`
- **Módulo:** `contacts`
- **Capa DDD:** `domain/contacts`, `application/`, `adapters/`, `infrastructure/`
- **Consumidores:** Asistente AI (OpenClaw), API REST Datamaq Hub, Webmail Roundcube.
- **Objetivo:** Proveer una API agnóstica de libreta de direcciones corporativa que permita buscar, listar, consultar, crear, modificar y eliminar contactos (incluyendo metadatos vCard), sincronizada bidireccionalmente con la base de datos de Roundcube.

---

## 2. Invariantes de Dominio
1. **Identificación de Contacto:** Todo contacto posee un identificador numérico o alfanumérico único (`ContactId`).
2. **Validación de Identidad:** Todo contacto debe poseer al menos un nombre (`name` o `firstname`/`surname`) o una dirección de correo electrónico válida (`EmailAddress`).
3. **Soft-Delete Inmutable:** La eliminación de contactos en Roundcube se realiza marcando el flag `del = 1` y actualizando la marca temporal `changed`, preservando la integridad referencial.
4. **Multiusuario Particionado:** Toda consulta y mutación está contextualizada al `user_id` de la cuenta de correo correspondiente (ej. `openclaw@datamaq.com.ar` o `agustin@datamaq.com.ar`).

---

## 3. Modelo de Dominio (`src/domain/contacts/`)

### Entidades y Value Objects
- `Contact`: Entidad `@dataclass(frozen=True)` representando un contacto con id, nombre completo, nombre de pila, apellido, email, teléfono, organización, notas, vCard raw y fecha de modificación.
- `ContactGroup`: Entidad `@dataclass(frozen=True)` representando una agrupación de contactos.
- `ContactId`: Value Object que encapsula y valida el identificador del contacto.
- `EmailAddress`: Value Object para validación de direcciones de correo electrónico.
- `PhoneNumber`: Value Object opcional para números de contacto.

### Puerto (`ports.py`)
```python
from typing import Protocol
from src.domain.contacts.entities import Contact, ContactGroup


class ContactsRepositoryPort(Protocol):
    def list_contacts(
        self,
        account: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contact], int]: ...

    def get_contact_by_id(self, contact_id: str, account: str) -> Contact | None: ...

    def create_contact(self, contact: Contact, account: str) -> Contact: ...

    def update_contact(self, contact: Contact, account: str) -> Contact: ...

    def delete_contact(self, contact_id: str, account: str) -> bool: ...
```

---

## 4. Casos de Uso (`src/application/`)
1. `ListContactsUseCase`: Búsqueda filtrada por texto libre (nombre, apellido, email) con paginación (`limit`, `offset`).
2. `GetContactDetailUseCase`: Obtención del detalle completo de un contacto por ID.
3. `CreateContactUseCase`: Validación y persistencia de un nuevo contacto.
4. `UpdateContactUseCase`: Actualización de campos de contacto preservando los no modificados.
5. `DeleteContactUseCase`: Baja lógica de contacto (`del = 1`).

---

## 5. Endpoints HTTP
- `GET /api/v1/contactos`: Listar / buscar contactos (`?q=&limit=&offset=&account=`).
- `GET /api/v1/contactos/{contact_id}`: Obtener detalle (`?account=`).
- `POST /api/v1/contactos`: Crear contacto (`CreateContactDTO`).
- `PUT /api/v1/contactos/{contact_id}`: Actualizar contacto (`UpdateContactDTO`).
- `DELETE /api/v1/contactos/{contact_id}`: Eliminar contacto (`?account=`).
