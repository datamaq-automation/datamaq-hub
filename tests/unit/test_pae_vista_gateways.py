"""Unit tests for PAE and Vista talent gateways."""

from unittest.mock import MagicMock

import httpx

from src.adapters.gateways.empleo.pae_talent_gateway import PaeTalentGateway
from src.adapters.gateways.empleo.vista_talent_gateway import VistaTalentGateway
from src.domain.empleo.value_objects import FuenteOferta, ModalidadTrabajo


def test_pae_talent_gateway_parsing():
    mock_response = {
        "d": {
            "results": [
                {
                    "jobReqId": "pae-551",
                    "jobTitle": "Ingeniero de Mantenimiento Electromecánico",
                    "location": "Lindero Atravesado, Neuquén, Argentina",
                    "jobDescription": "Mantenimiento preventivo de compresores, generadores y tableros CCM en yacimiento.",
                    "applyUrl": "https://jobs.pan-energy.com/job/551",
                    "postingDate": "/Date(1725148800000)/",
                }
            ]
        }
    }
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response
    mock_client.get.return_value = mock_resp

    gateway = PaeTalentGateway(http_client=mock_client)
    assert gateway.obtener_fuente() == FuenteOferta.PAE

    ofertas = gateway.buscar_ofertas(
        palabras_clave=("mantenimiento",), ubicacion="Neuquén"
    )
    assert len(ofertas) == 1
    o = ofertas[0]
    assert o.id_oferta == "pae-551"
    assert o.empresa == "Pan American Energy (PAE)"
    assert "Electromecánico" in o.titulo
    assert o.fuente == FuenteOferta.PAE
    assert o.modalidad == ModalidadTrabajo.ROTACIONAL_YACIMIENTO


def test_vista_talent_gateway_parsing():
    mock_response = {
        "jobs": [
            {
                "id": "vista-109",
                "title": "Supervisor de Instrumentación, Control y Telemetría",
                "location": "Bajada del Palo Oeste, Neuquén",
                "description": "Responsable de telemetría IoT, RTUs, variadores VFD e instrumentación de pozo.",
                "url": "https://vistaenergy.com/careers/109",
                "date": "2026-09-01",
            }
        ]
    }
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response
    mock_client.get.return_value = mock_resp

    gateway = VistaTalentGateway(http_client=mock_client)
    assert gateway.obtener_fuente() == FuenteOferta.VISTA

    ofertas = gateway.buscar_ofertas(
        palabras_clave=("instrumentacion",), ubicacion="Neuquén"
    )
    assert len(ofertas) == 1
    o = ofertas[0]
    assert o.id_oferta == "vista-109"
    assert o.empresa == "Vista Energy"
    assert "Telemetría" in o.titulo
    assert o.fuente == FuenteOferta.VISTA


def test_pae_and_vista_resilience_on_network_error():
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectTimeout("Timeout")

    pae_gw = PaeTalentGateway(http_client=mock_client)
    assert pae_gw.buscar_ofertas(palabras_clave=("test",)) == []

    vista_gw = VistaTalentGateway(http_client=mock_client)
    assert vista_gw.buscar_ofertas(palabras_clave=("test",)) == []
