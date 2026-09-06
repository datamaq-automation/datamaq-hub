"""Unit tests for empleo domain (entities, value objects, domain services)."""

from dataclasses import FrozenInstanceError

import pytest

from src.domain.empleo.entities import (
    OfertaLaboral,
    PerfilProfesional,
)
from src.domain.empleo.services import (
    FiltroVacaMuertaService,
    ScoringOfertasService,
)
from src.domain.empleo.value_objects import (
    FuenteOferta,
    ModalidadTrabajo,
    NivelAfinidad,
    UbicacionCuenca,
)


def test_oferta_laboral_immutability():
    oferta = OfertaLaboral(
        id_oferta="ypf-123",
        titulo="Ingeniero de Automatización y Control",
        empresa="YPF S.A.",
        ubicacion="Añelo, Neuquén",
        descripcion="Buscamos ingeniero con experiencia en SCADA y PLC para yacimiento.",
        url_postulacion="https://ypf.trabajo.org/job/123",
        fecha_publicacion="2026-09-01",
        fuente=FuenteOferta.YPF,
        tags=("SCADA", "PLC", "Automatización"),
    )
    assert oferta.id_oferta == "ypf-123"
    assert oferta.fuente == FuenteOferta.YPF
    with pytest.raises(FrozenInstanceError):
        oferta.titulo = "Otro titulo"  # type: ignore[misc]


def test_ubicacion_cuenca_vaca_muerta_detection():
    assert UbicacionCuenca.es_vaca_muerta("Añelo, Neuquén") is True
    assert UbicacionCuenca.es_vaca_muerta("Rincón de los Sauces") is True
    assert UbicacionCuenca.es_vaca_muerta("Plaza Huincul, NQN") is True
    assert UbicacionCuenca.es_vaca_muerta("Cipolletti, Río Negro") is True
    assert UbicacionCuenca.es_vaca_muerta("Neuquén Capital") is True
    assert UbicacionCuenca.es_vaca_muerta("Ciudad Autónoma de Buenos Aires") is False
    assert UbicacionCuenca.es_vaca_muerta("Rosario, Santa Fe") is False


def test_filtro_vaca_muerta_service():
    service = FiltroVacaMuertaService()

    # Por ubicación
    oferta_nqn = OfertaLaboral(
        id_oferta="1",
        titulo="Supervisor Eléctrico",
        empresa="Operadora",
        ubicacion="Añelo",
        descripcion="Mantenimiento en planta.",
        url_postulacion="https://...",
        fuente=FuenteOferta.YPF,
    )
    assert service.es_relevante_vaca_muerta(oferta_nqn) is True

    # Por keywords en descripción/título aunque ubicación sea genérica
    oferta_upstream = OfertaLaboral(
        id_oferta="2",
        titulo="Ingeniero de Perforación y Fractura (Upstream)",
        empresa="Servicios Petroleros",
        ubicacion="Argentina",
        descripcion="Operaciones de wellsite en formación Vaca Muerta.",
        url_postulacion="https://...",
        fuente=FuenteOferta.GENERICO,
    )
    assert service.es_relevante_vaca_muerta(oferta_upstream) is True

    # Oferta no relacionada
    oferta_otra = OfertaLaboral(
        id_oferta="3",
        titulo="Cajero Bancario",
        empresa="Banco",
        ubicacion="La Plata, Buenos Aires",
        descripcion="Atención al público en sucursal.",
        url_postulacion="https://...",
        fuente=FuenteOferta.GENERICO,
    )
    assert service.es_relevante_vaca_muerta(oferta_otra) is False


def test_scoring_ofertas_service():
    service = ScoringOfertasService()
    perfil = PerfilProfesional(
        titulo_deseado="Ingeniero de Automatización",
        palabras_clave_prioritarias=("SCADA", "PLC", "Automatización", "Telemetría"),
        palabras_clave_secundarias=("Python", "Modbus", "IoT", "Instrumentación"),
        ubicaciones_preferidas=("Neuquén", "Añelo"),
        modalidades_admitidas=(
            ModalidadTrabajo.ROTACIONAL_YACIMIENTO,
            ModalidadTrabajo.PRESENCIAL,
        ),
    )

    oferta_alta = OfertaLaboral(
        id_oferta="101",
        titulo="Ingeniero de Automatización y SCADA",
        empresa="YPF S.A.",
        ubicacion="Añelo, Neuquén",
        descripcion="Experiencia con PLC Rockwell/Siemens, protocolos Modbus e instrumentación en pozo.",
        url_postulacion="https://...",
        fuente=FuenteOferta.YPF,
        modalidad=ModalidadTrabajo.ROTACIONAL_YACIMIENTO,
    )

    scored = service.calcular_afinidad(oferta_alta, perfil)
    assert scored.score_afinidad >= 70
    assert scored.nivel_afinidad == NivelAfinidad.ALTA


def test_perfil_agustin_bustos():
    from src.domain.empleo.entities import obtener_perfil_agustin_bustos

    perfil = obtener_perfil_agustin_bustos()
    assert "Confiabilidad" in perfil.titulo_deseado
    assert "apm" in perfil.palabras_clave_prioritarias
    assert "vfd" in perfil.palabras_clave_prioritarias
    assert "telemetria" in perfil.palabras_clave_prioritarias
    assert "python" in perfil.palabras_clave_secundarias
    assert "añelo" in perfil.ubicaciones_preferidas

    # Probar scoring contra un puesto real de Vaca Muerta para su perfil
    service = ScoringOfertasService()
    oferta_confiabilidad = OfertaLaboral(
        id_oferta="ypf-999",
        titulo="Ingeniero de Confiabilidad y Mantenimiento de Planta",
        empresa="YPF",
        ubicacion="Añelo, Neuquén",
        descripcion="Gestión de mantenimiento predictivo, análisis CBM, monitoreo de variadores VFD y celdas de media tensión.",
        url_postulacion="https://...",
        fuente=FuenteOferta.YPF,
        modalidad=ModalidadTrabajo.ROTACIONAL_YACIMIENTO,
    )
    scored = service.calcular_afinidad(oferta_confiabilidad, perfil)
    assert scored.score_afinidad >= 75.0
    assert scored.nivel_afinidad == NivelAfinidad.ALTA
