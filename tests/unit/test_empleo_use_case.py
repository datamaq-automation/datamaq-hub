"""Unit tests for BuscarOfertasVacaMuertaUseCase."""

from unittest.mock import MagicMock

from src.application.dtos.empleo_dtos import BuscarOfertasQueryDTO, PerfilProfesionalDTO
from src.application.use_cases.empleo.buscar_ofertas_vaca_muerta_use_case import (
    BuscarOfertasVacaMuertaUseCase,
)
from src.domain.empleo.entities import OfertaLaboral
from src.domain.empleo.value_objects import FuenteOferta, ModalidadTrabajo


def test_buscar_ofertas_vaca_muerta_multi_portal_and_scoring():
    portal_ypf = MagicMock()
    portal_ypf.obtener_fuente.return_value = FuenteOferta.YPF
    portal_ypf.buscar_ofertas.return_value = [
        OfertaLaboral(
            id_oferta="ypf-1",
            titulo="Ingeniero de Automatización y SCADA",
            empresa="YPF",
            ubicacion="Añelo, Neuquén",
            descripcion="Manejo de PLC y telemetría de pozos en yacimiento.",
            url_postulacion="https://jobs.ypf.com/1",
            fuente=FuenteOferta.YPF,
            modalidad=ModalidadTrabajo.ROTACIONAL_YACIMIENTO,
        ),
        OfertaLaboral(
            id_oferta="ypf-2",
            titulo="Contador Senior",
            empresa="YPF",
            ubicacion="Buenos Aires",
            descripcion="Auditoría fiscal en sede central.",
            url_postulacion="https://jobs.ypf.com/2",
            fuente=FuenteOferta.YPF,
        ),
    ]

    portal_tecpetrol = MagicMock()
    portal_tecpetrol.obtener_fuente.return_value = FuenteOferta.TECPETROL
    portal_tecpetrol.buscar_ofertas.return_value = [
        OfertaLaboral(
            id_oferta="tec-1",
            titulo="Especialista en Instrumentación y Control",
            empresa="Tecpetrol",
            ubicacion="Fortín de Piedra, Neuquén",
            descripcion="Instrumentación de campo, calibración y telemetría.",
            url_postulacion="https://jobs.tecpetrol.com/1",
            fuente=FuenteOferta.TECPETROL,
        )
    ]

    cache_mock = MagicMock()
    cache_mock.obtener_ofertas.return_value = None

    use_case = BuscarOfertasVacaMuertaUseCase(
        portales=[portal_ypf, portal_tecpetrol],
        cache=cache_mock,
    )

    query = BuscarOfertasQueryDTO(
        palabras_clave=["automatizacion", "scada"],
        solo_vaca_muerta=True,
        min_score_afinidad=30.0,
        perfil=PerfilProfesionalDTO(
            titulo_deseado="Ingeniero de Automatización",
            palabras_clave_prioritarias=["SCADA", "PLC", "Telemetría"],
            palabras_clave_secundarias=["Instrumentación"],
            ubicaciones_preferidas=["Neuquén", "Añelo"],
        ),
    )

    resultado = use_case.execute(query)

    # Solo deben figurar las de Vaca Muerta con score >= 30 (debe excluir al contador de BsAs)
    assert resultado.total_encontradas == 2
    assert len(resultado.ofertas) == 2
    # El orden debe ser descendente por score
    assert resultado.ofertas[0].score_afinidad >= resultado.ofertas[1].score_afinidad
    assert resultado.ofertas[0].empresa in ("YPF", "Tecpetrol")
    assert "YPF" in resultado.fuentes_consultadas
    assert "TECPETROL" in resultado.fuentes_consultadas
    assert cache_mock.guardar_ofertas.called
