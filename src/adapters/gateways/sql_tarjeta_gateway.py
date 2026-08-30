"""Gateway relacional SQLAlchemy para persistencia de resúmenes de tarjetas de crédito."""

import json
import os
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Engine, Float, String, Text, create_engine, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.tarjetas.entities import ResumenTarjeta, TransaccionTarjeta
from src.domain.tarjetas.ports import TarjetaRepositoryPort


class Base(DeclarativeBase):
    """Base declarativa para el modelo de persistencia de tarjetas."""


class ResumenTarjetaModel(Base):
    """Tabla relacional para resúmenes de tarjeta de crédito."""

    __tablename__ = "tarjeta_resumenes"

    id_resumen: Mapped[str] = mapped_column(String(64), primary_key=True)
    banco: Mapped[str] = mapped_column(String(50), nullable=False)
    tarjeta_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    tarjeta_categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    numero_cuenta: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_cierre: Mapped[date] = mapped_column(Date, index=True)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, index=True)
    saldo_pesos: Mapped[float] = mapped_column(Float, default=0.0)
    saldo_dolares: Mapped[float] = mapped_column(Float, default=0.0)
    pago_minimo: Mapped[float] = mapped_column(Float, default=0.0)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class SQLTarjetaGateway(TarjetaRepositoryPort):
    """Implementación SQLAlchemy del repositorio de tarjetas de crédito."""

    def __init__(
        self, database_url: str | None = None, logger: LoggerPort | None = None
    ) -> None:
        self.database_url = database_url or os.environ.get(
            "DATABASE_URL", "sqlite:///data/leads.db"
        )
        self._logger = logger or NullLogger()
        if ":memory:" in self.database_url:
            self._engine: Engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self._engine: Engine = create_engine(self.database_url, pool_pre_ping=True)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def _get_session(self) -> Session:
        return self._session_factory()

    def guardar(self, resumen: ResumenTarjeta) -> None:
        """Persiste un resumen de tarjeta junto a sus consumos en JSON."""
        model = ResumenTarjetaModel(
            id_resumen=resumen.id_resumen,
            banco=resumen.banco,
            tarjeta_tipo=resumen.tarjeta_tipo,
            tarjeta_categoria=resumen.tarjeta_categoria,
            numero_cuenta=resumen.numero_cuenta,
            fecha_cierre=resumen.fecha_cierre,
            fecha_vencimiento=resumen.fecha_vencimiento,
            saldo_pesos=resumen.saldo_pesos,
            saldo_dolares=resumen.saldo_dolares,
            pago_minimo=resumen.pago_minimo,
            creado_en=datetime.now(timezone.utc),
            payload_json=self._serializar_consumos(resumen.consumos),
        )
        with self._get_session() as session:
            session.merge(model)
            session.commit()

    def obtener_por_id(self, id_resumen: str) -> ResumenTarjeta | None:
        """Recupera un resumen por su identificador."""
        with self._get_session() as session:
            stmt = select(ResumenTarjetaModel).where(
                ResumenTarjetaModel.id_resumen == id_resumen
            )
            model = session.scalars(stmt).first()
            if not model:
                return None
            return self._model_to_entity(model)

    def obtener_resumenes_vencimiento_cercano(
        self, fecha_limite: date
    ) -> list[ResumenTarjeta]:
        """Lista resúmenes cuyo vencimiento es igual o posterior a la fecha límite."""
        with self._get_session() as session:
            stmt = (
                select(ResumenTarjetaModel)
                .where(ResumenTarjetaModel.fecha_vencimiento >= fecha_limite)
                .order_by(ResumenTarjetaModel.fecha_vencimiento.asc())
            )
            models = session.scalars(stmt).all()
            return [self._model_to_entity(model) for model in models]

    def _model_to_entity(self, model: ResumenTarjetaModel) -> ResumenTarjeta:
        return ResumenTarjeta(
            id_resumen=model.id_resumen,
            banco=model.banco,
            tarjeta_tipo=model.tarjeta_tipo,
            tarjeta_categoria=model.tarjeta_categoria,
            numero_cuenta=model.numero_cuenta,
            fecha_cierre=model.fecha_cierre,
            fecha_vencimiento=model.fecha_vencimiento,
            saldo_pesos=model.saldo_pesos,
            saldo_dolares=model.saldo_dolares,
            pago_minimo=model.pago_minimo,
            consumos=self._deserializar_consumos(model.payload_json),
        )

    @staticmethod
    def _serializar_consumos(consumos: tuple[TransaccionTarjeta, ...]) -> str:
        data = [
            {
                "fecha": c.fecha.isoformat(),
                "descripcion": c.descripcion,
                "monto_pesos": c.monto_pesos,
                "monto_dolares": c.monto_dolares,
                "nro_cupon": c.nro_cupon,
            }
            for c in consumos
        ]
        return json.dumps({"consumos": data})

    @staticmethod
    def _deserializar_consumos(payload_json: str) -> tuple[TransaccionTarjeta, ...]:
        try:
            data = json.loads(payload_json)
            items = data.get("consumos", [])
            return tuple(
                TransaccionTarjeta(
                    fecha=date.fromisoformat(item["fecha"]),
                    descripcion=item["descripcion"],
                    monto_pesos=item["monto_pesos"],
                    monto_dolares=item["monto_dolares"],
                    nro_cupon=item.get("nro_cupon", ""),
                )
                for item in items
            )
        except (json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError):
            return ()
