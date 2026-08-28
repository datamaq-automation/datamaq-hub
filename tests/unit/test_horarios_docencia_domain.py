"""Tests unitarios para el dominio de horarios_docencia (compatibilidad, vigencias temporales y periodos)."""

from datetime import date

import pytest

from src.domain.horarios_docencia.entities import (
    CargoDocente,
    DeclaracionHorariaDocente,
    DesignacionDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.exceptions import (
    FranjaHorariaInvalidaException,
    HorarioDocenciaInvalidoException,
)
from src.domain.horarios_docencia.services import ValidadorHorariosDocenciaService
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    NivelSeveridad,
    PeriodoVigencia,
    SituacionRevista,
    TipoConflicto,
    Turno,
)


def test_franja_horaria_validation_and_calculations() -> None:
    """Verifica el cálculo de minutos, duración y validaciones de formato de FranjaHoraria."""
    franja = FranjaHoraria(hora_inicio="07:30", hora_fin="09:30")
    assert franja.inicio_minutos() == 450
    assert franja.fin_minutos() == 570
    assert franja.duracion_minutos() == 120

    # Error de formato
    with pytest.raises(FranjaHorariaInvalidaException):
        FranjaHoraria(hora_inicio="7:30", hora_fin="09:30")

    # Error si inicio >= fin
    with pytest.raises(FranjaHorariaInvalidaException):
        FranjaHoraria(hora_inicio="12:00", hora_fin="10:00")

    with pytest.raises(FranjaHorariaInvalidaException):
        FranjaHoraria(hora_inicio="08:00", hora_fin="08:00")


def test_franja_horaria_overlap_and_distance() -> None:
    """Verifica detección de solapamiento y cálculo de distancia entre franjas."""
    f1 = FranjaHoraria(hora_inicio="07:30", hora_fin="09:30")
    f2 = FranjaHoraria(hora_inicio="09:00", hora_fin="11:00")  # Solapamiento 30 min
    f3 = FranjaHoraria(
        hora_inicio="09:30", hora_fin="11:30"
    )  # Consecutivo exacto (0 min traslado)
    f4 = FranjaHoraria(hora_inicio="10:00", hora_fin="12:00")  # Distancia 30 min

    assert f1.se_superpone_con(f2) is True
    assert f1.minutos_solapamiento(f2) == 30

    assert f1.se_superpone_con(f3) is False
    assert f1.minutos_hasta(f3) == 0

    assert f1.se_superpone_con(f4) is False
    assert f1.minutos_hasta(f4) == 30


def test_periodo_vigencia_logic() -> None:
    """Verifica la lógica temporal del Value Object PeriodoVigencia."""
    v_activa = PeriodoVigencia(fecha_desde=date(2026, 3, 1), fecha_hasta=None)
    assert v_activa.esta_vigente_en(date(2026, 2, 28)) is False
    assert v_activa.esta_vigente_en(date(2026, 3, 1)) is True
    assert v_activa.esta_vigente_en(date(2026, 8, 27)) is True
    assert v_activa.duracion_dias() is None

    v_cerrada = PeriodoVigencia(
        fecha_desde=date(2026, 3, 1), fecha_hasta=date(2026, 6, 30)
    )
    assert v_cerrada.esta_vigente_en(date(2026, 4, 15)) is True
    assert v_cerrada.esta_vigente_en(date(2026, 7, 1)) is False
    assert v_cerrada.duracion_dias() == 122

    # Error si fecha_desde > fecha_hasta
    with pytest.raises(HorarioDocenciaInvalidoException):
        PeriodoVigencia(fecha_desde=date(2026, 8, 1), fecha_hasta=date(2026, 7, 1))


def test_designacion_docente_conversion() -> None:
    """Verifica que DesignacionDocente se convierta correctamente a CargoDocente para auditoría."""
    designacion = DesignacionDocente(
        id_designacion="DESIG-001",
        docente_cuit="20-36528392-4",
        ige="IGE-78901",
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

    cargo = designacion.to_cargo_docente()
    assert cargo.id_cargo == "DESIG-001"
    assert cargo.ige == "IGE-78901"
    assert cargo.establecimiento == "EEST N° 1 Pilar"
    assert len(cargo.horarios) == 1


def test_declaracion_compatible_sin_conflictos() -> None:
    """Verifica una declaración horaria 100% compatible sin superposiciones ni traslados riesgosos."""
    cargo1 = CargoDocente(
        id_cargo="C-01",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Electrotecnia 4to",
        revista=SituacionRevista.TITULAR,
        ige="IGE-1234",
        modulos=2,
        es_cargo_base=False,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.LUNES,
                franja=FranjaHoraria(hora_inicio="07:30", hora_fin="09:30"),
                turno=Turno.MANANA,
            ),
        ),
    )
    cargo2 = CargoDocente(
        id_cargo="C-02",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Instalaciones 5to",
        revista=SituacionRevista.PROVISIONAL,
        ige="IGE-5678",
        modulos=2,
        es_cargo_base=False,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.LUNES,
                franja=FranjaHoraria(hora_inicio="09:45", hora_fin="11:45"),
                turno=Turno.MANANA,
            ),
        ),
    )

    declaracion = DeclaracionHorariaDocente(
        docente_nombre="Agustín Deoz",
        cuit="20-36528392-4",
        cargos=(cargo1, cargo2),
    )

    validador = ValidadorHorariosDocenciaService()
    resultado = validador.validar(declaracion)

    assert resultado.es_compatible is True
    assert resultado.cantidad_conflictos == 0
    assert resultado.cantidad_incompatibilidades == 0
    assert resultado.cantidad_advertencias == 0
    assert resultado.tiene_advertencias is False
    assert resultado.total_modulos == 4
    assert resultado.total_cargos == 2
    assert len(resultado.grilla_semanal["LUNES"]) == 2
    assert resultado.grilla_semanal["LUNES"][0].ige == "IGE-1234"


def test_declaracion_con_superposicion_critica() -> None:
    """Verifica que una superposición horaria marca el resultado como incompatible."""
    cargo1 = CargoDocente(
        id_cargo="C-01",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Electrotecnia 4to",
        revista=SituacionRevista.TITULAR,
        modulos=2,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.MARTES,
                franja=FranjaHoraria(hora_inicio="08:00", hora_fin="10:00"),
                turno=Turno.MANANA,
            ),
        ),
    )
    cargo2 = CargoDocente(
        id_cargo="C-02",
        establecimiento="ISFT N° 199 Tigre",
        distrito="Tigre",
        cargo_asignatura="Automatización",
        revista=SituacionRevista.PROVISIONAL,
        modulos=2,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.MARTES,
                franja=FranjaHoraria(hora_inicio="09:30", hora_fin="11:30"),
                turno=Turno.MANANA,
            ),
        ),
    )

    declaracion = DeclaracionHorariaDocente(
        docente_nombre="Docente Test",
        cargos=(cargo1, cargo2),
    )

    validador = ValidadorHorariosDocenciaService()
    resultado = validador.validar(declaracion)

    assert resultado.es_compatible is False
    assert resultado.cantidad_conflictos >= 1

    conflicto = resultado.conflictos[0]
    assert conflicto.tipo == TipoConflicto.SUPERPOSICION_HORARIA
    assert conflicto.severidad == NivelSeveridad.CRITICO
    assert conflicto.dia == DiaSemana.MARTES
    assert conflicto.minutos_solapamiento_o_traslado == 30
