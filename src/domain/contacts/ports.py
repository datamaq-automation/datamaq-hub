"""Port protocols for contacts repository and storage."""

from typing import Protocol

from src.domain.contacts.entities import Contact, ContactGroup


class ContactsRepositoryPort(Protocol):
    """Abstract port for contacts persistence operations."""

    def list_contacts(
        self,
        account: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contact], int]:
        """Lists and searches contacts for a specific account with pagination."""
        ...

    def get_contact_by_id(self, contact_id: str, account: str) -> Contact | None:
        """Retrieves a single contact by identifier."""
        ...

    def create_contact(self, contact: Contact, account: str) -> Contact:
        """Persists a new contact returning the entity with generated ID."""
        ...

    def update_contact(self, contact: Contact, account: str) -> Contact:
        """Updates an existing contact."""
        ...

    def delete_contact(self, contact_id: str, account: str) -> bool:
        """Performs soft delete of a contact."""
        ...

    def list_groups(self, account: str) -> list[ContactGroup]:
        """Lists contact groups for the specified account."""
        ...
