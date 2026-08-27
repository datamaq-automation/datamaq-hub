"""SQLAlchemy Gateway implementing CalendarRepositoryPort for Roundcube/MySQL and SQLite."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import cast

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

from src.adapters.gateways.sql_contacts_gateway import (
    ContactsBase,
    RoundcubeUserModel,
)
from src.domain.calendar.entities import Calendar, CalendarEvent
from src.domain.calendar.exceptions import CalendarDomainException
from src.domain.calendar.ports import CalendarRepositoryPort

logger = logging.getLogger(__name__)


class CalendarBase(DeclarativeBase):
    """Base declarativa para tablas de calendario."""


class RoundcubeCalendarModel(CalendarBase):
    """Modelo relacional de calendarios de Roundcube."""

    __tablename__ = "calendars"

    calendar_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, default=0)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Principal")
    color: Mapped[str] = mapped_column(String(8), nullable=False, default="#0288D1")
    showalarms: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)


class RoundcubeEventModel(CalendarBase):
    """Modelo relacional de eventos de calendario de Roundcube."""

    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calendar_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("calendars.calendar_id"), nullable=False, index=True
    )
    uid: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    changed: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    categories: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    all_day: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CONFIRMED")
    attendees: Mapped[str | None] = mapped_column(Text, nullable=True)


class SQLCalendarGateway(CalendarRepositoryPort):
    """Gateway for calendar event storage supporting MySQL and SQLite."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ.get(
            "ROUNDCUBE_DB_URL", "sqlite:///data/roundcube.db"
        )
        self._engine: Engine = create_engine(self.database_url, pool_pre_ping=True)
        # Create users table schema if needed
        ContactsBase.metadata.create_all(self._engine)
        CalendarBase.metadata.create_all(self._engine)
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

    def get_or_create_default_calendar(self, account: str) -> Calendar:
        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                stmt = select(RoundcubeCalendarModel).where(
                    RoundcubeCalendarModel.user_id == user_id
                )
                cal = session.execute(stmt).scalar_one_or_none()
                if cal:
                    return Calendar(
                        id_calendario=str(cal.calendar_id),
                        nombre=cal.name,
                        color=cal.color,
                        cuenta=account,
                    )

                new_cal = RoundcubeCalendarModel(
                    user_id=user_id,
                    name="Principal",
                    color="#0288D1",
                    showalarms=1,
                )
                session.add(new_cal)
                session.commit()
                session.refresh(new_cal)
                return Calendar(
                    id_calendario=str(new_cal.calendar_id),
                    nombre=new_cal.name,
                    color=new_cal.color,
                    cuenta=account,
                )
        except SQLAlchemyError as e:
            logger.error("Error al obtener o crear calendario: %s", e)
            raise CalendarDomainException(
                f"Error en base de datos al resolver calendario: {e}"
            ) from e

    def _to_domain(self, model: RoundcubeEventModel, account: str) -> CalendarEvent:
        """Transforms ORM model into immutable domain CalendarEvent entity."""
        asistentes: list[str] = []
        if model.attendees:
            try:
                raw = json.loads(model.attendees)
                if isinstance(raw, list):
                    for item in cast(list[object], raw):
                        if isinstance(item, str):
                            asistentes.append(item)
                        elif isinstance(item, dict):
                            dict_item = cast(dict[object, object], item)
                            val = dict_item.get("email")
                            if isinstance(val, str):
                                asistentes.append(val)
            except (json.JSONDecodeError, TypeError, KeyError):
                asistentes = [
                    a.strip() for a in model.attendees.split(",") if a.strip()
                ]

        return CalendarEvent(
            id_evento=str(model.event_id),
            id_calendario=str(model.calendar_id),
            uid=model.uid,
            titulo=model.title,
            inicio=model.start,
            fin=model.end,
            descripcion=model.description,
            ubicacion=model.location,
            todo_el_dia=bool(model.all_day),
            estado=model.status,
            asistentes=asistentes,
            url=model.url,
            categorias=model.categories,
            cuenta=account,
        )

    def list_events(
        self,
        account: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[CalendarEvent]:
        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                # Find all calendars of this user
                cals_stmt = select(RoundcubeCalendarModel.calendar_id).where(
                    RoundcubeCalendarModel.user_id == user_id
                )
                cal_ids = session.execute(cals_stmt).scalars().all()
                if not cal_ids:
                    return []

                stmt = select(RoundcubeEventModel).where(
                    RoundcubeEventModel.calendar_id.in_(cal_ids)
                )

                if start_date is not None:
                    stmt = stmt.where(RoundcubeEventModel.end >= start_date)
                if end_date is not None:
                    stmt = stmt.where(RoundcubeEventModel.start <= end_date)

                stmt = stmt.order_by(RoundcubeEventModel.start.asc()).limit(limit)
                rows = session.execute(stmt).scalars().all()
                return [self._to_domain(r, account) for r in rows]

        except SQLAlchemyError as e:
            logger.error("Error al listar eventos de calendario: %s", e)
            raise CalendarDomainException(
                f"Error en base de datos al listar eventos: {e}"
            ) from e

    def get_event_by_id(self, event_id: str, account: str) -> CalendarEvent | None:
        try:
            with self._get_session() as session:
                user_id = self._get_or_create_user_id(session, account)
                cals_stmt = select(RoundcubeCalendarModel.calendar_id).where(
                    RoundcubeCalendarModel.user_id == user_id
                )
                cal_ids = session.execute(cals_stmt).scalars().all()
                if not cal_ids:
                    return None

                stmt = select(RoundcubeEventModel).where(
                    RoundcubeEventModel.calendar_id.in_(cal_ids)
                )
                try:
                    eid_int = int(event_id)
                    stmt = stmt.where(
                        or_(
                            RoundcubeEventModel.event_id == eid_int,
                            RoundcubeEventModel.uid == event_id,
                        )
                    )
                except ValueError:
                    stmt = stmt.where(RoundcubeEventModel.uid == event_id)

                row = session.execute(stmt).scalar_one_or_none()
                if not row:
                    return None
                return self._to_domain(row, account)

        except SQLAlchemyError as e:
            logger.error("Error al obtener evento %s: %s", event_id, e)
            raise CalendarDomainException(
                f"Error en base de datos al obtener evento: {e}"
            ) from e

    def create_event(self, event: CalendarEvent, account: str) -> CalendarEvent:
        try:
            with self._get_session() as session:
                cal_id_int = int(event.id_calendario)
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                event_uid = event.uid or str(uuid.uuid4())
                attendees_json = json.dumps(event.asistentes)

                model = RoundcubeEventModel(
                    calendar_id=cal_id_int,
                    uid=event_uid,
                    created=now,
                    changed=now,
                    start=event.inicio,
                    end=event.fin,
                    title=event.titulo,
                    description=event.descripcion,
                    location=event.ubicacion,
                    categories=event.categorias,
                    url=event.url,
                    all_day=1 if event.todo_el_dia else 0,
                    status=event.estado,
                    attendees=attendees_json,
                )
                session.add(model)
                session.commit()
                session.refresh(model)
                return self._to_domain(model, account)

        except SQLAlchemyError as e:
            logger.error("Error al crear evento: %s", e)
            raise CalendarDomainException(
                f"Error en base de datos al crear evento: {e}"
            ) from e

    def update_event(self, event: CalendarEvent, account: str) -> CalendarEvent:
        try:
            eid_int = int(event.id_evento)
        except (ValueError, TypeError) as e:
            raise CalendarDomainException(
                f"ID de evento inválido: {event.id_evento}"
            ) from e

        try:
            with self._get_session() as session:
                stmt = select(RoundcubeEventModel).where(
                    RoundcubeEventModel.event_id == eid_int
                )
                model = session.execute(stmt).scalar_one_or_none()
                if not model:
                    raise CalendarDomainException(
                        f"Evento con ID {eid_int} no encontrado para actualización."
                    )

                now = datetime.now(timezone.utc).replace(tzinfo=None)
                model.title = event.titulo
                model.start = event.inicio
                model.end = event.fin
                model.description = event.descripcion
                model.location = event.ubicacion
                model.all_day = 1 if event.todo_el_dia else 0
                model.status = event.estado
                model.attendees = json.dumps(event.asistentes)
                model.url = event.url
                model.categories = event.categorias
                model.changed = now

                session.commit()
                session.refresh(model)
                return self._to_domain(model, account)

        except SQLAlchemyError as e:
            logger.error("Error al actualizar evento %s: %s", event.id_evento, e)
            raise CalendarDomainException(
                f"Error en base de datos al actualizar evento: {e}"
            ) from e

    def delete_event(self, event_id: str, account: str) -> bool:
        try:
            eid_int = int(event_id)
        except (ValueError, TypeError):
            return False

        try:
            with self._get_session() as session:
                stmt = select(RoundcubeEventModel).where(
                    RoundcubeEventModel.event_id == eid_int
                )
                model = session.execute(stmt).scalar_one_or_none()
                if not model:
                    return False

                session.delete(model)
                session.commit()
                return True
        except SQLAlchemyError as e:
            logger.error("Error al eliminar evento %s: %s", event_id, e)
            raise CalendarDomainException(
                f"Error en base de datos al eliminar evento: {e}"
            ) from e
