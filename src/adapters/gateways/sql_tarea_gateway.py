"""Gateway relacional SQLAlchemy para persistencia y gestión de tareas (To-Do List)."""

import json
import os
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Engine,
    String,
    Text,
    create_engine,
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
from src.domain.tareas.entities import Tarea
from src.domain.tareas.ports import FiltrosTarea, TareaRepositoryPort
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)


class Base(DeclarativeBase):
    """Base declarativa para el modelo de persistencia de tareas."""


class TareaModel(Base):
    """Tabla relacional para almacenamiento de tareas y pendientes."""

    __tablename__ = "tareas"

    id_tarea: Mapped[str] = mapped_column(String(64), primary_key=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    prioridad: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default="MEDIA"
    )
    estado: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default="PENDIENTE"
    )
    categoria: Mapped[str] = mapped_column(
        String(30), index=True, nullable=False, default="GENERAL"
    )
    docente_cuit: Mapped[str | None] = mapped_column(
        String(20), index=True, nullable=True
    )
    id_referencia: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    tipo_referencia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    fecha_completada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metadatos_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class SQLTareaGateway(TareaRepositoryPort):
    """Implementación de TareaRepositoryPort basada en SQLAlchemy (SQLite / MySQL)."""

    def __init__(
        self, database_url: str | None = None, logger: LoggerPort | None = None
    ) -> None:
        self._logger = logger or NullLogger()
        if database_url:
            self._db_url = database_url
        else:
            self._db_url = os.getenv("DATABASE_URL") or "sqlite:///data/hub.db"

        connect_args = {}
        if self._db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self._engine: Engine = create_engine(
            self._db_url,
            connect_args=connect_args,
            echo=False,
            future=True,
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )
        self._init_db()

    def _init_db(self) -> None:
        try:
            Base.metadata.create_all(self._engine)
        except SQLAlchemyError as e:
            self._logger.warning(
                "No se pudo crear schema de tareas automáticamente: %s", e
            )

    def _get_session(self) -> Session:
        return self._session_factory()

    def guardar(self, tarea: Tarea) -> Tarea:
        with self._get_session() as session:
            model = TareaModel(
                id_tarea=tarea.id_tarea,
                titulo=tarea.titulo,
                descripcion=tarea.descripcion,
                fecha_limite=tarea.fecha_limite,
                prioridad=tarea.prioridad.value,
                estado=tarea.estado.value,
                categoria=tarea.categoria.value,
                docente_cuit=tarea.docente_cuit,
                id_referencia=tarea.id_referencia,
                tipo_referencia=tarea.tipo_referencia,
                fecha_creacion=tarea.fecha_creacion,
                fecha_completada=tarea.fecha_completada,
                tags_json=json.dumps(list(tarea.tags), ensure_ascii=False),
                metadatos_json=json.dumps(
                    tarea.metadatos, ensure_ascii=False, default=str
                ),
            )
            session.merge(model)
            session.commit()
            return tarea

    def obtener_por_id(self, id_tarea: str) -> Tarea | None:
        with self._get_session() as session:
            stmt = select(TareaModel).where(TareaModel.id_tarea == id_tarea)
            model = session.scalar(stmt)
            if not model:
                return None
            return self._model_to_entity(model)

    def listar(self, filtros: FiltrosTarea | None = None) -> list[Tarea]:
        with self._get_session() as session:
            stmt = select(TareaModel)

            if filtros:
                if filtros.estado:
                    stmt = stmt.where(TareaModel.estado == filtros.estado.value)
                if filtros.categoria:
                    stmt = stmt.where(TareaModel.categoria == filtros.categoria.value)
                if filtros.prioridad:
                    stmt = stmt.where(TareaModel.prioridad == filtros.prioridad.value)
                if filtros.docente_cuit:
                    cuit_clean = filtros.docente_cuit.replace("-", "").strip()
                    stmt = stmt.where(TareaModel.docente_cuit == cuit_clean)
                if filtros.id_referencia:
                    stmt = stmt.where(TareaModel.id_referencia == filtros.id_referencia)
                if filtros.fecha_limite_desde:
                    stmt = stmt.where(
                        TareaModel.fecha_limite >= filtros.fecha_limite_desde
                    )
                if filtros.fecha_limite_hasta:
                    stmt = stmt.where(
                        TareaModel.fecha_limite <= filtros.fecha_limite_hasta
                    )

                stmt = stmt.order_by(
                    TareaModel.fecha_limite.asc(),
                    TareaModel.fecha_creacion.desc(),
                )
                if filtros.offset is not None:
                    stmt = stmt.offset(filtros.offset)
                if filtros.limite is not None:
                    stmt = stmt.limit(filtros.limite)
            else:
                stmt = stmt.order_by(
                    TareaModel.fecha_limite.asc(),
                    TareaModel.fecha_creacion.desc(),
                )

            models = session.scalars(stmt).all()
            return [self._model_to_entity(m) for m in models]

    def actualizar(self, tarea: Tarea) -> Tarea:
        with self._get_session() as session:
            stmt = select(TareaModel).where(TareaModel.id_tarea == tarea.id_tarea)
            model = session.scalar(stmt)
            if not model:
                return self.guardar(tarea)

            model.titulo = tarea.titulo
            model.descripcion = tarea.descripcion
            model.fecha_limite = tarea.fecha_limite
            model.prioridad = tarea.prioridad.value
            model.estado = tarea.estado.value
            model.categoria = tarea.categoria.value
            model.docente_cuit = tarea.docente_cuit
            model.id_referencia = tarea.id_referencia
            model.tipo_referencia = tarea.tipo_referencia
            model.fecha_completada = tarea.fecha_completada
            model.tags_json = json.dumps(list(tarea.tags), ensure_ascii=False)
            model.metadatos_json = json.dumps(
                tarea.metadatos, ensure_ascii=False, default=str
            )

            session.commit()
            return tarea

    def eliminar(self, id_tarea: str) -> bool:
        with self._get_session() as session:
            stmt = select(TareaModel).where(TareaModel.id_tarea == id_tarea)
            model = session.scalar(stmt)
            if not model:
                return False
            session.delete(model)
            session.commit()
            return True

    @staticmethod
    def _model_to_entity(model: TareaModel) -> Tarea:
        try:
            tags = tuple(json.loads(model.tags_json))
        except (ValueError, TypeError):
            tags = ()

        try:
            meta = dict(json.loads(model.metadatos_json))
        except (ValueError, TypeError):
            meta = {}

        return Tarea(
            id_tarea=model.id_tarea,
            titulo=model.titulo,
            descripcion=model.descripcion or "",
            fecha_limite=model.fecha_limite,
            prioridad=PrioridadTarea(model.prioridad),
            estado=EstadoTarea(model.estado),
            categoria=CategoriaTarea(model.categoria),
            docente_cuit=model.docente_cuit,
            id_referencia=model.id_referencia,
            tipo_referencia=model.tipo_referencia,
            fecha_creacion=model.fecha_creacion,
            fecha_completada=model.fecha_completada,
            tags=tags,
            metadatos=meta,
        )
