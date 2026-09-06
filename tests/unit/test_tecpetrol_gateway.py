"""Unit tests for TecpetrolTalentGateway."""

from unittest.mock import MagicMock

import httpx

from src.adapters.gateways.empleo.tecpetrol_talent_gateway import (
    TecpetrolTalentGateway,
)
from src.domain.empleo.value_objects import FuenteOferta


def test_tecpetrol_talent_gateway_parsing():
    mock_response_data = {
        "d": {
            "results": [
                {
                    "jobReqId": "88120",
                    "jobTitle": "Especialista en Confiabilidad y Mantenimiento de Planta",
                    "location": "Fortín de Piedra, Neuquén, Argentina",
                    "jobDescription": "Mantenimiento predictivo CBM, monitoreo de turbocompresores, variadores y celdas.",
                    "applyUrl": "https://careers.techint.com/job/88120",
                    "postingDate": "/Date(1725148800000)/",
                }
            ]
        }
    }

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data
    mock_client.get.return_value = mock_resp

    gateway = TecpetrolTalentGateway(http_client=mock_client)
    assert gateway.obtener_fuente() == FuenteOferta.TECPETROL

    ofertas = gateway.buscar_ofertas(
        palabras_clave=("confiabilidad",), ubicacion="Neuquén"
    )
    assert len(ofertas) == 1
    primera = ofertas[0]
    assert primera.id_oferta == "tec-88120"
    assert primera.empresa == "Tecpetrol (Grupo Techint)"
    assert "Confiabilidad" in primera.titulo
    assert "Fortín de Piedra" in primera.ubicacion
    assert primera.fuente == FuenteOferta.TECPETROL


def test_tecpetrol_talent_gateway_network_error():
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectTimeout("Timeout")

    gateway = TecpetrolTalentGateway(http_client=mock_client)
    ofertas = gateway.buscar_ofertas(palabras_clave=("confiabilidad",))
    assert ofertas == []
