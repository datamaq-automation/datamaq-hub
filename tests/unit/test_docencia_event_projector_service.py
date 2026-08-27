"""Unit tests for DocenciaEventProjectorService."""

from datetime import date

from src.domain.calendar.services import DocenciaEventProjectorService
from src.domain.horarios_docencia.entities import (
    DesignacionDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    PeriodoVigencia,
    SituacionRevista,
    Turno,
)


def test_docencia_event_projector_generates_correct_instances():
    # Designacion active from 2026-09-01
    desig = DesignacionDocente(
        id_designacion="desig-001",
        docente_cuit="20365283921",
        establecimiento="EEST N°1",
        distrito="San Martín",
        cargo_asignatura="Sistemas Embebidos",
        revista=SituacionRevista.TITULAR,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 3, 1), fecha_hasta=None),
        ige="12345",
        modulos=4,
        es_cargo_base=False,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.LUNES,
                franja=FranjaHoraria("08:00", "10:00"),
                turno=Turno.MANANA,
            ),
            HorarioBloque(
                dia=DiaSemana.MIERCOLES,
                franja=FranjaHoraria("14:00", "16:00"),
                turno=Turno.TARDE,
            ),
        ),
    )

    # Date range: 2026-09-01 (Tuesday) to 2026-09-14 (Monday) -> 2 weeks
    # Week 1:
    # 2026-09-01 (Tue) -> No
    # 2026-09-02 (Wed) -> Yes (14:00 - 16:00)
    # 2026-09-07 (Mon) -> Yes (08:00 - 10:00)
    # 2026-09-09 (Wed) -> Yes (14:00 - 16:00)
    # 2026-09-14 (Mon) -> Yes (08:00 - 10:00)
    # Total = 4 events

    events = DocenciaEventProjectorService.project_events(
        designaciones=[desig],
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 9, 14),
        calendar_id="1",
        account="agustin@datamaq.com.ar",
    )

    assert len(events) == 4
    assert all(e.categorias == "Docencia" for e in events)
    assert all(e.ubicacion == "EEST N°1, San Martín" for e in events)
    assert all("Sistemas Embebidos" in e.titulo for e in events)
    assert events[0].inicio.date() == date(2026, 9, 2)
    assert events[0].inicio.hour == 14
    assert events[0].fin.hour == 16


def test_docencia_event_projector_respects_vigencia_limits():
    # Expired designacion before range
    desig_past = DesignacionDocente(
        id_designacion="desig-past",
        docente_cuit="20365283921",
        establecimiento="Escuela Vieja",
        distrito="Quilmes",
        cargo_asignatura="Física",
        revista=SituacionRevista.SUPLENTE,
        vigencia=PeriodoVigencia(
            fecha_desde=date(2026, 3, 1), fecha_hasta=date(2026, 6, 30)
        ),
        horarios=(
            HorarioBloque(
                dia=DiaSemana.LUNES,
                franja=FranjaHoraria("08:00", "10:00"),
                turno=Turno.MANANA,
            ),
        ),
    )

    events = DocenciaEventProjectorService.project_events(
        designaciones=[desig_past],
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 9, 30),
    )
    assert len(events) == 0
