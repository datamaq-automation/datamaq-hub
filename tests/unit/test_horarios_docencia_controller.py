"""Tests unitarios para HorariosDocenciaController y Use Case."""

from src.adapters.controllers.horarios_docencia_controller import (
    HorariosDocenciaController,
)
from src.application.dtos.horarios_docencia_dto import (
    CargoDocenteDTO,
    DeclaracionHorariaInputDTO,
    HorarioBloqueDTO,
)
from src.application.use_cases.validar_horarios_docencia import (
    ValidarHorariosDocenciaUseCase,
)


def test_controller_validar_declaracion() -> None:
    """Verifica que el controlador recibe el DTO y devuelve el reporte de compatibilidad."""
    use_case = ValidarHorariosDocenciaUseCase()
    controller = HorariosDocenciaController(validar_use_case=use_case)

    input_dto = DeclaracionHorariaInputDTO(
        docente_nombre="Agustín Deoz",
        cuit="20-36528392-4",
        dni="36528392",
        margen_traslado_minutos=20,
        cargos=[
            CargoDocenteDTO(
                id_cargo="CARGO-01",
                establecimiento="EEST N° 1 Pilar",
                distrito="Pilar",
                cargo_asignatura="Electrotecnia 4to",
                revista="TITULAR",
                modulos=4,
                es_cargo_base=False,
                horarios=[
                    HorarioBloqueDTO(
                        dia="LUNES",
                        hora_inicio="07:30",
                        hora_fin="09:30",
                        turno="MANANA",
                    )
                ],
            ),
            CargoDocenteDTO(
                id_cargo="CARGO-02",
                establecimiento="ISFT N° 199 Tigre",
                distrito="Tigre",
                cargo_asignatura="Automatización",
                revista="PROVISIONAL",
                modulos=4,
                es_cargo_base=False,
                horarios=[
                    HorarioBloqueDTO(
                        dia="LUNES",
                        hora_inicio="09:00",
                        hora_fin="11:00",
                        turno="MANANA",
                    )
                ],
            ),
        ],
    )

    resultado = controller.validar_declaracion(input_dto)
    assert resultado.es_compatible is False
    assert resultado.total_cargos == 2
    assert resultado.total_modulos == 8
    assert len(resultado.conflictos) == 1
    assert resultado.conflictos[0].tipo == "SUPERPOSICION_HORARIA"
    assert resultado.conflictos[0].severidad == "CRITICO"
