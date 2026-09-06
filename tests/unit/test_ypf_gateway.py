"""Unit tests for YpfTalentGateway and MemoryOfertasCacheGateway."""

from unittest.mock import MagicMock, patch

from src.adapters.gateways.empleo.memory_ofertas_cache_gateway import (
    MemoryOfertasCacheGateway,
)
from src.adapters.gateways.empleo.ypf_talent_gateway import YpfTalentGateway
from src.domain.empleo.entities import OfertaLaboral
from src.domain.empleo.value_objects import FuenteOferta


def test_ypf_talent_gateway_parsing():
    mock_response_data = {
        "d": {
            "results": [
                {
                    "jobReqId": "10045",
                    "jobTitle": "Ingeniero/a de Automatización y Control",
                    "location": "Añelo, Neuquén, Argentina",
                    "jobDescription": "Responsable de sistemas SCADA y PLCs en yacimiento Vaca Muerta.",
                    "applyUrl": "https://career8.successfactors.com/career?company=YPF&career_job_req_id=10045",
                    "postingDate": "/Date(1725148800000)/",
                },
                {
                    "jobReqId": "10046",
                    "jobTitle": "Analista de Impuestos",
                    "location": "Buenos Aires, Argentina",
                    "jobDescription": "Liquidación impositiva corporativa.",
                    "applyUrl": "https://career8.successfactors.com/career?company=YPF&career_job_req_id=10046",
                    "postingDate": "/Date(1725148800000)/",
                },
            ]
        }
    }

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data
    mock_client.get.return_value = mock_resp

    gateway = YpfTalentGateway(http_client=mock_client)
    ofertas = gateway.buscar_ofertas(
        palabras_clave=("automatizacion",), ubicacion="Neuquén"
    )

    assert len(ofertas) == 2
    primera = ofertas[0]
    assert primera.id_oferta == "ypf-10045"
    assert primera.empresa == "YPF S.A."
    assert "Automatización" in primera.titulo
    assert primera.ubicacion == "Añelo, Neuquén, Argentina"
    assert primera.fuente == FuenteOferta.YPF
    assert "https://career8.successfactors.com" in primera.url_postulacion


def test_ypf_talent_gateway_network_error():
    import httpx

    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectTimeout("Connection timeout")

    gateway = YpfTalentGateway(http_client=mock_client)
    # Debe capturar y devolver lista vacía en vez de tumbar el sistema
    ofertas = gateway.buscar_ofertas(palabras_clave=("automatizacion",))
    assert ofertas == []


def test_memory_ofertas_cache_gateway():
    cache = MemoryOfertasCacheGateway()
    key = "test_key"
    assert cache.obtener_ofertas(key) is None

    sample_ofertas = [
        OfertaLaboral(
            id_oferta="1",
            titulo="Ingeniero",
            empresa="YPF",
            ubicacion="Añelo",
            descripcion="",
            url_postulacion="",
            fuente=FuenteOferta.YPF,
        )
    ]

    cache.guardar_ofertas(key, sample_ofertas, ttl_segundos=60)
    cached = cache.obtener_ofertas(key)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0].id_oferta == "1"

    # Simular expiración
    with patch("time.time", return_value=1000000000.0):
        cache.guardar_ofertas("expiring", sample_ofertas, ttl_segundos=10)
    with patch("time.time", return_value=1000000020.0):
        assert cache.obtener_ofertas("expiring") is None
