"""Gateway relacional SQLAlchemy para persistencia de oportunidades laborales e interacciones.

Diseñado para operar de forma idéntica en MySQL (en VPS bajo la base busqueda_laboral)
y en SQLite (en entorno local y tests unitarios).
"""

import json
import os
from datetime import date, datetime, timezone
from typing import Any, cast

from sqlalchemy import (
    JSON,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from src.domain.empleo.entities import (
    InteraccionPostulacion,
    OportunidadLaboral,
)
from src.domain.empleo.ports import OportunidadesRepositoryPort
from src.domain.empleo.value_objects import EstadoOportunidad


class Base(DeclarativeBase):
    """Base declarativa para los modelos de búsqueda laboral."""


class OportunidadModel(Base):
    """Modelo relacional para la tabla 'oportunidades' (espejo exacto del esquema de MySQL VPS)."""

    __tablename__ = "oportunidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    empresa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultora: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ubicacion: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Neuquén"
    )
    regimen: Mapped[str | None] = mapped_column(String(100), nullable=True)
    jornada: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salario_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salario_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salario_moneda: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default="ARS"
    )
    salario_bruto_neto: Mapped[str | None] = mapped_column(String(50), nullable=True)
    url_fuente: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        default=EstadoOportunidad.DETECTADA.value,
    )
    fecha_publicacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_postulacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_entrevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_oferta: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_descarte: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_congelacion: Mapped[date | None] = mapped_column(Date, nullable=True)
    notas: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    requisitos: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    origen: Mapped[str] = mapped_column(String(50), nullable=False, default="MANUAL")
    tipo_modalidad: Mapped[str] = mapped_column(
        String(30), nullable=False, default="RELACION_DEPENDENCIA"
    )
    canal_adquisicion: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DIRECTO"
    )
    id_campania: Mapped[int | None] = mapped_column(Integer, nullable=True)

    interacciones: Mapped[list["InteraccionModel"]] = relationship(
        "InteraccionModel", back_populates="oportunidad", cascade="all, delete-orphan"
    )


class InteraccionModel(Base):
    """Modelo relacional para la tabla 'interacciones'."""

    __tablename__ = "interacciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    oportunidad_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oportunidades.id"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    canal: Mapped[str] = mapped_column(String(50), nullable=False, default="MAIL")
    contacto_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contacto_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contacto_telefono: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contacto_empresa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resumen: Mapped[str | None] = mapped_column(Text, nullable=True)
    proxima_accion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_proxima_accion: Mapped[date | None] = mapped_column(Date, nullable=True)

    oportunidad: Mapped["OportunidadModel"] = relationship(
        "OportunidadModel", back_populates="interacciones"
    )


def init_busqueda_laboral_db(database_url: str) -> None:
    """Crea las tablas en la base de datos (MySQL o SQLite) si aún no existen."""
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine, checkfirst=True)
    if database_url.startswith("sqlite") and ":memory:" not in database_url:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))


class SQLOportunidadesGateway(OportunidadesRepositoryPort):
    """Implementación de OportunidadesRepositoryPort utilizando SQLAlchemy."""

    def __init__(self, database_url: str | None = None) -> None:
        if database_url is None:
            database_url = os.getenv(
                "BUSQUEDA_LABORAL_DB_URL", "sqlite:///data/busqueda_laboral.db"
            )

        if database_url.startswith("sqlite") and ":memory:" in database_url:
            from sqlalchemy.pool import StaticPool

            self._engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self._engine = create_engine(database_url, pool_pre_ping=True)

        Base.metadata.create_all(self._engine, checkfirst=True)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    def guardar(self, oportunidad: OportunidadLaboral) -> OportunidadLaboral:
        """Inserta o actualiza una oportunidad en la base de datos."""
        with self._session_factory() as session:
            f_pub = (
                date.fromisoformat(oportunidad.fecha_publicacion)
                if oportunidad.fecha_publicacion
                else None
            )
            f_post = (
                date.fromisoformat(oportunidad.fecha_postulacion)
                if oportunidad.fecha_postulacion
                else None
            )
            f_ent = (
                date.fromisoformat(oportunidad.fecha_entrevista)
                if oportunidad.fecha_entrevista
                else None
            )
            f_ofr = (
                date.fromisoformat(oportunidad.fecha_oferta)
                if oportunidad.fecha_oferta
                else None
            )
            f_dsc = (
                date.fromisoformat(oportunidad.fecha_descarte)
                if oportunidad.fecha_descarte
                else None
            )
            f_cng = (
                date.fromisoformat(oportunidad.fecha_congelacion)
                if oportunidad.fecha_congelacion
                else None
            )

            model = (
                session.get(OportunidadModel, oportunidad.id)
                if oportunidad.id is not None
                else None
            )
            if model is None:
                model = OportunidadModel(
                    id=oportunidad.id,
                    titulo=oportunidad.titulo,
                    empresa=oportunidad.empresa,
                    consultora=oportunidad.consultora,
                    ubicacion=oportunidad.ubicacion or "Neuquén",
                    regimen=oportunidad.regimen,
                    jornada=oportunidad.jornada,
                    salario_min=oportunidad.salario_min,
                    salario_max=oportunidad.salario_max,
                    salario_moneda=oportunidad.salario_moneda,
                    salario_bruto_neto=oportunidad.salario_bruto_neto,
                    url_fuente=oportunidad.url_fuente,
                    estado=oportunidad.estado.value,
                    fecha_publicacion=f_pub,
                    fecha_postulacion=f_post,
                    fecha_entrevista=f_ent,
                    fecha_oferta=f_ofr,
                    fecha_descarte=f_dsc,
                    fecha_congelacion=f_cng,
                    notas=oportunidad.notas,
                    requisitos=list(oportunidad.requisitos),
                    origen=oportunidad.origen,
                    tipo_modalidad=oportunidad.tipo_modalidad,
                    canal_adquisicion=oportunidad.canal_adquisicion,
                    id_campania=oportunidad.id_campania,
                )
                session.add(model)
                session.commit()
                return self._model_a_entidad(model)
            else:
                model.titulo = oportunidad.titulo
                model.empresa = oportunidad.empresa
                model.consultora = oportunidad.consultora
                model.ubicacion = oportunidad.ubicacion
                model.regimen = oportunidad.regimen
                model.jornada = oportunidad.jornada
                model.salario_min = oportunidad.salario_min
                model.salario_max = oportunidad.salario_max
                model.salario_moneda = oportunidad.salario_moneda
                model.salario_bruto_neto = oportunidad.salario_bruto_neto
                model.url_fuente = oportunidad.url_fuente
                model.estado = oportunidad.estado.value
                model.fecha_publicacion = f_pub
                model.fecha_postulacion = f_post
                model.fecha_entrevista = f_ent
                model.fecha_oferta = f_ofr
                model.fecha_descarte = f_dsc
                model.fecha_congelacion = f_cng
                model.notas = oportunidad.notas
                model.requisitos = list(oportunidad.requisitos)
                session.commit()
                return self._model_a_entidad(model)

    def obtener_por_id(self, id_oportunidad: int) -> OportunidadLaboral | None:
        """Obtiene una oportunidad por ID."""
        with self._session_factory() as session:
            model = session.get(OportunidadModel, id_oportunidad)
            return self._model_a_entidad(model) if model else None

    def listar(
        self,
        estado: EstadoOportunidad | None = None,
        empresa: str | None = None,
    ) -> list[OportunidadLaboral]:
        """Lista oportunidades aplicando filtros opcionales."""
        with self._session_factory() as session:
            stmt = select(OportunidadModel)
            if estado:
                stmt = stmt.where(OportunidadModel.estado == estado.value)
            if empresa:
                stmt = stmt.where(OportunidadModel.empresa.ilike(f"%{empresa}%"))
            stmt = stmt.order_by(OportunidadModel.id.desc())
            results = session.scalars(stmt).all()
            return [self._model_a_entidad(m) for m in results]

    def actualizar_estado(
        self,
        id_oportunidad: int,
        nuevo_estado: EstadoOportunidad,
        notas: str | None = None,
    ) -> OportunidadLaboral:
        """Actualiza el estado y opcionalmente las notas de una oportunidad."""
        with self._session_factory() as session:
            model = session.get(OportunidadModel, id_oportunidad)
            if not model:
                raise ValueError(f"Oportunidad con ID {id_oportunidad} no encontrada")
            model.estado = nuevo_estado.value
            today = datetime.now(timezone.utc).date()
            if (
                nuevo_estado == EstadoOportunidad.POSTULADA
                and not model.fecha_postulacion
            ):
                model.fecha_postulacion = today
            elif (
                nuevo_estado == EstadoOportunidad.ENTREVISTA
                and not model.fecha_entrevista
            ):
                model.fecha_entrevista = today
            elif nuevo_estado == EstadoOportunidad.OFERTA and not model.fecha_oferta:
                model.fecha_oferta = today
            elif (
                nuevo_estado == EstadoOportunidad.DESCARTADA
                and not model.fecha_descarte
            ):
                model.fecha_descarte = today
            elif (
                nuevo_estado == EstadoOportunidad.CONGELADA
                and not model.fecha_congelacion
            ):
                model.fecha_congelacion = today

            if notas is not None:
                model.notas = notas
            session.commit()
            return self._model_a_entidad(model)

    def eliminar(self, id_oportunidad: int) -> bool:
        """Elimina la oportunidad por ID."""
        with self._session_factory() as session:
            model = session.get(OportunidadModel, id_oportunidad)
            if not model:
                return False
            session.delete(model)
            session.commit()
            return True

    def registrar_interaccion(
        self,
        interaccion: InteraccionPostulacion,
    ) -> InteraccionPostulacion:
        """Registra una interacción de seguimiento."""
        with self._session_factory() as session:
            f_inter = (
                date.fromisoformat(interaccion.fecha)
                if interaccion.fecha
                else datetime.now(timezone.utc).date()
            )

            f_prox = (
                date.fromisoformat(interaccion.fecha_proxima_accion)
                if interaccion.fecha_proxima_accion
                else None
            )

            model = InteraccionModel(
                id=interaccion.id,
                oportunidad_id=interaccion.oportunidad_id,
                fecha=f_inter,
                canal=interaccion.canal,
                contacto_nombre=interaccion.contacto_nombre,
                contacto_email=interaccion.contacto_email,
                contacto_telefono=interaccion.contacto_telefono,
                contacto_empresa=interaccion.contacto_empresa,
                resumen=interaccion.resumen,
                proxima_accion=interaccion.proxima_accion,
                fecha_proxima_accion=f_prox,
            )
            session.add(model)
            session.commit()
            return self._interaccion_model_a_entidad(model)

    def listar_interacciones(
        self,
        oportunidad_id: int,
    ) -> list[InteraccionPostulacion]:
        """Lista todas las interacciones asociadas a una oportunidad."""
        with self._session_factory() as session:
            stmt = (
                select(InteraccionModel)
                .where(InteraccionModel.oportunidad_id == oportunidad_id)
                .order_by(InteraccionModel.fecha.desc(), InteraccionModel.id.desc())
            )
            results = session.scalars(stmt).all()
            return [self._interaccion_model_a_entidad(m) for m in results]

    @staticmethod
    def _model_a_entidad(model: OportunidadModel) -> OportunidadLaboral:
        reqs = model.requisitos
        reqs_tuple: tuple[str, ...]
        if isinstance(reqs, str):
            try:
                parsed = json.loads(reqs)
                if isinstance(parsed, list):
                    parsed_list = cast(list[object], parsed)
                    reqs_tuple = tuple(str(x) for x in parsed_list)
                else:
                    reqs_tuple = (reqs,)
            except (json.JSONDecodeError, TypeError, ValueError):
                reqs_tuple = (reqs,)
        elif isinstance(reqs, list):
            reqs_list = cast(list[object], reqs)
            reqs_tuple = tuple(str(r) for r in reqs_list)
        else:
            reqs_tuple = ()

        try:
            estado_vo = EstadoOportunidad(model.estado)
        except ValueError:
            estado_vo = EstadoOportunidad.DETECTADA

        return OportunidadLaboral(
            id=model.id,
            titulo=model.titulo,
            empresa=model.empresa or "",
            consultora=model.consultora or "",
            ubicacion=model.ubicacion,
            regimen=model.regimen or "",
            jornada=model.jornada or "",
            salario_min=model.salario_min,
            salario_max=model.salario_max,
            salario_moneda=model.salario_moneda or "ARS",
            salario_bruto_neto=model.salario_bruto_neto or "",
            url_fuente=model.url_fuente or "",
            estado=estado_vo,
            fecha_publicacion=model.fecha_publicacion.isoformat()
            if model.fecha_publicacion
            else "",
            fecha_postulacion=model.fecha_postulacion.isoformat()
            if model.fecha_postulacion
            else "",
            fecha_entrevista=model.fecha_entrevista.isoformat()
            if model.fecha_entrevista
            else "",
            fecha_oferta=model.fecha_oferta.isoformat() if model.fecha_oferta else "",
            fecha_descarte=model.fecha_descarte.isoformat()
            if model.fecha_descarte
            else "",
            fecha_congelacion=model.fecha_congelacion.isoformat()
            if model.fecha_congelacion
            else "",
            notas=model.notas or "",
            requisitos=reqs_tuple,
            origen=model.origen,
            tipo_modalidad=model.tipo_modalidad,
            canal_adquisicion=model.canal_adquisicion,
            id_campania=model.id_campania,
        )

    @staticmethod
    def _interaccion_model_a_entidad(model: InteraccionModel) -> InteraccionPostulacion:
        return InteraccionPostulacion(
            id=model.id,
            oportunidad_id=model.oportunidad_id,
            fecha=model.fecha.isoformat() if model.fecha else "",
            canal=model.canal,
            contacto_nombre=model.contacto_nombre or "",
            contacto_email=model.contacto_email or "",
            contacto_telefono=model.contacto_telefono or "",
            contacto_empresa=model.contacto_empresa or "",
            resumen=model.resumen or "",
            proxima_accion=model.proxima_accion or "",
            fecha_proxima_accion=model.fecha_proxima_accion.isoformat()
            if model.fecha_proxima_accion
            else "",
        )
