"""Tests unitarios para el dominio de horarios_docencia (compatibilidad, superposiciones y traslados)."""

import pytest

from src.domain.horarios_docencia.entities import (
    CargoDocente,
    DeclaracionHorariaDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.exceptions import (
    FranjaHorariaInvalidaException,
)
from src.domain.horarios_docencia.services import ValidadorHorariosDocenciaService
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    NivelSeveridad,
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


def test_declaracion_compatible_sin_conflictos() -> None:
    """Verifica una declaración horaria 100% compatible sin superposiciones ni traslados riesgosos."""
    cargo1 = CargoDocente(
        id_cargo="C-01",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Electrotecnia 4to",
        revista=SituacionRevista.TITULAR,
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
    cargo2 = CargoDocente(
        id_cargo="C-02",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Instalaciones 5to",
        revista=SituacionRevista.PROVISIONAL,
        modulos=4,
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
        cargos=(cargo1, cargo2),
    )

    validador = ValidadorHorariosDocenciaService()
    resultado = validador.validar(declaracion)

    assert resultado.es_compatible is True
    assert resultado.cantidad_conflictos == 0
    assert resultado.total_modulos == 8
    assert resultado.total_cargos == 2
    assert len(resultado.grilla_semanal["LUNES"]) == 2


def test_declaracion_con_superposicion_critica() -> None:
    """Verifica que una superposición horaria marca el resultado como incompatible."""
    cargo1 = CargoDocente(
        id_cargo="C-01",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Electrotecnia 4to",
        revista=SituacionRevista.TITULAR,
        modulos=4,
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
        modulos=4,
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


def test_declaracion_con_traslado_insuficiente_y_topes_estatutarios() -> None:
    """Verifica advertencias de traslado insuficiente y exceso de 30 módulos."""
    cargo1 = CargoDocente(
        id_cargo="C-01",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Materia A",
        revista=SituacionRevista.TITULAR,
        modulos=18,
        es_cargo_base=True,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.MIERCOLES,
                franja=FranjaHoraria(hora_inicio="07:30", hora_fin="11:30"),
                turno=Turno.MANANA,
            ),
        ),
    )
    cargo2 = CargoDocente(
        id_cargo="C-02",
        establecimiento="EEST N° 2 Garín",
        distrito="Escobar",
        cargo_asignatura="Materia B",
        revista=SituacionRevista.TITULAR,
        modulos=18,
        es_cargo_base=True,
        horarios=(
            HorarioBloque(
                dia=DiaSemana.MIERCOLES,
                franja=FranjaHoraria(
                    hora_inicio="11:40", hora_fin="15:40"
                ),  # Solo 10 min entre escuelas distintas
                turno=Turno.TARDE,
            ),
        ),
    )
    cargo3 = CargoDocente(
        id_cargo="C-03",
        establecimiento="EEST N° 3",
        distrito="San Martín",
        cargo_asignatura="Materia C",
        revista=SituacionRevista.PROVISIONAL,
        modulos=2,
        es_cargo_base=True,  # 3 cargos de base en total (supera tope de 2)
        horarios=(),
    )

    declaracion = DeclaracionHorariaDocente(
        docente_nombre="Docente Sobrecargado",
        cargos=(cargo1, cargo2, cargo3),
    )

    validador = ValidadorHorariosDocenciaService()
    resultado = validador.validar(
        declaracion,
        margen_traslado_minutos=20,
        tope_modulos_semanales=30,
        tope_cargos_base=2,
    )

    # Es compatible porque no hay superposición física estricta, pero tiene advertencias
    assert resultado.es_compatible is True
    assert resultado.total_modulos == 38
    assert resultado.total_cargos_base == 3

    tipos_conflictos = [c.tipo for c in resultado.conflictos]
    assert TipoConflicto.TRASLADO_INSUFICIENTE in tipos_conflictos
    assert TipoConflicto.EXCESO_MODULOS_SEMANALES in tipos_conflictos
    assert TipoConflicto.EXCESO_CARGOS_BASE in tipos_conflictos
