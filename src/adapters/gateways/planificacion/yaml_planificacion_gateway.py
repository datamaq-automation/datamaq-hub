"""Gateway implementation for loading and updating project plans and PERT tasks from YAML files."""

from pathlib import Path
from typing import Any, cast

import yaml

from src.domain.planificacion.entities import EstimacionPert, TableroKanban, TareaPlan
from src.domain.planificacion.exceptions import (
    PlanNoEncontradoError,
    TareaPlanInvalidaError,
    TareaPlanNoEncontradaError,
)
from src.domain.planificacion.ports import PlanificacionRepositoryPort
from src.domain.planificacion.services import CalculadorPertCpmService
from src.domain.planificacion.value_objects import EstadoTareaPlan


class YamlPlanificacionGateway(PlanificacionRepositoryPort):
    """Carga, recalcula y persiste redes de planificación y tableros Kanban desde archivos YAML."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            # Default a data/pert/ relativo a la raíz del repositorio
            self._data_dir = Path(__file__).resolve().parents[4] / "data" / "pert"
        else:
            self._data_dir = data_dir
        self._cache: dict[str, TableroKanban] = {}

    def _resolver_ruta_archivo(self, id_plan: str) -> Path:
        clean_id = id_plan.strip().lower().removesuffix(".yaml").removesuffix(".yml")
        # Si clean_id es 'vaca_muerta', admitir 'camino_critico_vaca_muerta' si el directo no existe
        candidatos = [
            self._data_dir / f"{clean_id}.yaml",
            self._data_dir / f"{clean_id}.yml",
            self._data_dir / f"camino_critico_{clean_id}.yaml",
            self._data_dir / f"camino_critico_{clean_id}.yml",
        ]
        for p in candidatos:
            if p.exists():
                return p
        raise PlanNoEncontradoError(
            f"No se encontró el archivo de planificación para el plan '{id_plan}' en {self._data_dir}"
        )

    def obtener_tablero(self, id_plan: str = "vaca_muerta") -> TableroKanban:
        """Carga el plan desde el archivo YAML, calcula métricas PERT-CPM y retorna el TableroKanban."""
        clean_id = id_plan.strip().lower()
        if clean_id in self._cache:
            return self._cache[clean_id]

        archivo = self._resolver_ruta_archivo(clean_id)

        try:
            content = archivo.read_text(encoding="utf-8")
            raw_data: Any = yaml.safe_load(content)
            data: dict[str, Any] = (
                cast(dict[str, Any], raw_data) if isinstance(raw_data, dict) else {}
            )
        except Exception as exc:
            raise TareaPlanInvalidaError(
                f"Error al leer o parsear el archivo de planificación {archivo}: {exc}"
            ) from exc

        id_plan_doc = str(data.get("id_plan", clean_id))
        titulo_plan = str(data.get("titulo", "Plan de Proyecto"))
        descripcion_plan = str(data.get("descripcion", ""))

        raw_tareas: Any = data.get("tareas")
        tareas_list: list[Any] = (
            cast(list[Any], raw_tareas) if isinstance(raw_tareas, list) else []
        )

        tareas_parsed: list[TareaPlan] = []
        for t_item in tareas_list:
            if not isinstance(t_item, dict):
                continue
            dict_item: dict[str, Any] = cast(dict[str, Any], t_item)
            t_id = str(dict_item.get("id", "")).strip()
            if not t_id:
                continue

            titulo = str(dict_item.get("titulo", "")).strip()
            descripcion = str(dict_item.get("descripcion", "")).strip()
            fase = str(dict_item.get("fase", "")).strip()
            responsable = str(dict_item.get("responsable", "")).strip()

            raw_estado = str(dict_item.get("estado", "PENDIENTE")).strip().upper()
            try:
                estado = EstadoTareaPlan(raw_estado)
            except ValueError:
                estado = EstadoTareaPlan.PENDIENTE

            raw_preds: Any = dict_item.get("predecesores")
            preds_list: list[Any] = (
                cast(list[Any], raw_preds) if isinstance(raw_preds, list) else []
            )
            predecesores = tuple(str(p).strip() for p in preds_list if str(p).strip())

            try:
                opt = float(t_item.get("optimista", 1.0))
                mas_prob = float(t_item.get("mas_probable", opt))
                pes = float(t_item.get("pesimista", mas_prob))
            except (ValueError, TypeError) as exc:
                raise TareaPlanInvalidaError(
                    f"Valores numéricos de estimación inválidos para la tarea '{t_id}': {exc}"
                ) from exc

            estimacion = EstimacionPert(
                optimista=opt,
                mas_probable=mas_prob,
                pesimista=pes,
            )

            tarea = TareaPlan(
                id=t_id,
                titulo=titulo,
                descripcion=descripcion,
                fase=fase,
                estado=estado,
                predecesores=predecesores,
                estimacion=estimacion,
                responsable=responsable,
            )
            tareas_parsed.append(tarea)

        tablero = CalculadorPertCpmService.calcular_tablero(
            id_plan=id_plan_doc,
            titulo_plan=titulo_plan,
            descripcion_plan=descripcion_plan,
            tareas_raw=tareas_parsed,
        )

        self._cache[clean_id] = tablero
        return tablero

    def actualizar_estado_tarea(
        self,
        id_tarea: str,
        nuevo_estado: EstadoTareaPlan,
        id_plan: str = "vaca_muerta",
    ) -> TableroKanban:
        """Actualiza el estado de una tarea en el archivo YAML y retorna el tablero recalculado."""
        clean_id = id_plan.strip().lower()
        archivo = self._resolver_ruta_archivo(clean_id)

        try:
            content = archivo.read_text(encoding="utf-8")
            raw_data: Any = yaml.safe_load(content)
            data: dict[str, Any] = (
                cast(dict[str, Any], raw_data) if isinstance(raw_data, dict) else {}
            )
        except Exception as exc:
            raise TareaPlanInvalidaError(
                f"Error al leer archivo {archivo}: {exc}"
            ) from exc

        raw_tareas: Any = data.get("tareas")
        tareas_list: list[Any] = (
            cast(list[Any], raw_tareas) if isinstance(raw_tareas, list) else []
        )

        encontrada = False
        target_id = id_tarea.strip()

        for t_item in tareas_list:
            if (
                isinstance(t_item, dict)
                and str(t_item.get("id", "")).strip() == target_id
            ):
                t_item["estado"] = nuevo_estado.value
                encontrada = True
                break

        if not encontrada:
            raise TareaPlanNoEncontradaError(
                f"No se encontró la tarea con ID '{id_tarea}' en el plan '{id_plan}'"
            )

        # Escribir nuevamente el archivo YAML preservando formato legible
        archivo.write_text(
            yaml.dump(
                data, allow_unicode=True, sort_keys=False, default_flow_style=False
            ),
            encoding="utf-8",
        )

        # Invalidar caché
        self._cache.pop(clean_id, None)

        return self.obtener_tablero(clean_id)
