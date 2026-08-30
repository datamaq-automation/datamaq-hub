"""Pruebas unitarias para el mapper de proyección salarial por CUIT."""

from datetime import date

from src.application.mappers.proyeccion_sueldo_mapper import (
    ProyeccionSueldoMapper,
    calcular_dias_trabajados,
    inferir_nivel_cargo,
    mapear_revista,
)
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.value_objects import (
    PeriodoVigencia,
)
from src.domain.horarios_docencia.value_objects import (
    SituacionRevista as RevistaHoraria,
)
from src.domain.liquidacion.value_objects import NivelCargo, SituacionRevista


def test_calcular_dias_trabajados_alta_mid_mes():
    """PSC-2: alta el 2026-08-13 -> 18 días proporcionales."""
    assert calcular_dias_trabajados(date(2026, 8, 13), None, 2026, 8) == 18.0


def test_calcular_dias_trabajados_baja_mid_mes():
    """PSC-3: baja el 2026-08-10 -> 10 días proporcionales."""
    assert (
        calcular_dias_trabajados(date(2026, 7, 1), date(2026, 8, 10), 2026, 8) == 10.0
    )


def test_calcular_dias_trabajados_mes_completo():
    """Sin novedades en el mes -> 30 días."""
    assert calcular_dias_trabajados(date(2026, 7, 1), None, 2026, 8) == 30.0
    assert calcular_dias_trabajados(date(2026, 8, 1), None, 2026, 8) == 30.0


def test_inferir_nivel_cargo_superior():
    assert inferir_nivel_cargo("Tigre (ISFDyT N199)", "Matemática", "") == NivelCargo.SM
    assert inferir_nivel_cargo("ISFT 199", "", "") == NivelCargo.SM


def test_inferir_nivel_cargo_secundario_tecnico():
    assert (
        inferir_nivel_cargo("Escobar (Tecnica 1)", "Electrónica", "") == NivelCargo.PM
    )
    assert inferir_nivel_cargo("", "", "05-TIGRE MT-0001") == NivelCargo.PM


def test_mapear_revista():
    assert mapear_revista(RevistaHoraria.TITULAR) == SituacionRevista.TITULAR
    assert mapear_revista(RevistaHoraria.PROVISIONAL) == SituacionRevista.PROVISIONAL
    assert mapear_revista(RevistaHoraria.SUPLENTE) == SituacionRevista.SUPLENTE


def test_designacion_a_dominio():
    desig = DesignacionDocente(
        id_designacion="d-1",
        docente_cuit="20365283924",
        establecimiento="Tigre (ISFDyT N199)",
        distrito="TIGRE",
        cargo_asignatura="Matemática",
        revista=RevistaHoraria.PROVISIONAL,
        modulos=4,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 8, 13), fecha_hasta=None),
        secuencia=16,
        escuela_numero="",
    )

    resultado = ProyeccionSueldoMapper.designacion_a_dominio(desig, 2026, 8, "202608")

    assert resultado.secuencia == "016"
    assert resultado.cargo_nivel == NivelCargo.SM
    assert resultado.carga_horaria == 4.0
    assert resultado.situacion_revista == SituacionRevista.PROVISIONAL
    assert resultado.dias_trabajados == 18.0
    assert resultado.periodo_liquidado == "202608"
    assert resultado.es_retroactivo is True
    assert resultado.fecha_inicio == "2026-08-13"
    assert resultado.fecha_fin is None
