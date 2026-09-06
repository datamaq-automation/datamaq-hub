"""Unit tests for empleo oportunidades and tracking use cases."""

from unittest.mock import MagicMock

from src.application.dtos.empleo_dtos import (
    ActualizarEstadoOportunidadDTO,
    RegistrarInteraccionDTO,
    RegistrarOportunidadDTO,
)
from src.application.use_cases.empleo.gestionar_oportunidades_use_cases import (
    ActualizarEstadoOportunidadUseCase,
    ListarInteraccionesUseCase,
    ListarOportunidadesUseCase,
    RegistrarInteraccionUseCase,
    RegistrarOportunidadUseCase,
)
from src.domain.empleo.entities import (
    InteraccionPostulacion,
    OportunidadLaboral,
)
from src.domain.empleo.value_objects import EstadoOportunidad


def test_registrar_y_listar_oportunidad_use_cases():
    repo = MagicMock()
    repo.guardar.side_effect = lambda op: OportunidadLaboral(
        id=100,
        titulo=op.titulo,
        empresa=op.empresa,
        ubicacion=op.ubicacion,
        estado=op.estado,
    )
    repo.listar.return_value = [
        OportunidadLaboral(
            id=100,
            titulo="Supervisor de Instrumentación",
            empresa="Tecpetrol",
            ubicacion="Añelo",
            estado=EstadoOportunidad.DETECTADA,
        )
    ]

    registrar_uc = RegistrarOportunidadUseCase(repository=repo)
    listar_uc = ListarOportunidadesUseCase(repository=repo)

    dto = RegistrarOportunidadDTO(
        titulo="Supervisor de Instrumentación",
        empresa="Tecpetrol",
        ubicacion="Añelo",
        estado="DETECTADA",
    )

    creada = registrar_uc.execute(dto)
    assert creada.id == 100
    assert creada.empresa == "Tecpetrol"

    lista = listar_uc.execute(estado=None, empresa=None)
    assert len(lista) == 1
    assert lista[0].titulo == "Supervisor de Instrumentación"


def test_actualizar_estado_use_case():
    repo = MagicMock()
    repo.actualizar_estado.return_value = OportunidadLaboral(
        id=40,
        titulo="Oficial Calificado",
        empresa="YPF S.A.",
        ubicacion="Neuquén",
        estado=EstadoOportunidad.ENTREVISTA,
        notas="Entrevista confirmada",
    )

    use_case = ActualizarEstadoOportunidadUseCase(repository=repo)
    dto = ActualizarEstadoOportunidadDTO(
        id_oportunidad=40,
        nuevo_estado="ENTREVISTA",
        notas="Entrevista confirmada",
    )

    resultado = use_case.execute(dto)
    assert resultado.estado == "ENTREVISTA"
    assert resultado.notas == "Entrevista confirmada"
    repo.actualizar_estado.assert_called_once_with(
        id_oportunidad=40,
        nuevo_estado=EstadoOportunidad.ENTREVISTA,
        notas="Entrevista confirmada",
    )


def test_registrar_interaccion_use_case():
    repo = MagicMock()
    repo.registrar_interaccion.side_effect = lambda i: InteraccionPostulacion(
        id=5,
        oportunidad_id=i.oportunidad_id,
        fecha=i.fecha,
        canal=i.canal,
        contacto_nombre=i.contacto_nombre,
        resumen=i.resumen,
    )

    use_case = RegistrarInteraccionUseCase(repository=repo)
    dto = RegistrarInteraccionDTO(
        oportunidad_id=40,
        fecha="2026-09-06",
        canal="TELEFONO",
        contacto_nombre="Lic. Reclutamiento YPF",
        resumen="Llamado de coordinación para entrevista en sede Añelo.",
    )

    resultado = use_case.execute(dto)
    assert resultado.id == 5
    assert resultado.contacto_nombre == "Lic. Reclutamiento YPF"


def test_listar_interacciones_use_case():
    repo = MagicMock()
    repo.listar_interacciones.return_value = [
        InteraccionPostulacion(
            id=1,
            oportunidad_id=40,
            fecha="2026-09-01",
            canal="LINKEDIN",
            contacto_nombre="Headhunter Tech",
            resumen="Primer contacto",
        ),
        InteraccionPostulacion(
            id=2,
            oportunidad_id=40,
            fecha="2026-09-05",
            canal="MAIL",
            contacto_nombre="RRHH",
            resumen="Envío de CV actualizado",
        ),
    ]

    use_case = ListarInteraccionesUseCase(repository=repo)
    resultado = use_case.execute(oportunidad_id=40)
    assert len(resultado) == 2
    assert resultado[0].id == 1
    assert resultado[1].canal == "MAIL"
    repo.listar_interacciones.assert_called_once_with(oportunidad_id=40)
