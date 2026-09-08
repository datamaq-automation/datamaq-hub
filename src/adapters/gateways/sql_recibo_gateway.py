"""Gateway relacional SQLAlchemy para persistencia y consulta de recibos de sueldo."""

import json
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Engine,
    Float,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.common.ports import LoggerPort, NullLogger
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    ConceptoItem,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.ports import ReciboRepositoryPort
from src.domain.recibos.value_objects import TipoRecibo


class Base(DeclarativeBase):
    """Base declarativa para el modelo de persistencia de recibos."""


class ReciboModel(Base):
    """Tabla relacional para almacenamiento de recibos de sueldo parseados."""

    __tablename__ = "recibos_sueldo"

    id_recibo: Mapped[str] = mapped_column(String(64), primary_key=True)
    docente_cuit: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    docente_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    mes_pago: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    tipo_recibo: Mapped[str] = mapped_column(String(50), nullable=False)
    organismo: Mapped[str] = mapped_column(String(200), nullable=False)
    total_haberes: Mapped[float] = mapped_column(Float, default=0.0)
    total_descuentos: Mapped[float] = mapped_column(Float, default=0.0)
    total_liquido: Mapped[float] = mapped_column(Float, default=0.0)
    pdf_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    estado_cierre: Mapped[str | None] = mapped_column(
        String(20), default="SIN_TOTAL", nullable=True
    )
    total_declarado: Mapped[float | None] = mapped_column(Float, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


def _migrate_recibos_schema(engine: Engine) -> None:
    """Aplica migraciones no destructivas a tablas existentes."""
    from sqlalchemy import inspect, text

    with engine.connect() as conn:
        inspector = inspect(engine)
        if "recibos_sueldo" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("recibos_sueldo")}
            if "pdf_hash" not in cols:
                conn.execute(
                    text("ALTER TABLE recibos_sueldo ADD COLUMN pdf_hash VARCHAR(64)")
                )
                conn.commit()
            if "estado_cierre" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE recibos_sueldo ADD COLUMN estado_cierre VARCHAR(20) DEFAULT 'SIN_TOTAL'"
                    )
                )
                conn.commit()
            if "total_declarado" not in cols:
                conn.execute(
                    text("ALTER TABLE recibos_sueldo ADD COLUMN total_declarado FLOAT")
                )
                conn.commit()


def init_recibos_db(database_url: str) -> Engine:
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    _migrate_recibos_schema(engine)
    return engine


from sqlalchemy.pool import StaticPool


class SQLReciboGateway(ReciboRepositoryPort):
    """Implementación SQLAlchemy del repositorio de recibos de sueldo."""

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
        _migrate_recibos_schema(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def _get_session(self) -> Session:
        return self._session_factory()

    def obtener_por_hash(self, pdf_hash: str) -> ReciboSueldo | None:
        """Recupera un recibo existente por el hash SHA-256 de su PDF."""
        if not pdf_hash:
            return None
        with self._get_session() as session:
            stmt = select(ReciboModel).where(ReciboModel.pdf_hash == pdf_hash)
            model = session.scalars(stmt).first()
            if not model:
                return None
            return self._model_to_entity(model)

    def guardar(self, recibo: ReciboSueldo) -> ReciboSueldo:
        """Persiste un recibo de sueldo asegurando un ID único e idempotencia por hash."""
        if recibo.pdf_hash:
            existente = self.obtener_por_hash(recibo.pdf_hash)
            if existente:
                existente.es_duplicado = True
                return existente

        if not recibo.id_recibo:
            recibo.id_recibo = str(uuid.uuid4())

        cuit_normalizado = recibo.agente.cuil.replace("-", "").strip()
        dto = ReceiptMapper.to_dto(recibo)
        payload_dict = dto.model_dump(mode="json")
        payload_str = json.dumps(payload_dict)

        model = ReciboModel(
            id_recibo=recibo.id_recibo,
            docente_cuit=cuit_normalizado,
            docente_nombre=recibo.agente.nombre_completo,
            numero_documento=recibo.agente.numero_documento,
            mes_pago=recibo.agente.mes_pago,
            tipo_recibo=recibo.tipo_recibo.value
            if hasattr(recibo.tipo_recibo, "value")
            else str(recibo.tipo_recibo),
            organismo=recibo.empleador.organismo_o_empresa,
            total_haberes=recibo.totales.total_haberes,
            total_descuentos=recibo.totales.total_descuentos,
            total_liquido=recibo.totales.total_liquido,
            pdf_hash=recibo.pdf_hash,
            estado_cierre=recibo.totales.estado_cierre,
            total_declarado=recibo.totales.total_declarado,
            creado_en=datetime.now(timezone.utc),
            payload_json=payload_str,
        )

        with self._get_session() as session:
            session.merge(model)
            session.commit()

        return recibo

    def obtener_por_id(self, id_recibo: str) -> ReciboSueldo | None:
        """Recupera un recibo por su ID y reconstruye la entidad de dominio."""
        with self._get_session() as session:
            stmt = select(ReciboModel).where(ReciboModel.id_recibo == id_recibo)
            model = session.scalars(stmt).first()
            if not model:
                return None
            return self._model_to_entity(model)

    def listar(
        self,
        cuit: str | None = None,
        mes_pago: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReciboSueldo]:
        """Lista recibos con filtros opcionales por CUIT y mes de pago."""
        with self._get_session() as session:
            stmt = select(ReciboModel)
            if cuit:
                cuit_norm = cuit.replace("-", "").strip()
                stmt = stmt.where(ReciboModel.docente_cuit == cuit_norm)
            if mes_pago:
                stmt = stmt.where(ReciboModel.mes_pago.contains(mes_pago))

            stmt = (
                stmt.order_by(ReciboModel.creado_en.desc()).offset(offset).limit(limit)
            )
            models = session.scalars(stmt).all()
            return [self._model_to_entity(m) for m in models]

    def eliminar(self, id_recibo: str) -> bool:
        """Elimina un recibo por ID."""
        with self._get_session() as session:
            stmt = select(ReciboModel).where(ReciboModel.id_recibo == id_recibo)
            model = session.scalars(stmt).first()
            if not model:
                return False
            session.delete(model)
            session.commit()
            return True

    def _model_to_entity(self, model: ReciboModel) -> ReciboSueldo:
        try:
            data = json.loads(model.payload_json)
            dto = ReceiptResponseDTO.model_validate(data)
            return self._dto_to_domain(dto, id_recibo=model.id_recibo)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            self._logger.error(f"Error deserializando recibo {model.id_recibo}: {e}")
            # Fallback construyendo entidad básica
            return ReciboSueldo(
                id_recibo=model.id_recibo,
                tipo_recibo=TipoRecibo.DGCYE_PBA
                if "DGCYE" in model.tipo_recibo
                else TipoRecibo.GENERICO,
                empleador=Empleador(organismo_o_empresa=model.organismo),
                agente=Agente(
                    nombre_completo=model.docente_nombre,
                    numero_documento=model.numero_documento,
                    cuil=model.docente_cuit,
                    mes_pago=model.mes_pago,
                ),
                totales=TotalesConsolidados(
                    total_haberes=model.total_haberes,
                    total_descuentos=model.total_descuentos,
                    total_liquido=model.total_liquido,
                    total_declarado=model.total_declarado,
                    estado_cierre=model.estado_cierre or "SIN_TOTAL",
                ),
                pdf_hash=model.pdf_hash,
            )

    @staticmethod
    def _dto_to_domain(dto: ReceiptResponseDTO, id_recibo: str) -> ReciboSueldo:
        return ReciboSueldo(
            id_recibo=id_recibo,
            tipo_recibo=dto.tipo_recibo,
            empleador=Empleador(
                organismo_o_empresa=dto.empleador.organismo_o_empresa,
                dependencia=dto.empleador.dependencia,
                cuit=dto.empleador.cuit,
            ),
            agente=Agente(
                nombre_completo=dto.agente.nombre_completo,
                tipo_documento=dto.agente.tipo_documento,
                numero_documento=dto.agente.numero_documento,
                sexo=dto.agente.sexo,
                cuil=dto.agente.cuil,
                mes_pago=dto.agente.mes_pago,
            ),
            resumen_liquidos=[
                ResumenLiquidoItem(
                    establecimiento_codigo=item.establecimiento_codigo,
                    secuencia=item.secuencia,
                    periodo_liquidado=item.periodo_liquidado,
                    fecha_pago=item.fecha_pago,
                    orden_pago_codigo=item.orden_pago_codigo,
                    orden_pago_descripcion=item.orden_pago_descripcion,
                    liquido_pesos=item.liquido_pesos,
                    distrito=item.distrito,
                    tipo_nivel=item.tipo_nivel,
                    escuela=item.escuela,
                    revista=item.revista,
                    orden_pago=item.orden_pago,
                    importe=item.importe
                    if item.importe is not None
                    else item.liquido_pesos,
                    concepto_normalizado=item.concepto_normalizado,
                )
                for item in dto.resumen_liquidos
            ],
            liquidaciones=[
                LiquidacionSecuencia(
                    establecimiento=EstablecimientoDetalle(
                        codigo=liq.establecimiento.codigo,
                        distrito=liq.establecimiento.distrito,
                        categoria=liq.establecimiento.categoria,
                        desfavorabilidad=liq.establecimiento.desfavorabilidad,
                        secciones=liq.establecimiento.secciones,
                        es_carcel=liq.establecimiento.es_carcel,
                        doble_escolaridad=liq.establecimiento.doble_escolaridad,
                        turnos=liq.establecimiento.turnos,
                        nombre=liq.establecimiento.nombre,
                    ),
                    cargo=CargoDetalle(
                        secuencia=liq.cargo.secuencia,
                        situacion_revista=liq.cargo.situacion_revista,
                        cargo_real=liq.cargo.cargo_real,
                        carga_horaria=liq.cargo.carga_horaria,
                        antiguedad_anios=liq.cargo.antiguedad_anios,
                        dias_trabajados=liq.cargo.dias_trabajados,
                        inasistencias=liq.cargo.inasistencias,
                        periodo_liquidado=liq.cargo.periodo_liquidado,
                        orden_pago=liq.cargo.orden_pago,
                    ),
                    conceptos=[
                        ConceptoItem(
                            codigo=c.codigo,
                            descripcion=c.descripcion,
                            haberes=c.haberes,
                            descuentos=c.descuentos,
                            tipo=c.tipo,
                        )
                        for c in liq.conceptos
                    ],
                    subtotal_haberes=liq.subtotal_haberes,
                    subtotal_descuentos=liq.subtotal_descuentos,
                    liquido_calculado=liq.liquido_calculado,
                )
                for liq in dto.liquidaciones
            ],
            totales=TotalesConsolidados(
                total_haberes_remunerativos=dto.totales.total_haberes_remunerativos,
                total_haberes_no_remunerativos=dto.totales.total_haberes_no_remunerativos,
                total_haberes=dto.totales.total_haberes,
                total_descuentos=dto.totales.total_descuentos,
                total_liquido=dto.totales.total_liquido,
                total_declarado=dto.totales.total_declarado,
                diferencia_cierre=dto.totales.diferencia_cierre,
                estado_cierre=dto.totales.estado_cierre,
            ),
            pdf_hash=getattr(dto, "pdf_hash", None),
            es_duplicado=getattr(dto, "es_duplicado", False),
            metadata=dict(dto.metadata),
        )
