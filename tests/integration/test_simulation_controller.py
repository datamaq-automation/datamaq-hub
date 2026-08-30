"""Integration tests for salary simulation controller."""

from starlette.testclient import TestClient


def test_simulation_controller_success(client: TestClient):
    payload = {
        "anios_antiguedad": 4,
        "periodo_proyectado": "202608",
        "tope_bonificaciones_modulos": 30.0,
        "designaciones": [
            {
                "secuencia": "016",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": 7.0,
                "situacion_revista": "PROV.",
                "dias_trabajados": 30.0,
                "inasistencias_paro": 0.0,
                "aplica_suteba": True,
            },
            {
                "secuencia": "021",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": 4.0,
                "situacion_revista": "SUP.",
                "dias_trabajados": 30.0,
            },
            {
                "secuencia": "023",
                "escuela_codigo": "MT-0001",
                "escuela_nombre": "EEST 1 Escobar",
                "cargo_nivel": "PM",
                "carga_horaria": 4.0,
                "situacion_revista": "SUP.",
                "dias_trabajados": 9.0,
                "es_retroactivo": True,
            },
        ],
    }

    response = client.post("/api/v1/simulacion", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True

    data = res_json["data"]
    assert data["periodo_proyectado"] == "202608"
    assert data["anios_antiguedad"] == 4
    assert len(data["cargos_liquidados"]) == 3
    assert data["total_liquido"] > 0
    assert data["total_liquido_regular"] > 0
    assert data["total_liquido_retroactivos"] > 0


def test_simulation_controller_validation_error(client: TestClient):
    # Missing required fields or negative carga_horaria
    payload = {
        "anios_antiguedad": 4,
        "designaciones": [
            {
                "secuencia": "016",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": -2.0,  # Invalid <= 0
                "situacion_revista": "PROV.",
            }
        ],
    }

    response = client.post("/api/v1/simulacion", json=payload)
    assert response.status_code == 422


def test_simulation_controller_invalid_period_format(client: TestClient):
    payload = {
        "anios_antiguedad": 4,
        "periodo_proyectado": "202613",  # Month 13 is invalid YYYYMM
        "designaciones": [
            {
                "secuencia": "016",
                "escuela_codigo": "IS-0199",
                "escuela_nombre": "ISFDyT 199",
                "cargo_nivel": "SM",
                "carga_horaria": 7.0,
                "situacion_revista": "PROV.",
            }
        ],
    }

    response = client.post("/api/v1/simulacion", json=payload)
    assert response.status_code == 422


def test_simulation_by_cuit_success(client: TestClient):
    import uuid
    from datetime import date
    from src.adapters.controllers.dependencies import get_designacion_docente_repository_gateway
    from src.domain.horarios_docencia.entities import DesignacionDocente
    from src.domain.horarios_docencia.value_objects import (
        PeriodoVigencia,
        SituacionRevista as RevistaHoraria,
    )
    from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
    from src.domain.recibos.entities import (
        Agente,
        CargoDetalle,
        Empleador,
        EstablecimientoDetalle,
        LiquidacionSecuencia,
        ReciboSueldo,
    )
    from src.domain.recibos.value_objects import TipoRecibo

    # 1. Recuperar el repository de la app (que es el en-memoria mockeado)
    repo = client.app.dependency_overrides[get_designacion_docente_repository_gateway]()

    # Generar CUIT único para aislar esta prueba (solo dígitos)
    import random
    test_suffix = "".join(str(random.randint(0, 9)) for _ in range(8))
    test_cuit = f"20{test_suffix}4"
    test_cuit_formatted = f"20-{test_suffix}-4"

    # 2. Guardar designaciones vía REST API
    payload = {
        "docente_cuit": test_cuit,
        "ige": "IGE-REG-01",
        "establecimiento": "Tigre (ISFDyT N199)",
        "distrito": "Tigre",
        "cargo_asignatura": "Matematica",
        "revista": "PROVISIONAL",
        "modulos": 4,
        "fecha_desde": "2026-07-01",
        "observaciones": "Test integration",
        "cupof": "CUP-REG-01",
        "horarios": [
            {
                "dia": "LUNES",
                "hora_inicio": "07:30",
                "hora_fin": "09:30",
                "turno": "MANANA",
            }
        ],
    }
    resp = client.post("/api/v1/horarios-docencia/designaciones", json=payload)
    assert resp.status_code == 200

    # 3. Guardar un recibo para inferencia de antigüedad
    recibo_repo = SQLReciboGateway()
    recibo = ReciboSueldo(
        id_recibo="rec-cuit-test-01",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA"),
        agente=Agente(
            nombre_completo="BUSTOS AGUSTAN INTEGRATION",
            numero_documento="36528392",
            cuil=test_cuit_formatted,
            mes_pago="07 / 2026",
        ),
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(codigo="IS-0199"),
                cargo=CargoDetalle(secuencia="016", antiguedad_anios=4),
            )
        ],
    )
    recibo_repo.guardar(recibo)

    # 4. Request projection by CUIT
    response = client.post(f"/api/v1/simulacion/docente/{test_cuit}?periodo=202608")
    print("RESPONSE JSON:", response.json())
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True

    data = res_json["data"]
    assert data["cuit"] == test_cuit
    assert data["docente_nombre"] == "BUSTOS AGUSTAN INTEGRATION"
    assert data["anios_antiguedad"] == 4
    assert data["modulos_totales"] == 4.0
    assert data["escenario_base_asegurado"]["total_liquido"] > 0
    assert data["escenario_devengado_total"]["total_liquido"] > 0

    # Clean up recibo from DB
    recibo_repo.eliminar("rec-cuit-test-01")


