"""Tests unitarios para SQLDesignacionDocenteGateway (persistencia inmutable / temporal)."""

from datetime import date

import pytest

from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.domain.horarios_docencia.entities import (
    DesignacionDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    MotivoCese,
    PeriodoVigencia,
    SituacionRevista,
    Turno,
)


@pytest.fixture
def gateway() -> SQLDesignacionDocenteGateway:
    """Fixture de gateway en memoria para tests aislados."""
    return SQLDesignacionDocenteGateway(database_url="sqlite:///:memory:")


def test_guardar_y_obtener_por_id(gateway: SQLDesignacionDocenteGateway) -> None:
    """Verifica la persistencia de una designación y sus bloques horarios."""
    designacion = DesignacionDocente(
        id_designacion="DESIG-001",
        docente_cuit="20-36528392-4",
        ige="IGE-99881",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Electrotecnia 4to",
        revista=SituacionRevista.TITULAR,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1)),
        modulos=4,
        es_cargo_base=False,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.LUNES,
                franja=FranjaHoraria(hora_inicio="07:30", hora_fin="09:30"),
                turno=Turno.MANANA,
            ),
        ),
    )

    guardada = gateway.guardar(designacion)
    assert guardada.id_designacion == "DESIG-001"
    assert guardada.ige == "IGE-99881"
    assert len(guardada.horarios) == 1

    recuperada = gateway.obtener_por_id("DESIG-001")
    assert recuperada is not None
    assert recuperada.docente_cuit == "20-36528392-4"
    assert recuperada.establecimiento == "EEST N° 1 Pilar"
    assert recuperada.horarios[0].franja.hora_inicio == "07:30"


def test_consultar_vigentes_en_fecha_y_cerrar_vigencia(
    gateway: SQLDesignacionDocenteGateway,
) -> None:
    """Verifica time-travel queries: consulta en fechas activas vs fechas posteriores al cese."""
    # 1. Cargo Titular (desde 2026-03-01 en adelante)
    d_titular = DesignacionDocente(
        id_designacion="TITULAR-01",
        docente_cuit="20-36528392-4",
        ige="IGE-TIT-01",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Electrotecnia",
        revista=SituacionRevista.TITULAR,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1)),
        modulos=4,
    )
    gateway.guardar(d_titular)

    # 2. Suplencia (desde 2026-04-01 hasta 2026-06-30)
    d_suplente = DesignacionDocente(
        id_designacion="SUPLENTE-01",
        docente_cuit="20-36528392-4",
        ige="IGE-SUP-01",
        establecimiento="ISFT N° 199 Tigre",
        distrito="Tigre",
        cargo_asignatura="Automatización",
        revista=SituacionRevista.SUPLENTE,
        vigencia=PeriodoVigencia(
            fecha_desde=date(2026, 4, 1),
            fecha_hasta=date(2026, 6, 30),
        ),
        motivo_cese=MotivoCese.FIN_SUPLENCIA,
        modulos=4,
    )
    gateway.guardar(d_suplente)

    # Consulta el 2026-05-15 (ambos cargos activos)
    vigentes_mayo = gateway.obtener_vigentes_en_fecha(
        "20-36528392-4", date(2026, 5, 15)
    )
    assert len(vigentes_mayo) == 2

    # Consulta el 2026-07-15 (la suplencia ya cesó, solo queda el titular)
    vigentes_julio = gateway.obtener_vigentes_en_fecha(
        "20-36528392-4", date(2026, 7, 15)
    )
    assert len(vigentes_julio) == 1
    assert vigentes_julio[0].id_designacion == "TITULAR-01"

    # Consulta antes del inicio (2026-01-01 -> 0 cargos)
    vigentes_enero = gateway.obtener_vigentes_en_fecha(
        "20-36528392-4", date(2026, 1, 1)
    )
    assert len(vigentes_enero) == 0

    # 3. Cerrar vigencia del titular por renuncia
    cerrado = gateway.cerrar_vigencia(
        id_designacion="TITULAR-01",
        fecha_hasta=date(2026, 8, 31),
        motivo=MotivoCese.RENUNCIA,
    )
    assert cerrado is not None
    assert cerrado.vigencia.fecha_hasta == date(2026, 8, 31)
    assert cerrado.motivo_cese == MotivoCese.RENUNCIA

    # Historial completo (2 registros intactos sin deletes)
    historial = gateway.obtener_historial("20-36528392-4")
    assert len(historial) == 2
