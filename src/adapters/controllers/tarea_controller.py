"""Controlador agnóstico de framework para el subdominio de tareas."""

from typing import Any

from src.adapters.presenters.tarea_presenter import TareaPresenter
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.tarea_dtos import (
    ActualizarTareaDTO,
    CrearTareaDTO,
    GenerarTareasReciboResponseDTO,
    ListarTareasResponseDTO,
    TareaResponseDTO,
)
from src.application.use_cases.actualizar_tarea import ActualizarTareaUseCase
from src.application.use_cases.completar_tarea import CompletarTareaUseCase
from src.application.use_cases.crear_tarea import CrearTareaUseCase
from src.application.use_cases.eliminar_tarea import EliminarTareaUseCase
from src.application.use_cases.generar_tareas_desde_recibo import (
    GenerarTareasDesdeReciboUseCase,
)
from src.application.use_cases.listar_tareas import ListarTareasUseCase
from src.application.use_cases.obtener_tarea import ObtenerTareaUseCase
from src.domain.tareas.ports import FiltrosTarea


class TareaController:
    """Controlador que orquesta los casos de uso de tareas independientemente del transporte."""

    def __init__(
        self,
        crear_use_case: CrearTareaUseCase,
        obtener_use_case: ObtenerTareaUseCase,
        listar_use_case: ListarTareasUseCase,
        actualizar_use_case: ActualizarTareaUseCase,
        completar_use_case: CompletarTareaUseCase,
        eliminar_use_case: EliminarTareaUseCase,
        generar_desde_recibo_use_case: GenerarTareasDesdeReciboUseCase,
    ) -> None:
        self._crear_use_case = crear_use_case
        self._obtener_use_case = obtener_use_case
        self._listar_use_case = listar_use_case
        self._actualizar_use_case = actualizar_use_case
        self._completar_use_case = completar_use_case
        self._eliminar_use_case = eliminar_use_case
        self._generar_desde_recibo_use_case = generar_desde_recibo_use_case

    def crear(self, dto: CrearTareaDTO) -> APIResponseDTO[TareaResponseDTO]:
        res = self._crear_use_case.execute(dto)
        return TareaPresenter.present_tarea(res)

    def obtener_por_id(self, id_tarea: str) -> APIResponseDTO[TareaResponseDTO]:
        res = self._obtener_use_case.execute(id_tarea)
        return TareaPresenter.present_tarea(res)

    def listar(
        self, filtros: FiltrosTarea | None = None
    ) -> APIResponseDTO[ListarTareasResponseDTO]:
        res = self._listar_use_case.execute(filtros)
        return TareaPresenter.present_listado(res)

    def actualizar(
        self, id_tarea: str, dto: ActualizarTareaDTO
    ) -> APIResponseDTO[TareaResponseDTO]:
        res = self._actualizar_use_case.execute(id_tarea, dto)
        return TareaPresenter.present_tarea(res)

    def completar(self, id_tarea: str) -> APIResponseDTO[TareaResponseDTO]:
        res = self._completar_use_case.execute(id_tarea)
        return TareaPresenter.present_tarea(res)

    def eliminar(self, id_tarea: str) -> APIResponseDTO[dict[str, Any]]:
        self._eliminar_use_case.execute(id_tarea)
        return TareaPresenter.present_eliminacion(id_tarea)

    def generar_desde_recibo(
        self, id_recibo: str
    ) -> APIResponseDTO[GenerarTareasReciboResponseDTO]:
        res = self._generar_desde_recibo_use_case.execute(id_recibo)
        return TareaPresenter.present_generadas(res)
