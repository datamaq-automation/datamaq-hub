"""Gateway SQLAlchemy para el seguimiento diferido de designaciones no liquidadas."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Engine,
    Float,
    Integer,
    String,
    create_engine,
    select,
    update,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.recibos.entities import DesignacionNoLiquidada
from src.domain.recibos.ports import SeguimientoNoLiquidadosRepositoryPort


class Base(DeclarativeBase):
    pass


class DesignacionNoLiquidadaModel(Base):
    __tablename__ = "recibos_no_liquidados"

    id_seguimiento: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_recibo: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    id_designacion: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    docente_cuit: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    mes_pago: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    secuencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    escuela_codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    modulos: Mapped[float] = mapped_column(Float, default=0.0)
    situacion_revista: Mapped[str] = mapped_column(String(20), nullable=False)
    periodos_consecutivos: Mapped[int] = mapped_column(Integer, default=1)
    alerta_2_periodos: Mapped[bool] = mapped_column(Boolean, default=False)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    id_recibo_resolucion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


def init_seguimiento_db(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if "sqlite" in database_url else {}
    if database_url.startswith("sqlite:///:memory:"):
        engine = create_engine(
            database_url,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(database_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


class SQLSeguimientoNoLiquidadosGateway(SeguimientoNoLiquidadosRepositoryPort):
    """Implementación SQLite/SQLAlchemy para seguimiento de cargos no cobrados."""

    def __init__(
        self,
        database_url: str | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        self._db_url = database_url or os.environ.get(
            "DATABASE_URL", "sqlite:///data/leads.db"
        )
        self._logger = logger or NullLogger()
        self._engine = init_seguimiento_db(self._db_url)
        self._session_factory = sessionmaker(
            bind=self._engine, autoflush=False, expire_on_commit=False
        )

    def _get_session(self) -> Session:
        return self._session_factory()

    def guardar(self, item: DesignacionNoLiquidada) -> DesignacionNoLiquidada:
        """Persiste un registro de seguimiento individual."""
        id_seg = item.id_seguimiento or f"seg_{uuid.uuid4().hex[:12]}"
        model = DesignacionNoLiquidadaModel(
            id_seguimiento=id_seg,
            id_recibo=item.id_recibo,
            id_designacion=item.id_designacion,
            docente_cuit=item.docente_cuit,
            mes_pago=item.mes_pago,
            secuencia=item.secuencia,
            escuela_codigo=item.escuela_codigo,
            modulos=item.modulos,
            situacion_revista=item.situacion_revista,
            periodos_consecutivos=item.periodos_consecutivos,
            alerta_2_periodos=item.alerta_2_periodos,
            estado=item.estado,
            id_recibo_resolucion=item.id_recibo_resolucion,
        )
        with self._get_session() as session, session.begin():
            session.merge(model)
        item.id_seguimiento = id_seg
        return item

    def guardar_batch(self, items: list[DesignacionNoLiquidada]) -> None:
        """Persiste una lista de registros de seguimiento."""
        if not items:
            return
        with self._get_session() as session, session.begin():
            for item in items:
                id_seg = item.id_seguimiento or f"seg_{uuid.uuid4().hex[:12]}"
                model = DesignacionNoLiquidadaModel(
                    id_seguimiento=id_seg,
                    id_recibo=item.id_recibo,
                    id_designacion=item.id_designacion,
                    docente_cuit=item.docente_cuit,
                    mes_pago=item.mes_pago,
                    secuencia=item.secuencia,
                    escuela_codigo=item.escuela_codigo,
                    modulos=item.modulos,
                    situacion_revista=item.situacion_revista,
                    periodos_consecutivos=item.periodos_consecutivos,
                    alerta_2_periodos=item.alerta_2_periodos,
                    estado=item.estado,
                    id_recibo_resolucion=item.id_recibo_resolucion,
                )
                session.merge(model)
                item.id_seguimiento = id_seg

    def obtener_por_recibo(self, id_recibo: str) -> list[DesignacionNoLiquidada]:
        """Obtiene las designaciones no liquidadas para un recibo específico."""
        with self._get_session() as session:
            stmt = select(DesignacionNoLiquidadaModel).where(
                DesignacionNoLiquidadaModel.id_recibo == id_recibo
            )
            models = session.scalars(stmt).all()
            return [self._to_domain(m) for m in models]

    def listar(
        self,
        docente_cuit: str | None = None,
        solo_pendientes: bool = False,
        solo_alertas: bool = False,
    ) -> list[DesignacionNoLiquidada]:
        """Lista registros con filtros opcionales."""
        with self._get_session() as session:
            stmt = select(DesignacionNoLiquidadaModel)
            if docente_cuit:
                stmt = stmt.where(
                    DesignacionNoLiquidadaModel.docente_cuit == docente_cuit
                )
            if solo_pendientes:
                stmt = stmt.where(DesignacionNoLiquidadaModel.estado == "PENDIENTE")
            if solo_alertas:
                stmt = stmt.where(
                    DesignacionNoLiquidadaModel.alerta_2_periodos.is_(True)
                )
            stmt = stmt.order_by(DesignacionNoLiquidadaModel.mes_pago.desc())
            models = session.scalars(stmt).all()
            return [self._to_domain(m) for m in models]

    def obtener_ultimas_pendientes(
        self, docente_cuit: str
    ) -> list[DesignacionNoLiquidada]:
        """Obtiene las designaciones pendientes más recientes de un docente."""
        with self._get_session() as session:
            stmt = (
                select(DesignacionNoLiquidadaModel)
                .where(
                    DesignacionNoLiquidadaModel.docente_cuit == docente_cuit,
                    DesignacionNoLiquidadaModel.estado == "PENDIENTE",
                )
                .order_by(DesignacionNoLiquidadaModel.mes_pago.desc())
            )
            models = session.scalars(stmt).all()
            return [self._to_domain(m) for m in models]

    def resolver_designaciones(
        self, docente_cuit: str, ids_designacion: list[str], id_recibo_resolucion: str
    ) -> None:
        """Marca como RESUELTO el seguimiento de designaciones liquidadas en un período posterior."""
        if not ids_designacion:
            return
        with self._get_session() as session, session.begin():
            stmt = (
                update(DesignacionNoLiquidadaModel)
                .where(
                    DesignacionNoLiquidadaModel.docente_cuit == docente_cuit,
                    DesignacionNoLiquidadaModel.id_designacion.in_(ids_designacion),
                    DesignacionNoLiquidadaModel.estado == "PENDIENTE",
                )
                .values(
                    estado="RESUELTO",
                    id_recibo_resolucion=id_recibo_resolucion,
                )
            )
            session.execute(stmt)

    @staticmethod
    def _to_domain(model: DesignacionNoLiquidadaModel) -> DesignacionNoLiquidada:
        return DesignacionNoLiquidada(
            id_seguimiento=model.id_seguimiento,
            id_recibo=model.id_recibo,
            id_designacion=model.id_designacion,
            docente_cuit=model.docente_cuit,
            mes_pago=model.mes_pago,
            secuencia=model.secuencia,
            escuela_codigo=model.escuela_codigo,
            modulos=model.modulos,
            situacion_revista=model.situacion_revista,
            periodos_consecutivos=model.periodos_consecutivos,
            alerta_2_periodos=model.alerta_2_periodos,
            estado=model.estado,
            id_recibo_resolucion=model.id_recibo_resolucion,
            creado_en=model.creado_en.isoformat() if model.creado_en else "",
        )
