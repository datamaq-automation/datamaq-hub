"""Gateway relacional SQLAlchemy para persistencia inmutable / temporal de designaciones docentes."""

import logging
import os
import sqlite3
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    String,
    create_engine,
    select,
    text,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from src.domain.horarios_docencia.entities import (
    DesignacionDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    MotivoCese,
    PeriodoVigencia,
    SituacionRevista,
    Turno,
    normalizar_cuit,
)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarativa para los modelos de horarios_docencia."""


class DesignacionDocenteModel(Base):
    """Tabla de designaciones docentes con intervalos de vigencia temporal."""

    __tablename__ = "horarios_designaciones"

    id_designacion: Mapped[str] = mapped_column(String(64), primary_key=True)
    docente_cuit: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    ige: Mapped[str] = mapped_column(String(50), index=True, nullable=False, default="")
    establecimiento: Mapped[str] = mapped_column(String(255), nullable=False)
    distrito: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    cargo_asignatura: Mapped[str] = mapped_column(String(255), nullable=False)
    revista: Mapped[str] = mapped_column(String(20), nullable=False, default="TITULAR")
    modulos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    es_cargo_base: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_desde: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    fecha_hasta: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    motivo_cese: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observaciones: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    cupof: Mapped[str] = mapped_column(
        String(50), nullable=False, default="", index=True
    )
    secuencia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codigo_acto: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    escuela_numero: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    reemplaza_a: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    articulo_licencia: Mapped[str] = mapped_column(
        String(50), nullable=False, default=""
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    horarios: Mapped[list["HorarioBloqueModel"]] = relationship(
        "HorarioBloqueModel",
        back_populates="designacion",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class HorarioBloqueModel(Base):
    """Tabla de bloques horarios asociados a una designación."""

    __tablename__ = "horarios_designaciones_bloques"

    id_bloque: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_designacion: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("horarios_designaciones.id_designacion"),
        index=True,
        nullable=False,
    )
    dia: Mapped[str] = mapped_column(String(20), nullable=False)
    hora_inicio: Mapped[str] = mapped_column(String(5), nullable=False)
    hora_fin: Mapped[str] = mapped_column(String(5), nullable=False)
    turno: Mapped[str] = mapped_column(String(20), nullable=False, default="MANANA")

    designacion: Mapped["DesignacionDocenteModel"] = relationship(
        "DesignacionDocenteModel", back_populates="horarios"
    )


def init_horarios_db(database_url: str) -> None:
    """Crea las tablas de horarios_docencia si no existen y actualiza columnas si faltan."""
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        Base.metadata.create_all(engine, checkfirst=True)
        with engine.connect() as conn:
            if database_url.startswith("sqlite") and ":memory:" not in database_url:
                conn.execute(text("PRAGMA journal_mode=WAL"))
            try:
                cursor = conn.execute(text("PRAGMA table_info(horarios_designaciones)"))
                existing_cols = {row[1] for row in cursor.fetchall()}
                if existing_cols:
                    cols_to_add = [
                        ("observaciones", "VARCHAR(500) DEFAULT '' NOT NULL"),
                        ("cupof", "VARCHAR(50) DEFAULT '' NOT NULL"),
                        ("secuencia", "INTEGER"),
                        ("codigo_acto", "VARCHAR(50) DEFAULT '' NOT NULL"),
                        ("escuela_numero", "VARCHAR(50) DEFAULT '' NOT NULL"),
                        ("reemplaza_a", "VARCHAR(100) DEFAULT '' NOT NULL"),
                        ("articulo_licencia", "VARCHAR(50) DEFAULT '' NOT NULL"),
                    ]
                    for col_name, col_type in cols_to_add:
                        if col_name not in existing_cols:
                            conn.execute(
                                text(
                                    f"ALTER TABLE horarios_designaciones ADD COLUMN {col_name} {col_type}"
                                )
                            )
                    conn.commit()
            except (
                SQLAlchemyError,
                sqlite3.Error,
                OSError,
                ValueError,
                RuntimeError,
            ) as exc:
                logger.debug(
                    "No se pudieron verificar columnas de horarios_designaciones: %s",
                    exc,
                )
    except (SQLAlchemyError, sqlite3.Error, OSError, ValueError, RuntimeError) as e:
        logger.warning("No se pudo inicializar schema de horarios_docencia: %s", e)


from sqlalchemy.pool import StaticPool


class SQLDesignacionDocenteGateway(DesignacionDocenteRepositoryPort):
    """Implementación del repositorio temporal de designaciones docentes usando SQLAlchemy."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ.get(
            "DATABASE_URL", "sqlite:///data/leads.db"
        )
        if ":memory:" in self.database_url:
            self._engine: Engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self._engine: Engine = create_engine(self.database_url, pool_pre_ping=True)
        Base.metadata.create_all(self._engine)
        self._check_and_migrate_columns(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def _check_and_migrate_columns(self, engine: Engine) -> None:
        try:
            with engine.connect() as conn:
                cursor = conn.execute(text("PRAGMA table_info(horarios_designaciones)"))
                existing_cols = {row[1] for row in cursor.fetchall()}
                if existing_cols:
                    cols_to_add = [
                        ("observaciones", "VARCHAR(500) DEFAULT '' NOT NULL"),
                        ("cupof", "VARCHAR(50) DEFAULT '' NOT NULL"),
                        ("secuencia", "INTEGER"),
                        ("codigo_acto", "VARCHAR(50) DEFAULT '' NOT NULL"),
                        ("escuela_numero", "VARCHAR(50) DEFAULT '' NOT NULL"),
                        ("reemplaza_a", "VARCHAR(100) DEFAULT '' NOT NULL"),
                        ("articulo_licencia", "VARCHAR(50) DEFAULT '' NOT NULL"),
                    ]
                    for col_name, col_type in cols_to_add:
                        if col_name not in existing_cols:
                            conn.execute(
                                text(
                                    f"ALTER TABLE horarios_designaciones ADD COLUMN {col_name} {col_type}"
                                )
                            )
                    conn.commit()
        except (SQLAlchemyError, OSError, ValueError, RuntimeError) as e:
            logger.debug(f"Migración omitida: {e}")

    def _get_session(self) -> Session:
        return self._session_factory()

    def _to_domain(self, model: DesignacionDocenteModel) -> DesignacionDocente:
        """Mapea de modelo SQLAlchemy a entidad inmutable de Dominio."""
        horarios: list[HorarioBloque] = []
        for h in model.horarios:
            horarios.append(
                HorarioBloque(
                    dia=DiaSemana[h.dia],
                    franja=FranjaHoraria(
                        hora_inicio=h.hora_inicio, hora_fin=h.hora_fin
                    ),
                    turno=Turno[h.turno]
                    if h.turno in Turno.__members__
                    else Turno.MANANA,
                )
            )

        motivo = (
            MotivoCese[model.motivo_cese]
            if model.motivo_cese and model.motivo_cese in MotivoCese.__members__
            else None
        )

        return DesignacionDocente(
            id_designacion=model.id_designacion,
            docente_cuit=model.docente_cuit,
            ige=model.ige,
            establecimiento=model.establecimiento,
            distrito=model.distrito,
            cargo_asignatura=model.cargo_asignatura,
            revista=SituacionRevista[model.revista],
            vigencia=PeriodoVigencia(
                fecha_desde=model.fecha_desde,
                fecha_hasta=model.fecha_hasta,
            ),
            modulos=model.modulos,
            es_cargo_base=model.es_cargo_base,
            horarios=tuple(horarios),
            motivo_cese=motivo,
            observaciones=getattr(model, "observaciones", "") or "",
            cupof=getattr(model, "cupof", "") or "",
            secuencia=getattr(model, "secuencia", None),
            codigo_acto=getattr(model, "codigo_acto", "") or "",
            escuela_numero=getattr(model, "escuela_numero", "") or "",
            reemplaza_a=getattr(model, "reemplaza_a", "") or "",
            articulo_licencia=getattr(model, "articulo_licencia", "") or "",
            creado_en=model.creado_en,
        )

    def guardar(self, designacion: DesignacionDocente) -> DesignacionDocente:
        """Inserta una nueva designación y sus bloques de forma inmutable."""
        with self._get_session() as session:
            clean_cuit = normalizar_cuit(designacion.docente_cuit)
            model = DesignacionDocenteModel(
                id_designacion=designacion.id_designacion or str(uuid.uuid4()),
                docente_cuit=clean_cuit,
                ige=designacion.ige.strip(),
                establecimiento=designacion.establecimiento.strip(),
                distrito=designacion.distrito.strip(),
                cargo_asignatura=designacion.cargo_asignatura.strip(),
                revista=designacion.revista.value,
                modulos=designacion.modulos,
                es_cargo_base=designacion.es_cargo_base,
                fecha_desde=designacion.vigencia.fecha_desde,
                fecha_hasta=designacion.vigencia.fecha_hasta,
                motivo_cese=(
                    designacion.motivo_cese.value
                    if isinstance(designacion.motivo_cese, MotivoCese)
                    else str(designacion.motivo_cese)
                    if designacion.motivo_cese is not None
                    else None
                ),
                observaciones=designacion.observaciones,
                cupof=designacion.cupof,
                secuencia=designacion.secuencia,
                codigo_acto=designacion.codigo_acto,
                escuela_numero=designacion.escuela_numero,
                reemplaza_a=designacion.reemplaza_a,
                articulo_licencia=designacion.articulo_licencia,
                creado_en=designacion.creado_en,
            )

            for h in designacion.horarios:
                model.horarios.append(
                    HorarioBloqueModel(
                        dia=h.dia.value,
                        hora_inicio=h.franja.hora_inicio,
                        hora_fin=h.franja.hora_fin,
                        turno=h.turno.value,
                    )
                )

            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    def obtener_por_id(self, id_designacion: str) -> DesignacionDocente | None:
        """Recupera una designación por su ID único."""
        with self._get_session() as session:
            stmt = select(DesignacionDocenteModel).where(
                DesignacionDocenteModel.id_designacion == id_designacion.strip()
            )
            model = session.scalars(stmt).unique().first()
            return self._to_domain(model) if model else None

    def obtener_vigentes_en_fecha(
        self, docente_cuit: str, fecha: date
    ) -> tuple[DesignacionDocente, ...]:
        """Recupera todas las designaciones vigentes en una fecha específica."""
        with self._get_session() as session:
            clean_cuit = normalizar_cuit(docente_cuit)
            stmt = (
                select(DesignacionDocenteModel)
                .where(
                    DesignacionDocenteModel.docente_cuit == clean_cuit,
                    DesignacionDocenteModel.fecha_desde <= fecha,
                    (DesignacionDocenteModel.fecha_hasta.is_(None))
                    | (DesignacionDocenteModel.fecha_hasta >= fecha),
                )
                .order_by(DesignacionDocenteModel.fecha_desde.asc())
            )
            models = session.scalars(stmt).unique().all()
            return tuple(self._to_domain(m) for m in models)

    def obtener_historial(self, docente_cuit: str) -> tuple[DesignacionDocente, ...]:
        """Recupera todas las designaciones (activas y pasadas) del docente."""
        with self._get_session() as session:
            clean_cuit = normalizar_cuit(docente_cuit)
            stmt = (
                select(DesignacionDocenteModel)
                .where(DesignacionDocenteModel.docente_cuit == clean_cuit)
                .order_by(DesignacionDocenteModel.fecha_desde.asc())
            )
            models = session.scalars(stmt).unique().all()
            return tuple(self._to_domain(m) for m in models)

    def cerrar_vigencia(
        self, id_designacion: str, fecha_hasta: date, motivo: MotivoCese
    ) -> DesignacionDocente | None:
        """Cierra la vigencia de una designación asignando fecha_hasta y motivo de cese."""
        with self._get_session() as session:
            stmt = select(DesignacionDocenteModel).where(
                DesignacionDocenteModel.id_designacion == id_designacion.strip()
            )
            model = session.scalars(stmt).unique().first()
            if not model:
                return None

            model.fecha_hasta = fecha_hasta
            model.motivo_cese = motivo.value
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    def listar(
        self,
        docente_cuit: str | None = None,
        vigentes_al: date | None = None,
        establecimiento: str | None = None,
        distrito: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[DesignacionDocente, ...]:
        """Lista designaciones docentes con filtros opcionales y paginación."""
        with self._get_session() as session:
            stmt = select(DesignacionDocenteModel)
            if docente_cuit:
                stmt = stmt.where(
                    DesignacionDocenteModel.docente_cuit
                    == normalizar_cuit(docente_cuit)
                )
            if vigentes_al:
                stmt = stmt.where(
                    DesignacionDocenteModel.fecha_desde <= vigentes_al,
                    (DesignacionDocenteModel.fecha_hasta.is_(None))
                    | (DesignacionDocenteModel.fecha_hasta >= vigentes_al),
                )
            if establecimiento:
                stmt = stmt.where(
                    DesignacionDocenteModel.establecimiento.ilike(
                        f"%{establecimiento.strip()}%"
                    )
                )
            if distrito:
                stmt = stmt.where(
                    DesignacionDocenteModel.distrito.ilike(f"%{distrito.strip()}%")
                )

            stmt = (
                stmt.order_by(DesignacionDocenteModel.fecha_desde.desc())
                .offset(offset)
                .limit(limit)
            )
            models = session.scalars(stmt).unique().all()
            return tuple(self._to_domain(m) for m in models)

    def actualizar(self, designacion: DesignacionDocente) -> DesignacionDocente | None:
        """Actualiza una designación existente por su ID."""
        with self._get_session() as session:
            stmt = select(DesignacionDocenteModel).where(
                DesignacionDocenteModel.id_designacion == designacion.id_designacion
            )
            model = session.scalars(stmt).unique().first()
            if not model:
                return None

            model.docente_cuit = normalizar_cuit(designacion.docente_cuit)
            model.ige = designacion.ige.strip()
            model.establecimiento = designacion.establecimiento.strip()
            model.distrito = designacion.distrito.strip()
            model.cargo_asignatura = designacion.cargo_asignatura.strip()
            model.revista = designacion.revista.value
            model.modulos = designacion.modulos
            model.es_cargo_base = designacion.es_cargo_base
            model.fecha_desde = designacion.vigencia.fecha_desde
            model.fecha_hasta = designacion.vigencia.fecha_hasta
            model.motivo_cese = (
                designacion.motivo_cese.value if designacion.motivo_cese else None
            )
            model.observaciones = designacion.observaciones
            model.cupof = designacion.cupof
            model.secuencia = designacion.secuencia
            model.codigo_acto = designacion.codigo_acto
            model.escuela_numero = designacion.escuela_numero
            model.reemplaza_a = designacion.reemplaza_a
            model.articulo_licencia = designacion.articulo_licencia

            # Actualizar bloques horarios
            model.horarios.clear()
            for h in designacion.horarios:
                model.horarios.append(
                    HorarioBloqueModel(
                        dia=h.dia.value,
                        hora_inicio=h.franja.hora_inicio,
                        hora_fin=h.franja.hora_fin,
                        turno=h.turno.value,
                    )
                )

            session.commit()
            session.refresh(model)
            return self._to_domain(model)

    def eliminar(self, id_designacion: str) -> bool:
        """Elimina físicamente una designación por su ID."""
        with self._get_session() as session:
            stmt = select(DesignacionDocenteModel).where(
                DesignacionDocenteModel.id_designacion == id_designacion.strip()
            )
            model = session.scalars(stmt).unique().first()
            if not model:
                return False

            session.delete(model)
            session.commit()
            return True
