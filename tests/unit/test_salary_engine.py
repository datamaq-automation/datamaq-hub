"""Unit tests for deterministic salary calculation engine."""

import pytest

from src.adapters.gateways.paritaria_json_gateway import ParitariaJsonGateway
from src.domain.liquidacion.entities import DesignacionDocente
from src.domain.liquidacion.exceptions import (
    DesignacionInvalidaException,
    ParitariaNoEncontradaException,
)
from src.domain.liquidacion.services import MotorLiquidacionDocenteService
from src.domain.liquidacion.value_objects import (
    EscalaAntiguedad,
    NivelCargo,
    ParametrosParitaria,
    SituacionRevista,
)


@pytest.fixture
def motor() -> MotorLiquidacionDocenteService:
    return MotorLiquidacionDocenteService()


@pytest.fixture
def paritaria() -> ParametrosParitaria:
    return ParametrosParitaria(
        periodo="202608",
        basico_por_modulo_sm=42894.625,
        basico_por_modulo_pm=22877.1325,
        bonif_0455_sm=14125.9425,
        bonif_0455_pm=9281.9325,
        bonif_0667_sm=14796.8575,
        bonif_0667_pm=9722.7825,
        bonif_2575_sm=3390.187,
        bonif_2575_pm=2009.00,
        alicuota_ips=0.1600,
        alicuota_ioma=0.0480,
        alicuota_suteba_sindicato=0.0155,
        alicuota_suteba_os=0.0464,
        tope_bonificaciones_modulos=30.0,
    )


def test_escala_antiguedad():
    assert EscalaAntiguedad.obtener_porcentaje(0) == 0.0
    assert EscalaAntiguedad.obtener_porcentaje(1) == 0.30
    assert EscalaAntiguedad.obtener_porcentaje(4) == 0.33
    assert EscalaAntiguedad.obtener_porcentaje(5) == 0.40
    assert EscalaAntiguedad.obtener_porcentaje(10) == 0.60
    assert EscalaAntiguedad.obtener_porcentaje(24) == 1.20


def test_paritaria_json_gateway():
    gateway = ParitariaJsonGateway()
    p = gateway.obtener_por_periodo("202608")
    assert p.periodo == "202608"
    assert p.basico_por_modulo_sm == 42894.625
    assert p.basico_por_modulo_pm == 22877.1325
    assert p.alicuota_ips == 0.16
    assert p.alicuota_ioma == 0.048
    assert p.alicuota_suteba_sindicato == 0.0155
    assert p.alicuota_suteba_os == 0.0464
    assert p.tope_bonificaciones_modulos == 30.0


def test_paritaria_json_gateway_periodo_inexistente():
    gateway = ParitariaJsonGateway()
    with pytest.raises(ParitariaNoEncontradaException):
        gateway.obtener_por_periodo("199901")


def test_paritaria_json_gateway_invalido(tmp_path):
    invalid_file = tmp_path / "202609.json"
    invalid_file.write_text(
        '{"periodo": "202609"}', encoding="utf-8"
    )  # Missing required fields
    gateway = ParitariaJsonGateway(data_dir=tmp_path)
    with pytest.raises(ParitariaNoEncontradaException):
        gateway.obtener_por_periodo("202609")


def test_paritaria_json_gateway_cache():
    gateway = ParitariaJsonGateway()
    p1 = gateway.obtener_por_periodo("202608")
    p2 = gateway.obtener_por_periodo("202608")
    assert p1 is p2  # Cache hits return same object instance


def test_calculo_superior_sm_7hs_sin_paros(motor, paritaria):
    designacion = DesignacionDocente(
        secuencia="016",
        escuela_codigo="IS-0199",
        escuela_nombre="ISFDyT 199",
        cargo_nivel=NivelCargo.SM,
        carga_horaria=7.0,
        situacion_revista=SituacionRevista.PROVISIONAL,
        dias_trabajados=30.0,
        periodo_liquidado="202608",
        inasistencias_paro=0.0,
        aplica_suteba=True,
    )

    resultado, _ = motor.liquidar_cargo(
        designacion, anios_antiguedad=4, paritaria=paritaria
    )

    # 7 * 42894.625 = 300262.38
    assert resultado.subtotal_haberes > 600000
    assert resultado.subtotal_descuentos > 0
    assert (
        round(resultado.subtotal_haberes - resultado.subtotal_descuentos, 2)
        == resultado.liquido
    )
    # Verificación de conceptos presentes
    codigos = [c.codigo for c in resultado.conceptos]
    assert "0510" in codigos  # Básico provisional
    assert "0220" in codigos  # Antigüedad
    assert "0455" in codigos  # Bonif Docente
    assert "0667" in codigos  # Bonif No Jerárquica
    assert "2575" in codigos  # FONID
    assert "1060" in codigos  # IPS
    assert "1280" in codigos  # IOMA
    assert "1472" in codigos  # SUTEBA


def test_calculo_con_dias_de_paro(motor, paritaria):
    designacion = DesignacionDocente(
        secuencia="016",
        escuela_codigo="IS-0199",
        escuela_nombre="ISFDyT 199",
        cargo_nivel=NivelCargo.SM,
        carga_horaria=7.0,
        situacion_revista=SituacionRevista.PROVISIONAL,
        dias_trabajados=30.0,
        periodo_liquidado="202608",
        inasistencias_paro=3.0,
        aplica_suteba=True,
    )

    resultado, _ = motor.liquidar_cargo(
        designacion, anios_antiguedad=4, paritaria=paritaria
    )
    codigos = [c.codigo for c in resultado.conceptos]
    assert "1173" in codigos  # Retención básico paros
    assert "1273" in codigos  # Retención antigüedad paros

    # Verificar monto retención paros: (3/30) * 300262.38 = 30026.24
    concepto_1173 = next(c for c in resultado.conceptos if c.codigo == "1173")
    assert concepto_1173.descuentos == 30026.24


def test_calculo_secundaria_pm_4hs(motor, paritaria):
    designacion = DesignacionDocente(
        secuencia="019",
        escuela_codigo="MT-0001",
        escuela_nombre="EEST 1",
        cargo_nivel=NivelCargo.PM,
        carga_horaria=4.0,
        situacion_revista=SituacionRevista.SUPLENTE,
        dias_trabajados=30.0,
        periodo_liquidado="202608",
    )

    resultado, _ = motor.liquidar_cargo(
        designacion, anios_antiguedad=4, paritaria=paritaria
    )
    assert resultado.cargo_nivel == NivelCargo.PM
    assert resultado.carga_horaria == 4.0
    assert resultado.liquido > 150000


def test_calculo_retroactivo_proporcional_dias(motor, paritaria):
    # 9 días en junio para Sec 23 Escobar
    designacion = DesignacionDocente(
        secuencia="023",
        escuela_codigo="MT-0001",
        escuela_nombre="EEST 1 Escobar",
        cargo_nivel=NivelCargo.PM,
        carga_horaria=4.0,
        situacion_revista=SituacionRevista.SUPLENTE,
        dias_trabajados=9.0,
        periodo_liquidado="202606",
        es_retroactivo=True,
    )

    resultado, _ = motor.liquidar_cargo(
        designacion, anios_antiguedad=4, paritaria=paritaria
    )
    assert resultado.dias_trabajados == 9.0
    assert resultado.es_retroactivo is True
    assert resultado.liquido > 0
    # Básico proporcional: (9/30) * (4 * 22877.1325) = (9/30) * 91508.53 = 27452.56
    concepto_basico = next(c for c in resultado.conceptos if c.codigo == "0511")
    assert concepto_basico.haberes == 27452.56


def test_validacion_errores_designacion(motor, paritaria):
    with pytest.raises(DesignacionInvalidaException):
        motor.liquidar_cargo(
            DesignacionDocente(
                secuencia="001",
                escuela_codigo="E1",
                escuela_nombre="Escuela 1",
                cargo_nivel=NivelCargo.SM,
                carga_horaria=0,  # Inválido
                situacion_revista=SituacionRevista.PROVISIONAL,
                dias_trabajados=30.0,
                periodo_liquidado="202608",
            ),
            anios_antiguedad=4,
            paritaria=paritaria,
        )

    with pytest.raises(DesignacionInvalidaException):
        motor.liquidar_cargo(
            DesignacionDocente(
                secuencia="001",
                escuela_codigo="E1",
                escuela_nombre="Escuela 1",
                cargo_nivel=NivelCargo.SM,
                carga_horaria=4,
                situacion_revista=SituacionRevista.PROVISIONAL,
                dias_trabajados=35,  # Inválido > 30
                periodo_liquidado="202608",
            ),
            anios_antiguedad=4,
            paritaria=paritaria,
        )


def test_liquidar_consolidado_distingue_regulares_y_retroactivos(motor, paritaria):
    designaciones = [
        DesignacionDocente(
            secuencia="016",
            escuela_codigo="IS-0199",
            escuela_nombre="ISFDyT 199",
            cargo_nivel=NivelCargo.SM,
            carga_horaria=7.0,
            situacion_revista=SituacionRevista.PROVISIONAL,
            dias_trabajados=30.0,
            periodo_liquidado="202608",
        ),
        DesignacionDocente(
            secuencia="023",
            escuela_codigo="MT-0001",
            escuela_nombre="EEST 1",
            cargo_nivel=NivelCargo.PM,
            carga_horaria=4.0,
            situacion_revista=SituacionRevista.SUPLENTE,
            dias_trabajados=9.0,
            periodo_liquidado="202606",
            es_retroactivo=True,
        ),
    ]

    consolidado = motor.liquidar_consolidado(
        designaciones=designaciones,
        anios_antiguedad=4,
        paritaria=paritaria,
    )

    assert consolidado.total_liquido == round(
        consolidado.total_liquido_regular + consolidado.total_liquido_retroactivos, 2
    )
    assert consolidado.total_liquido_regular > 0
    assert consolidado.total_liquido_retroactivos > 0
