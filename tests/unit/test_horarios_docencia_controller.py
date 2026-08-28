"""Tests unitarios para HorariosDocenciaController y Use Cases temporales."""

from src.adapters.controllers.horarios_docencia_controller import (
    HorariosDocenciaController,
)
from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.application.dtos.horarios_docencia_dto import (
    CargoDocenteDTO,
    CesarDesignacionInputDTO,
    DeclaracionHorariaInputDTO,
    HorarioBloqueDTO,
    RegistrarDesignacionInputDTO,
)
from src.application.use_cases.cesar_designacion import CesarDesignacionUseCase
from src.application.use_cases.consultar_designaciones_vigentes import (
    ConsultarDesignacionesVigentesUseCase,
)
from src.application.use_cases.consultar_historial_docente import (
    ConsultarHistorialDocenteUseCase,
)
from src.application.use_cases.registrar_designacion import (
    RegistrarDesignacionUseCase,
)
from src.application.use_cases.validar_horarios_docencia import (
    ValidarHorariosDocenciaUseCase,
)


def test_controller_validar_declaracion() -> None:
    """Verifica que el controlador recibe el DTO ad-hoc y devuelve el reporte de compatibilidad."""
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
                ige="IGE-101",
                modulos=2,
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
                ige="IGE-102",
                modulos=2,
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
    assert resultado.total_modulos == 4
    assert len(resultado.conflictos) == 1
    assert resultado.conflictos[0].tipo == "SUPERPOSICION_HORARIA"
    assert resultado.conflictos[0].severidad == "CRITICO"


def test_controller_flujo_temporal_persistencia() -> None:
    """Verifica el flujo completo de persistencia temporal en el controlador."""
    repo = SQLDesignacionDocenteGateway(database_url="sqlite:///:memory:")
    validar_uc = ValidarHorariosDocenciaUseCase()
    registrar_uc = RegistrarDesignacionUseCase(repository=repo)
    cesar_uc = CesarDesignacionUseCase(repository=repo)
    vigentes_uc = ConsultarDesignacionesVigentesUseCase(repository=repo)
    historial_uc = ConsultarHistorialDocenteUseCase(repository=repo)

    controller = HorariosDocenciaController(
        validar_use_case=validar_uc,
        registrar_use_case=registrar_uc,
        cesar_use_case=cesar_uc,
        consultar_vigentes_use_case=vigentes_uc,
        consultar_historial_use_case=historial_uc,
    )

    # 1. Registrar cargo titular
    dto_titular = RegistrarDesignacionInputDTO(
        docente_cuit="20-36528392-4",
        ige="IGE-T1",
        establecimiento="EEST N° 1 Pilar",
        distrito="Pilar",
        cargo_asignatura="Electrotecnia",
        revista="TITULAR",
        modulos=2,
        fecha_desde="2026-03-01",
        horarios=[
            HorarioBloqueDTO(
                dia="LUNES",
                hora_inicio="07:30",
                hora_fin="09:30",
                turno="MANANA",
            )
        ],
    )
    res_tit = controller.registrar_designacion(dto_titular)
    assert res_tit.designacion.id_designacion != ""
    assert res_tit.designacion.ige == "IGE-T1"

    # 2. Registrar suplencia
    dto_suplente = RegistrarDesignacionInputDTO(
        docente_cuit="20-36528392-4",
        ige="IGE-S1",
        establecimiento="ISFT N° 199 Tigre",
        distrito="Tigre",
        cargo_asignatura="Automatización",
        revista="SUPLENTE",
        modulos=2,
        fecha_desde="2026-04-01",
        fecha_hasta="2026-06-30",
        horarios=[
            HorarioBloqueDTO(
                dia="MARTES",
                hora_inicio="18:00",
                hora_fin="20:00",
                turno="VESPERTINO",
            )
        ],
    )
    res_sup = controller.registrar_designacion(dto_suplente)
    assert res_sup.designacion.revista == "SUPLENTE"

    # 3. Consultar vigentes en Mayo (2 cargos)
    rep_mayo = controller.consultar_vigentes_en_fecha("20-36528392-4", "2026-05-15")
    assert rep_mayo.total_cargos == 2
    assert rep_mayo.es_compatible is True

    # 4. Consultar vigentes en Julio (1 cargo, la suplencia ya terminó)
    rep_julio = controller.consultar_vigentes_en_fecha("20-36528392-4", "2026-07-15")
    assert rep_julio.total_cargos == 1

    # 5. Cesar el titular
    cesado = controller.cesar_designacion(
        res_tit.designacion.id_designacion,
        CesarDesignacionInputDTO(fecha_hasta="2026-08-31", motivo_cese="RENUNCIA"),
    )
    assert cesado is not None
    assert cesado.motivo_cese == "RENUNCIA"

    # 6. Historial completo (2 registros)
    historial = controller.consultar_historial("20-36528392-4")
    assert len(historial) == 2
