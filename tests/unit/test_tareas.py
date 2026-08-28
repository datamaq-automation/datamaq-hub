"""Pruebas unitarias para el subdominio de tareas (To-Do List)."""

from datetime import date

import pytest

from src.adapters.gateways.sql_designacion_docente_gateway import (
    SQLDesignacionDocenteGateway,
)
from src.adapters.gateways.sql_recibo_gateway import SQLReciboGateway
from src.adapters.gateways.sql_tarea_gateway import SQLTareaGateway
from src.application.dtos.tarea_dtos import ActualizarTareaDTO, CrearTareaDTO
from src.application.use_cases.actualizar_tarea import ActualizarTareaUseCase
from src.application.use_cases.completar_tarea import CompletarTareaUseCase
from src.application.use_cases.crear_tarea import CrearTareaUseCase
from src.application.use_cases.eliminar_tarea import EliminarTareaUseCase
from src.application.use_cases.generar_tareas_desde_recibo import (
    GenerarTareasDesdeReciboUseCase,
)
from src.application.use_cases.listar_tareas import ListarTareasUseCase
from src.application.use_cases.obtener_tarea import ObtenerTareaUseCase
from src.domain.horarios_docencia.entities import DesignacionDocente
from src.domain.horarios_docencia.value_objects import PeriodoVigencia, SituacionRevista
from src.domain.recibos.entities import (
    Agente,
    CargoDetalle,
    Empleador,
    EstablecimientoDetalle,
    LiquidacionSecuencia,
    ReciboSueldo,
    ResumenLiquidoItem,
    TotalesConsolidados,
)
from src.domain.recibos.value_objects import TipoRecibo
from src.domain.tareas.entities import Tarea
from src.domain.tareas.exceptions import (
    TareaInvalidaException,
    TareaNoEncontradaException,
)
from src.domain.tareas.ports import FiltrosTarea
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)


def test_entidad_tarea_y_validaciones() -> None:
    # 1. Creación válida
    t = Tarea(
        id_tarea="tarea-1",
        titulo="Comprar insumos",
        descripcion="Tinta y papel",
        fecha_limite=date(2026, 9, 1),
        prioridad=PrioridadTarea.ALTA,
        categoria=CategoriaTarea.GENERAL,
        docente_cuit="20-36528392-4",
    )
    assert t.id_tarea == "tarea-1"
    assert t.titulo == "Comprar insumos"
    assert t.docente_cuit == "20365283924"
    assert t.estado == EstadoTarea.PENDIENTE
    assert t.fecha_completada is None

    # 2. Completar
    t_comp = t.completar()
    assert t_comp.estado == EstadoTarea.COMPLETADA
    assert t_comp.fecha_completada is not None

    # 3. Validaciones de error
    with pytest.raises(TareaInvalidaException, match="ID"):
        Tarea(id_tarea="", titulo="Válido")

    with pytest.raises(TareaInvalidaException, match="título"):
        Tarea(id_tarea="tarea-2", titulo="   ")

    with pytest.raises(TareaInvalidaException, match="250"):
        Tarea(id_tarea="tarea-3", titulo="A" * 251)


def test_sql_tarea_gateway_crud_y_filtros() -> None:
    gateway = SQLTareaGateway(database_url="sqlite:///:memory:")

    # 1. Guardar tareas
    t1 = Tarea(
        id_tarea="t-doc-1",
        titulo="Reclamar horas ISFDyT",
        prioridad=PrioridadTarea.ALTA,
        categoria=CategoriaTarea.DOCENCIA,
        docente_cuit="20365283924",
        fecha_limite=date(2026, 8, 30),
        tags=("docencia", "reclamo"),
    )
    t2 = Tarea(
        id_tarea="t-rec-2",
        titulo="Revisar recibo de julio",
        prioridad=PrioridadTarea.URGENTE,
        categoria=CategoriaTarea.RECIBOS,
        docente_cuit="20365283924",
        id_referencia="recibo-jul-26",
        fecha_limite=date(2026, 8, 25),
    )
    t3 = Tarea(
        id_tarea="t-gen-3",
        titulo="Actualizar servidor",
        prioridad=PrioridadTarea.BAJA,
        categoria=CategoriaTarea.GENERAL,
        estado=EstadoTarea.COMPLETADA,
    )

    gateway.guardar(t1)
    gateway.guardar(t2)
    gateway.guardar(t3)

    # 2. Obtener por ID
    recuperada = gateway.obtener_por_id("t-doc-1")
    assert recuperada is not None
    assert recuperada.titulo == "Reclamar horas ISFDyT"
    assert recuperada.tags == ("docencia", "reclamo")

    assert gateway.obtener_por_id("inexistente") is None

    # 3. Listar con filtros
    # Por estado
    pendientes = gateway.listar(FiltrosTarea(estado=EstadoTarea.PENDIENTE))
    assert len(pendientes) == 2

    # Por categoría
    recibos = gateway.listar(FiltrosTarea(categoria=CategoriaTarea.RECIBOS))
    assert len(recibos) == 1
    assert recibos[0].id_tarea == "t-rec-2"

    # Por CUIT
    docente_tareas = gateway.listar(FiltrosTarea(docente_cuit="20-36528392-4"))
    assert len(docente_tareas) == 2

    # Por ID referencia
    ref_tareas = gateway.listar(FiltrosTarea(id_referencia="recibo-jul-26"))
    assert len(ref_tareas) == 1

    # 4. Actualizar
    t1_mod = Tarea(
        id_tarea=t1.id_tarea,
        titulo="Reclamar horas ISFDyT - Actualizado",
        descripcion="Nueva descripción",
        prioridad=PrioridadTarea.URGENTE,
        estado=EstadoTarea.EN_PROGRESO,
        categoria=t1.categoria,
    )
    gateway.actualizar(t1_mod)
    recup_mod = gateway.obtener_por_id("t-doc-1")
    assert recup_mod is not None
    assert recup_mod.titulo == "Reclamar horas ISFDyT - Actualizado"
    assert recup_mod.estado == EstadoTarea.EN_PROGRESO
    assert recup_mod.prioridad == PrioridadTarea.URGENTE

    # 5. Eliminar
    assert gateway.eliminar("t-gen-3") is True
    assert gateway.obtener_por_id("t-gen-3") is None
    assert gateway.eliminar("inexistente") is False


def test_casos_de_uso_tareas_flujo_completo() -> None:
    gateway = SQLTareaGateway(database_url="sqlite:///:memory:")

    crear_uc = CrearTareaUseCase(gateway)
    obtener_uc = ObtenerTareaUseCase(gateway)
    listar_uc = ListarTareasUseCase(gateway)
    actualizar_uc = ActualizarTareaUseCase(gateway)
    completar_uc = CompletarTareaUseCase(gateway)
    eliminar_uc = EliminarTareaUseCase(gateway)

    # 1. Crear tarea
    dto_in = CrearTareaDTO(
        titulo="Preparar final de Inteligencia Artificial",
        descripcion="Temas: NLP y Modelos Secuenciales",
        prioridad=PrioridadTarea.ALTA,
        categoria=CategoriaTarea.DOCENCIA,
        fecha_limite=date(2026, 9, 15),
        tags=["ia", "finales"],
    )
    creada = crear_uc.execute(dto_in)
    assert creada.id_tarea is not None
    assert creada.titulo == "Preparar final de Inteligencia Artificial"
    assert creada.estado == EstadoTarea.PENDIENTE

    # 2. Obtener por ID
    obtenida = obtener_uc.execute(creada.id_tarea)
    assert obtenida.id_tarea == creada.id_tarea

    # 3. Listar
    listado = listar_uc.execute()
    assert listado.total == 1

    # 4. Actualizar
    actualizada = actualizar_uc.execute(
        creada.id_tarea,
        ActualizarTareaDTO(
            prioridad=PrioridadTarea.URGENTE, descripcion="Temas ampliados"
        ),
    )
    assert actualizada.prioridad == PrioridadTarea.URGENTE
    assert actualizada.descripcion == "Temas ampliados"

    # 5. Completar
    completada = completar_uc.execute(creada.id_tarea)
    assert completada.estado == EstadoTarea.COMPLETADA
    assert completada.fecha_completada is not None

    # 6. Eliminar
    assert eliminar_uc.execute(creada.id_tarea) is True
    with pytest.raises(TareaNoEncontradaException):
        obtener_uc.execute(creada.id_tarea)


def test_auto_generacion_tareas_desde_recibo() -> None:
    recibo_repo = SQLReciboGateway(database_url="sqlite:///:memory:")
    desig_repo = SQLDesignacionDocenteGateway(database_url="sqlite:///:memory:")
    tarea_repo = SQLTareaGateway(database_url="sqlite:///:memory:")

    # 1. Recibo de julio con una línea liquidada en ISFDyT 199 (7 hs)
    recibo = ReciboSueldo(
        id_recibo="recibo-test-tareas",
        tipo_recibo=TipoRecibo.DGCYE_PBA,
        empleador=Empleador(organismo_o_empresa="DGCyE PBA"),
        agente=Agente(
            nombre_completo="Docente Test",
            numero_documento="36528392",
            cuil="20-36528392-4",
            mes_pago="2026-07",
        ),
        liquidaciones=[
            LiquidacionSecuencia(
                establecimiento=EstablecimientoDetalle(
                    codigo="055 IS 0199", nombre="ISFDyT N°199"
                ),
                cargo=CargoDetalle(
                    secuencia="016",
                    situacion_revista="PROVISIONAL",
                    carga_horaria=7.0,
                    periodo_liquidado="202607",
                ),
                liquido_calculado=450000.0,
            )
        ],
        resumen_liquidos=[
            ResumenLiquidoItem(
                establecimiento_codigo="055 IS 0199",
                secuencia="016",
                periodo_liquidado="202607",
                fecha_pago="07/08/2026",
                orden_pago_codigo="001",
                orden_pago_descripcion="HABERES",
                liquido_pesos=450000.0,
            )
        ],
        totales=TotalesConsolidados(total_liquido=450000.0),
    )
    recibo_repo.guardar(recibo)

    # 2. Designaciones: Una activa que coincide (ISFDyT 199 7hs) y otra activa NO cobrada (EEST 3 2hs)
    desig_199 = DesignacionDocente(
        id_designacion="desig-199-7hs",
        docente_cuit="20365283924",
        establecimiento="ISFDyT N°199",
        distrito="TIGRE",
        escuela_numero="",
        secuencia="016",
        cargo_asignatura="Ciencias de Datos",
        revista=SituacionRevista.PROVISIONAL,
        modulos=7,
        vigencia=PeriodoVigencia(fecha_desde=date(2025, 9, 1), fecha_hasta=None),
    )
    desig_no_cobrada = DesignacionDocente(
        id_designacion="desig-eest3-no-cobrada",
        docente_cuit="20365283924",
        establecimiento="Tigre - EEST N°3",
        distrito="TIGRE",
        escuela_numero="3",
        secuencia="020",
        cargo_asignatura="LSO",
        revista=SituacionRevista.SUPLENTE,
        modulos=2,
        vigencia=PeriodoVigencia(fecha_desde=date(2026, 7, 1), fecha_hasta=None),
    )
    desig_repo.guardar(desig_199)
    desig_repo.guardar(desig_no_cobrada)

    # 3. Ejecutar auto-generación de tareas
    uc = GenerarTareasDesdeReciboUseCase(
        recibo_repository=recibo_repo,
        designacion_repository=desig_repo,
        tarea_repository=tarea_repo,
    )

    res = uc.execute("recibo-test-tareas")
    assert res.total_generadas == 1
    assert len(res.tareas) == 1

    tarea_gen = res.tareas[0]
    assert "Reclamar liquidación" in tarea_gen.titulo
    assert tarea_gen.categoria == CategoriaTarea.RECIBOS
    assert tarea_gen.prioridad == PrioridadTarea.ALTA
    assert tarea_gen.docente_cuit == "20365283924"
    assert tarea_gen.id_referencia == "recibo-test-tareas"
