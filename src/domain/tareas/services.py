import uuid
from typing import Any

from src.domain.recibos.entities import (
    EstadoLineaConciliacion,
    ResultadoConciliacion,
)
from src.domain.tareas.entities import Tarea
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)


class GeneradorTareasReciboService:
    """Genera tareas inteligentes a partir de los resultados de conciliación de recibos."""

    @classmethod
    def generar_tareas_desde_conciliacion(
        cls,
        conciliacion: ResultadoConciliacion,
    ) -> list[Tarea]:
        tareas: list[Tarea] = []

        # 1. Tareas por cargos vigentes no cobrados en el mes
        for d in conciliacion.designaciones_no_cobradas:
            titulo = (
                f"Reclamar liquidación: {d.escuela_codigo} ({d.modulos_designacion} hs)"
            )
            descripcion = (
                f"El cargo en {d.escuela_codigo} ({d.modulos_designacion} módulos, revista {d.revista_designacion}) "
                f"estaba vigente durante el mes {conciliacion.mes_pago}, pero no figura liquidado en el recibo {conciliacion.id_recibo}."
            )
            meta: dict[str, Any] = {
                "id_designacion": d.id_designacion,
                "escuela_codigo": d.escuela_codigo,
                "modulos": d.modulos_designacion,
                "mes_pago": conciliacion.mes_pago,
                "id_recibo": conciliacion.id_recibo,
            }
            tarea = Tarea(
                id_tarea=str(uuid.uuid4()),
                titulo=titulo,
                descripcion=descripcion,
                fecha_limite=None,
                prioridad=PrioridadTarea.ALTA,
                estado=EstadoTarea.PENDIENTE,
                categoria=CategoriaTarea.RECIBOS,
                docente_cuit=conciliacion.docente_cuit,
                id_referencia=conciliacion.id_recibo,
                tipo_referencia="RECIBO",
                tags=("reclamo", "sueldo_no_liquidado", f"mes:{conciliacion.mes_pago}"),
                metadatos=meta,
            )
            tareas.append(tarea)

        # 2. Tareas por discrepancias en módulos o datos
        for l in conciliacion.lineas_conciliadas:
            if l.estado == EstadoLineaConciliacion.DISCREPANCIA:
                titulo = (
                    f"Verificar discrepancia en {l.escuela_codigo}: "
                    f"Recibo ({l.modulos_recibo} hs) vs Designación ({l.modulos_designacion} hs)"
                )
                descripcion = (
                    f"En la secuencia {l.secuencia} de {l.escuela_codigo}, se liquidaron {l.modulos_recibo} módulos, "
                    f"mientras que en el sistema figuran {l.modulos_designacion} módulos. Observación: {l.observacion}"
                )
                meta_l: dict[str, Any] = {
                    "id_designacion": l.id_designacion,
                    "secuencia": l.secuencia,
                    "escuela_codigo": l.escuela_codigo,
                    "modulos_recibo": l.modulos_recibo,
                    "modulos_designacion": l.modulos_designacion,
                    "id_recibo": conciliacion.id_recibo,
                }
                tarea = Tarea(
                    id_tarea=str(uuid.uuid4()),
                    titulo=titulo,
                    descripcion=descripcion,
                    fecha_limite=None,
                    prioridad=PrioridadTarea.MEDIA,
                    estado=EstadoTarea.PENDIENTE,
                    categoria=CategoriaTarea.RECIBOS,
                    docente_cuit=conciliacion.docente_cuit,
                    id_referencia=conciliacion.id_recibo,
                    tipo_referencia="RECIBO",
                    tags=("discrepancia", "modulos", f"mes:{conciliacion.mes_pago}"),
                    metadatos=meta_l,
                )
                tareas.append(tarea)

        return tareas
