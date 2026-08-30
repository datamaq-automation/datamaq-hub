"""Pruebas unitarias para el caso de uso de proyección salarial docente vigente por CUIT."""

from datetime import date

import pytest

from src.adapters.gateways.paritaria_json_gateway import ParitariaJsonGateway
from src.application.use_cases.proyectar_sueldo_docente_vigente import (
    ProyectarSueldoDocenteVigenteUseCase,
)
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.value_objects import (
    PeriodoVigencia,
)
from src.domain.horarios_docencia.value_objects import (
    SituacionRevista as RevistaHoraria,
)
from src.domain.liquidacion.exceptions import DocenteSinDesignacionesException
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
)
from src.domain.recibos.value_objects import TipoRecibo


class FakeDesignacionRepository:
    def __init__(self, designaciones: tuple[DesignacionDocente, ...] = ()) -> None:
        self._designaciones = list(designaciones)

    def obtener_historial(self, docente_cuit: str) -> tuple[DesignacionDocente, ...]:
        return tuple(self._designaciones)


class FakeReciboRepository:
    def __init__(self, recibos: list[ReciboSueldo] | None = None) -> None:
        self._recibos = recibos or []

    def listar(
        self,
        cuit: str | None = None,
        mes_pago: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReciboSueldo]:
        return list(self._recibos)[offset : offset + limit]


def _build_recibo(antiguedad: int = 4) -> ReciboSueldo:
    return ReciboSueldo(
        id_recibo="r-1",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA"),
        agente=Agente(
            nombre_completo="BUSTOS AGUSTAN",
            numero_documento="36528392",
            cuil="20-36528392-4",
            mes_pago="07 / 2026",
        ),
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(codigo="IS-0199"),
                cargo=CargoDetalle(secuencia="016", antiguedad_anios=antiguedad),
            )
        ],
    )


def _build_designacion(
    id_designacion: str,
    establecimiento: str,
    revista: RevistaHoraria,
    modulos: int,
    fecha_desde: date,
    fecha_hasta: date | None = None,
    secuencia: int | None = None,
    escuela_numero: str = "",
    cargo_asignatura: str = "Cargo",
) -> DesignacionDocente:
    return DesignacionDocente(
        id_designacion=id_designacion,
        docente_cuit="20365283924",
        establecimiento=establecimiento,
        distrito="",
        cargo_asignatura=cargo_asignatura,
        revista=revista,
        modulos=modulos,
        vigencia=PeriodoVigencia(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta),
        secuencia=secuencia,
        escuela_numero=escuela_numero,
    )


def _build_use_case(
    designaciones: tuple[DesignacionDocente, ...] = (),
    recibos: list[ReciboSueldo] | None = None,
) -> ProyectarSueldoDocenteVigenteUseCase:
    return ProyectarSueldoDocenteVigenteUseCase(
        designacion_repository=FakeDesignacionRepository(designaciones),
        recibo_repository=FakeReciboRepository(recibos),
        paritaria_repo=ParitariaJsonGateway(),
    )


def test_sin_designaciones_lanza_excepcion() -> None:
    use_case = _build_use_case()
    with pytest.raises(DocenteSinDesignacionesException):
        use_case.execute("20365283924", "202608")


def test_inferencia_antiguedad_desde_recibo() -> None:
    desig = _build_designacion(
        id_designacion="d-1",
        establecimiento="Tigre (ISFDyT N199)",
        revista=RevistaHoraria.PROVISIONAL,
        modulos=4,
        fecha_desde=date(2026, 7, 1),
        secuencia=16,
    )
    use_case = _build_use_case(
        designaciones=(desig,),
        recibos=[_build_recibo(antiguedad=4)],
    )
    resultado = use_case.execute("20-36528392-4", "202608")

    assert resultado.anios_antiguedad == 4
    assert resultado.docente_nombre == "BUSTOS AGUSTAN"
    assert resultado.cuit == "20365283924"


def test_flujo_completo_dos_cargos() -> None:
    regular = _build_designacion(
        id_designacion="d-reg",
        establecimiento="Tigre (ISFDyT N199)",
        revista=RevistaHoraria.PROVISIONAL,
        modulos=4,
        fecha_desde=date(2026, 7, 1),
        secuencia=16,
    )
    retroactivo = _build_designacion(
        id_designacion="d-retro",
        establecimiento="Escobar (Tecnica 1)",
        revista=RevistaHoraria.SUPLENTE,
        modulos=2,
        fecha_desde=date(2026, 8, 13),
        secuencia=20,
        cargo_asignatura="Electrónica",
    )
    use_case = _build_use_case(
        designaciones=(regular, retroactivo),
        recibos=[_build_recibo(antiguedad=4)],
    )
    resultado = use_case.execute("20365283924", "202608")

    assert resultado.periodo_proyectado == "202608"
    assert resultado.modulos_totales == 6.0
    assert len(resultado.cargos_liquidados) == 2

    devengado = resultado.escenario_devengado_total
    base = resultado.escenario_base_asegurado

    assert devengado.total_liquido > base.total_liquido
    assert resultado.retroactivo_estimado == round(
        devengado.total_liquido - base.total_liquido, 2
    )
    assert resultado.retroactivo_estimado > 0
