"""SQLAlchemy Gateway implementing ContactsRepositoryPort for Roundcube/MySQL and SQLite."""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    create_engine,
    or_,
    select,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.contacts.entities import Contact, ContactGroup
from src.domain.contacts.exceptions import ContactsDomainException
from src.domain.contacts.ports import ContactsRepositoryPort
from src.domain.contacts.services import VCardFormatterService


class ContactsBase(DeclarativeBase):
    """Base declarativa para tablas de contactos."""


class RoundcubeUserModel(ContactsBase):
    """Modelo de usuarios de Roundcube para resolver user_id por username/email."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, default=""
    )
    mail_host: Mapped[str] = mapped_column(
        String(128), nullable=False, default="localhost"
    )


class RoundcubeContactModel(ContactsBase):
    """Modelo relacional de contactos de Roundcube."""

    __tablename__ = "contacts"

    contact_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False, index=True
    )
    changed: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    del_: Mapped[int] = mapped_column("del", SmallInteger, nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    email: Mapped[str] = mapped_column(Text, nullable=False, default="")
    firstname: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    surname: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    vcard: Mapped[str | None] = mapped_column(Text, nullable=True)
    words: Mapped[str | None] = mapped_column(Text, nullable=True)


class SQLContactsGateway(ContactsRepositoryPort):
    """Gateway for contacts storage supporting MySQL and SQLite."""

    def __init__(
        self, database_url: str | None = None, logger: LoggerPort | None = None
    ) -> None:
        self._logger = logger or NullLogger()
        self.database_url = database_url or os.environ.get(
            "ROUNDCUBE_DB_URL", "sqlite:///data/roundcube.db"
        )
        self._engine: Engine = create_engine(self.database_url, pool_pre_ping=True)
        ContactsBase.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def _get_session(self) -> Session:
        return self._session_factory()

    def _get_or_create_user_id(self, session: Session, account: str) -> int:
        """Resolves user_id by email/username creating an entry if not exists."""
        clean_account = account.strip().lower()
        stmt = select(RoundcubeUserModel).where(
            RoundcubeUserModel.username == clean_account
        )
        user = session.execute(stmt).scalar_one_or_none()
        if user:
            return user.user_id

        new_user = RoundcubeUserModel(username=clean_account, mail_host="localhost")
        session.add(new_user)
        session.flush()
        return new_user.user_id

    def _to_domain(self, model: RoundcubeContactModel, account: str) -> Contact:
        """Transforms ORM model into immutable domain Contact entity."""
        vcard_text = model.vcard or ""
        vcard_data = VCardFormatterService.parse_vcard_fields(vcard_text)

        phone = vcard_data.get("phone", "")
        org = vcard_data.get("organization", "")
        note = vcard_data.get("note", "")

        changed_iso = (
            model.changed.isoformat()
            if model.changed
            else datetime.now(timezone.utc).isoformat()
        )

        return Contact(
            id_contacto=str(model.contact_id),
            nombre=model.name,
            nombre_pila=model.firstname,
            apellido=model.surname,
            email=model.email,
            telefono=phone,
            organizacion=org,
            notas=note,
            vcard=vcard_text,
            modificado=changed_iso,
            eliminado=bool(model.del_),
            cuenta=account,
            grupos=[],
        )

    def list_contacts(
        self,
        account: str,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contact], int]:
        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                stmt = select(RoundcubeContactModel).where(
                    RoundcubeContactModel.user_id == user_id,
                    RoundcubeContactModel.del_ == 0,
                )

                if query and query.strip():
                    pattern = f"%{query.strip()}%"
                    stmt = stmt.where(
                        or_(
                            RoundcubeContactModel.name.ilike(pattern),
                            RoundcubeContactModel.email.ilike(pattern),
                            RoundcubeContactModel.firstname.ilike(pattern),
                            RoundcubeContactModel.surname.ilike(pattern),
                            RoundcubeContactModel.words.ilike(pattern),
                        )
                    )

                # Total count
                total_stmt = select(RoundcubeContactModel.contact_id).where(
                    RoundcubeContactModel.user_id == user_id,
                    RoundcubeContactModel.del_ == 0,
                )
                if query and query.strip():
                    pattern = f"%{query.strip()}%"
                    total_stmt = total_stmt.where(
                        or_(
                            RoundcubeContactModel.name.ilike(pattern),
                            RoundcubeContactModel.email.ilike(pattern),
                            RoundcubeContactModel.firstname.ilike(pattern),
                            RoundcubeContactModel.surname.ilike(pattern),
                            RoundcubeContactModel.words.ilike(pattern),
                        )
                    )
                total = len(session.execute(total_stmt).all())

                # Pagination
                stmt = (
                    stmt.order_by(RoundcubeContactModel.name.asc())
                    .offset(offset)
                    .limit(limit)
                )
                rows = session.execute(stmt).scalars().all()
                return [self._to_domain(r, account) for r in rows], total

        except SQLAlchemyError as e:
            self._logger.error("Error al listar contactos: %s", e)
            raise ContactsDomainException(
                f"Error en base de datos al listar contactos: {e}"
            ) from e

    def get_contact_by_id(self, contact_id: str, account: str) -> Contact | None:
        try:
            cid = int(contact_id)
        except (ValueError, TypeError):
            return None

        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                stmt = select(RoundcubeContactModel).where(
                    RoundcubeContactModel.contact_id == cid,
                    RoundcubeContactModel.user_id == user_id,
                    RoundcubeContactModel.del_ == 0,
                )
                row = session.execute(stmt).scalar_one_or_none()
                if not row:
                    return None
                return self._to_domain(row, account)
        except SQLAlchemyError as e:
            self._logger.error("Error al obtener contacto %s: %s", contact_id, e)
            raise ContactsDomainException(
                f"Error en base de datos al obtener contacto: {e}"
            ) from e

    def create_contact(self, contact: Contact, account: str) -> Contact:
        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                words = f"{contact.nombre} {contact.email} {contact.telefono} {contact.organizacion}".strip()
                vcard_text = contact.vcard or VCardFormatterService.generate_vcard(
                    name=contact.nombre,
                    firstname=contact.nombre_pila,
                    surname=contact.apellido,
                    email=contact.email,
                    phone=contact.telefono,
                    organization=contact.organizacion,
                    note=contact.notas,
                )

                model = RoundcubeContactModel(
                    user_id=user_id,
                    changed=datetime.now(timezone.utc).replace(tzinfo=None),
                    del_=0,
                    name=contact.nombre,
                    email=contact.email,
                    firstname=contact.nombre_pila,
                    surname=contact.apellido,
                    vcard=vcard_text,
                    words=words,
                )
                session.add(model)
                session.commit()
                session.refresh(model)
                return self._to_domain(model, account)
        except SQLAlchemyError as e:
            self._logger.error("Error al crear contacto: %s", e)
            raise ContactsDomainException(
                f"Error en base de datos al crear contacto: {e}"
            ) from e

    def update_contact(self, contact: Contact, account: str) -> Contact:
        try:
            cid = int(contact.id_contacto)
        except (ValueError, TypeError) as e:
            raise ContactsDomainException(
                f"ID de contacto inválido: {contact.id_contacto}"
            ) from e

        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                stmt = select(RoundcubeContactModel).where(
                    RoundcubeContactModel.contact_id == cid,
                    RoundcubeContactModel.user_id == user_id,
                    RoundcubeContactModel.del_ == 0,
                )
                model = session.execute(stmt).scalar_one_or_none()
                if not model:
                    raise ContactsDomainException(
                        f"Contacto con ID {cid} no encontrado para actualización."
                    )

                words = f"{contact.nombre} {contact.email} {contact.telefono} {contact.organizacion}".strip()
                vcard_text = contact.vcard or VCardFormatterService.generate_vcard(
                    name=contact.nombre,
                    firstname=contact.nombre_pila,
                    surname=contact.apellido,
                    email=contact.email,
                    phone=contact.telefono,
                    organization=contact.organizacion,
                    note=contact.notas,
                )
                model.name = contact.nombre
                model.firstname = contact.nombre_pila
                model.surname = contact.apellido
                model.email = contact.email
                model.vcard = vcard_text
                model.words = words
                model.changed = datetime.now(timezone.utc).replace(tzinfo=None)

                session.commit()
                session.refresh(model)
                return self._to_domain(model, account)
        except SQLAlchemyError as e:
            self._logger.error("Error al actualizar contacto %s: %s", contact.id_contacto, e)
            raise ContactsDomainException(
                f"Error en base de datos al actualizar contacto: {e}"
            ) from e

    def delete_contact(self, contact_id: str, account: str) -> bool:
        try:
            cid = int(contact_id)
        except (ValueError, TypeError):
            return False

        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                stmt = select(RoundcubeContactModel).where(
                    RoundcubeContactModel.contact_id == cid,
                    RoundcubeContactModel.user_id == user_id,
                    RoundcubeContactModel.del_ == 0,
                )
                model = session.execute(stmt).scalar_one_or_none()
                if not model:
                    return False

                model.del_ = 1
                model.changed = datetime.now(timezone.utc).replace(tzinfo=None)
                session.commit()
                return True
        except SQLAlchemyError as e:
            self._logger.error("Error al eliminar contacto %s: %s", contact_id, e)
            raise ContactsDomainException(
                f"Error en base de datos al eliminar contacto: {e}"
            ) from e

    def list_groups(self, account: str) -> list[ContactGroup]:
        return []
