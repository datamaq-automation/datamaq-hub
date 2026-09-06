"""FastAPI routes for empleo y oportunidades laborales en Vaca Muerta."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.adapters.controllers.dependencies import get_empleo_controller
from src.adapters.controllers.empleo_controller import EmpleoController
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.empleo_dtos import (
    ActualizarEstadoOportunidadDTO,
    BuscarOfertasQueryDTO,
    CambiarEstadoDTO,
    InteraccionDTO,
    OportunidadDTO,
    RegistrarInteraccionDTO,
    RegistrarOportunidadDTO,
    ResultadoBusquedaDTO,
)

router = APIRouter(prefix="/empleo", tags=["Búsqueda Laboral Vaca Muerta"])


@router.get(
    "/vaca-muerta",
    response_model=APIResponseDTO[ResultadoBusquedaDTO],
    summary="Búsqueda de ofertas laborales en Vaca Muerta",
    description=(
        "Consulta multifuente (YPF, ATS y portales de Oil & Gas), filtra por la cuenca neuquina "
        "y pondera la afinidad con el perfil técnico/ingenieril."
    ),
)
async def buscar_ofertas_vaca_muerta(
    controller: Annotated[EmpleoController, Depends(get_empleo_controller)],
    q: Annotated[list[str] | None, Query(description="Términos de búsqueda")] = None,
    ubicacion: Annotated[
        str | None, Query(description="Ubicación o localidad específica")
    ] = None,
    solo_vaca_muerta: Annotated[
        bool, Query(description="Filtrar estrictamente por Vaca Muerta / Oil & Gas")
    ] = True,
    min_score: Annotated[
        float, Query(ge=0.0, le=100.0, description="Puntaje mínimo de afinidad")
    ] = 0.0,
) -> APIResponseDTO[ResultadoBusquedaDTO]:
    """Ejecuta la búsqueda y ranking de ofertas vía GET."""
    query_dto = BuscarOfertasQueryDTO(
        palabras_clave=q or [],
        ubicacion=ubicacion,
        solo_vaca_muerta=solo_vaca_muerta,
        min_score_afinidad=min_score,
    )
    resultado = controller.buscar_ofertas_vaca_muerta(query_dto)
    return APIResponseDTO[ResultadoBusquedaDTO](success=True, data=resultado)


@router.post(
    "/vaca-muerta",
    response_model=APIResponseDTO[ResultadoBusquedaDTO],
    summary="Búsqueda avanzada de ofertas laborales con perfil personalizado",
    description="Permite enviar un perfil profesional específico para calcular el scoring de afinidad.",
)
async def buscar_ofertas_vaca_muerta_con_perfil(
    request: BuscarOfertasQueryDTO,
    controller: Annotated[EmpleoController, Depends(get_empleo_controller)],
) -> APIResponseDTO[ResultadoBusquedaDTO]:
    """Ejecuta la búsqueda con un perfil profesional personalizado."""
    resultado = controller.buscar_ofertas_vaca_muerta(request)
    return APIResponseDTO[ResultadoBusquedaDTO](success=True, data=resultado)


@router.get(
    "/oportunidades",
    response_model=APIResponseDTO[list[OportunidadDTO]],
    summary="Listar oportunidades de búsqueda laboral",
    description="Permite listar y filtrar oportunidades por estado del embudo y empresa.",
)
async def listar_oportunidades(
    controller: Annotated[EmpleoController, Depends(get_empleo_controller)],
    estado: Annotated[str | None, Query(description="Filtrar por estado")] = None,
    empresa: Annotated[str | None, Query(description="Filtrar por empresa")] = None,
) -> APIResponseDTO[list[OportunidadDTO]]:
    """Devuelve las oportunidades registradas en el tracker."""
    resultado = controller.listar_oportunidades(estado=estado, empresa=empresa)
    return APIResponseDTO[list[OportunidadDTO]](success=True, data=resultado)


@router.post(
    "/oportunidades",
    response_model=APIResponseDTO[OportunidadDTO],
    status_code=201,
    summary="Registrar nueva oportunidad laboral",
    description="Registra una nueva vacante u oportunidad detectada o postulada en la base de datos.",
)
async def registrar_oportunidad(
    dto: RegistrarOportunidadDTO,
    controller: Annotated[EmpleoController, Depends(get_empleo_controller)],
) -> APIResponseDTO[OportunidadDTO]:
    """Crea una oportunidad en la base de datos."""
    resultado = controller.registrar_oportunidad(dto)
    return APIResponseDTO[OportunidadDTO](success=True, data=resultado)


@router.patch(
    "/oportunidades/{id}/estado",
    response_model=APIResponseDTO[OportunidadDTO],
    summary="Actualizar estado de una postulación",
    description="Modifica el estado en el embudo (POSTULADA, ENTREVISTA, etc.) y registra notas.",
)
async def actualizar_estado_oportunidad(
    id: int,
    body: CambiarEstadoDTO,
    controller: Annotated[EmpleoController, Depends(get_empleo_controller)],
) -> APIResponseDTO[OportunidadDTO]:
    """Actualiza el estado y notas de una oportunidad por ID."""
    dto = ActualizarEstadoOportunidadDTO(
        id_oportunidad=id,
        nuevo_estado=body.nuevo_estado,
        notas=body.notas,
    )
    resultado = controller.actualizar_estado_oportunidad(dto)
    return APIResponseDTO[OportunidadDTO](success=True, data=resultado)


@router.post(
    "/oportunidades/{id}/interacciones",
    response_model=APIResponseDTO[InteraccionDTO],
    status_code=201,
    summary="Registrar interacción en una postulación",
    description="Registra un contacto, llamada, correo o entrevista de seguimiento.",
)
async def registrar_interaccion(
    id: int,
    dto: RegistrarInteraccionDTO,
    controller: Annotated[EmpleoController, Depends(get_empleo_controller)],
) -> APIResponseDTO[InteraccionDTO]:
    """Registra una interacción asociada a la oportunidad."""
    dto_con_id = dto.model_copy(update={"oportunidad_id": id})
    resultado = controller.registrar_interaccion(dto_con_id)
    return APIResponseDTO[InteraccionDTO](success=True, data=resultado)


@router.get(
    "/oportunidades/{id}/interacciones",
    response_model=APIResponseDTO[list[InteraccionDTO]],
    summary="Listar interacciones de una postulación",
    description="Devuelve el historial de contactos y avances registrados para la oportunidad.",
)
async def listar_interacciones(
    id: int,
    controller: Annotated[EmpleoController, Depends(get_empleo_controller)],
) -> APIResponseDTO[list[InteraccionDTO]]:
    """Lista las interacciones asociadas a la oportunidad."""
    resultado = controller.listar_interacciones(oportunidad_id=id)
    return APIResponseDTO[list[InteraccionDTO]](success=True, data=resultado)
