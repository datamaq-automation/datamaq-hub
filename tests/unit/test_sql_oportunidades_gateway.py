"""Unit tests for SQLOportunidadesGateway with SQLite."""

from datetime import datetime, timezone

import pytest

from src.adapters.gateways.empleo.sql_oportunidades_gateway import (
    SQLOportunidadesGateway,
    init_busqueda_laboral_db,
)
from src.domain.empleo.entities import (
    InteraccionPostulacion,
    OportunidadLaboral,
)
from src.domain.empleo.value_objects import EstadoOportunidad


@pytest.fixture
def test_gateway() -> SQLOportunidadesGateway:
    # Base SQLite en memoria para tests unitarios
    db_url = "sqlite:///:memory:"
    init_busqueda_laboral_db(db_url)
    return SQLOportunidadesGateway(database_url=db_url)


def test_guardar_y_obtener_oportunidad(test_gateway: SQLOportunidadesGateway):
    hoy_str = str(datetime.now(timezone.utc).date())
    oportunidad = OportunidadLaboral(
        id=None,
        titulo="Supervisor de Mantenimiento de Campo",
        empresa="Tecpetrol (Grupo Techint)",
        ubicacion="Yacimiento Fortín de Piedra, Añelo",
        regimen="14x7",
        jornada="Rotativo con pernocte",
        salario_min=2500000.0,
        salario_max=3200000.0,
        salario_moneda="ARS",
        url_fuente="https://jobs.tecpetrol.com/job/1234",
        estado=EstadoOportunidad.POSTULADA,
        fecha_postulacion=hoy_str,
        notas="Postulación enviada a través de portal de carreras.",
        requisitos=("Experiencia en plantas compresoras", "VFD y celdas"),
    )

    guardada = test_gateway.guardar(oportunidad)
    assert guardada.id is not None
    assert guardada.empresa == "Tecpetrol (Grupo Techint)"
    assert guardada.estado == EstadoOportunidad.POSTULADA

    recuperada = test_gateway.obtener_por_id(guardada.id)
    assert recuperada is not None
    assert recuperada.titulo == oportunidad.titulo
    assert recuperada.ubicacion == "Yacimiento Fortín de Piedra, Añelo"
    assert "VFD y celdas" in recuperada.requisitos


def test_listar_y_filtrar_oportunidades(test_gateway: SQLOportunidadesGateway):
    op1 = OportunidadLaboral(
        id=None,
        titulo="Oficial Instrumentista",
        empresa="Fischer Instrumentación",
        ubicacion="Rincón de los Sauces",
        estado=EstadoOportunidad.DETECTADA,
    )
    op2 = OportunidadLaboral(
        id=None,
        titulo="Inspector Técnico",
        empresa="Trace Group",
        ubicacion="Tratayén, Añelo",
        estado=EstadoOportunidad.POSTULADA,
    )

    test_gateway.guardar(op1)
    test_gateway.guardar(op2)

    todas = test_gateway.listar()
    assert len(todas) == 2

    solo_postuladas = test_gateway.listar(estado=EstadoOportunidad.POSTULADA)
    assert len(solo_postuladas) == 1
    assert solo_postuladas[0].empresa == "Trace Group"


def test_actualizar_estado_oportunidad(test_gateway: SQLOportunidadesGateway):
    op = test_gateway.guardar(
        OportunidadLaboral(
            id=None,
            titulo="Especialista APM",
            empresa="YPF S.A.",
            ubicacion="Añelo",
            estado=EstadoOportunidad.DETECTADA,
        )
    )
    assert op.id is not None

    actualizada = test_gateway.actualizar_estado(
        id_oportunidad=op.id,
        nuevo_estado=EstadoOportunidad.ENTREVISTA,
        notas="Entrevista técnica agendada con el Gerente de Mantenimiento.",
    )
    assert actualizada.estado == EstadoOportunidad.ENTREVISTA
    assert "Entrevista técnica" in actualizada.notas


def test_registrar_y_listar_interacciones(test_gateway: SQLOportunidadesGateway):
    op = test_gateway.guardar(
        OportunidadLaboral(
            id=None,
            titulo="Ingeniero Eléctrico",
            empresa="ManpowerGroup",
            ubicacion="Añelo",
            estado=EstadoOportunidad.POSTULADA,
        )
    )
    assert op.id is not None

    interaccion = InteraccionPostulacion(
        id=None,
        oportunidad_id=op.id,
        fecha="2026-09-06",
        canal="LINKEDIN",
        contacto_nombre="Lic. Reclutamiento",
        contacto_empresa="ManpowerGroup",
        resumen="Contacto inicial por vacante en yacimiento.",
        proxima_accion="Enviar CV actualizado en PDF.",
        fecha_proxima_accion="2026-09-08",
    )

    guardada = test_gateway.registrar_interaccion(interaccion)
    assert guardada.id is not None

    interacciones = test_gateway.listar_interacciones(op.id)
    assert len(interacciones) == 1
    assert interacciones[0].contacto_nombre == "Lic. Reclutamiento"
    assert interacciones[0].proxima_accion == "Enviar CV actualizado en PDF."
