"""Caso de uso para modificar o corregir una designación docente existente."""

from datetime import date

from src.application.dtos.horarios_docencia_dto import (
    ActualizarDesignacionInputDTO,
    DesignacionDocenteDTO,
)
from src.application.mappers.horarios_docencia_mapper import HorariosDocenciaMapper
from src.domain.horarios_docencia.entities import (
    DesignacionDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.ports import DesignacionDocenteRepositoryPort
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    MotivoCese,
    PeriodoVigencia,
    SituacionRevista,
    Turno,
    inferir_turno,
    normalizar_cuit,
)


class ActualizarDesignacionUseCase:
    """Orquesta la modificación de una designación docente existente."""

    def __init__(self, repository: DesignacionDocenteRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self, id_designacion: str, input_dto: ActualizarDesignacionInputDTO
    ) -> DesignacionDocenteDTO | None:
        """Aplica los cambios solicitados sobre la designación existente."""
        existente = self._repository.obtener_por_id(id_designacion.strip())
        if not existente:
            return None

        docente_cuit = (
            normalizar_cuit(input_dto.docente_cuit)
            if input_dto.docente_cuit is not None
            else existente.docente_cuit
        )
        ige = input_dto.ige.strip() if input_dto.ige is not None else existente.ige
        establecimiento = (
            input_dto.establecimiento.strip()
            if input_dto.establecimiento is not None
            else existente.establecimiento
        )
        distrito = (
            input_dto.distrito.strip()
            if input_dto.distrito is not None
            else existente.distrito
        )
        cargo_asignatura = (
            input_dto.cargo_asignatura.strip()
            if input_dto.cargo_asignatura is not None
            else existente.cargo_asignatura
        )

        revista = existente.revista
        if input_dto.revista is not None:
            r_str = input_dto.revista.strip().upper()
            if r_str in SituacionRevista.__members__:
                revista = SituacionRevista[r_str]

        modulos = (
            input_dto.modulos if input_dto.modulos is not None else existente.modulos
        )
        es_cargo_base = (
            input_dto.es_cargo_base
            if input_dto.es_cargo_base is not None
            else existente.es_cargo_base
        )

        f_desde = (
            date.fromisoformat(input_dto.fecha_desde.strip())
            if input_dto.fecha_desde is not None
            else existente.vigencia.fecha_desde
        )
        f_hasta = (
            date.fromisoformat(input_dto.fecha_hasta.strip())
            if input_dto.fecha_hasta is not None
            else existente.vigencia.fecha_hasta
        )

        motivo_cese = existente.motivo_cese
        if input_dto.motivo_cese is not None:
            m_str = input_dto.motivo_cese.strip().upper()
            motivo_cese = MotivoCese[m_str] if m_str in MotivoCese.__members__ else None

        observaciones = (
            input_dto.observaciones.strip()
            if input_dto.observaciones is not None
            else existente.observaciones
        )
        cupof = (
            input_dto.cupof.strip() if input_dto.cupof is not None else existente.cupof
        )
        secuencia = (
            input_dto.secuencia
            if input_dto.secuencia is not None
            else existente.secuencia
        )
        codigo_acto = (
            input_dto.codigo_acto.strip()
            if input_dto.codigo_acto is not None
            else existente.codigo_acto
        )
        escuela_numero = (
            input_dto.escuela_numero.strip()
            if input_dto.escuela_numero is not None
            else existente.escuela_numero
        )
        reemplaza_a = (
            input_dto.reemplaza_a.strip()
            if input_dto.reemplaza_a is not None
            else existente.reemplaza_a
        )
        articulo_licencia = (
            input_dto.articulo_licencia.strip()
            if input_dto.articulo_licencia is not None
            else existente.articulo_licencia
        )

        horarios = existente.horarios
        if input_dto.horarios is not None:
            nuevos_horarios: list[HorarioBloque] = []
            for h_dto in input_dto.horarios:
                dia_enum = DiaSemana[h_dto.dia.strip().upper()]
                franja = FranjaHoraria(
                    hora_inicio=h_dto.hora_inicio.strip(),
                    hora_fin=h_dto.hora_fin.strip(),
                )
                if h_dto.turno and h_dto.turno.strip().upper() in Turno.__members__:
                    turno_enum = Turno[h_dto.turno.strip().upper()]
                else:
                    turno_enum = inferir_turno(franja)

                nuevos_horarios.append(
                    HorarioBloque(
                        dia=dia_enum,
                        franja=franja,
                        turno=turno_enum,
                    )
                )
            horarios = tuple(nuevos_horarios)

        updated_domain = DesignacionDocente(
            id_designacion=existente.id_designacion,
            docente_cuit=docente_cuit,
            ige=ige,
            establecimiento=establecimiento,
            distrito=distrito,
            cargo_asignatura=cargo_asignatura,
            revista=revista,
            vigencia=PeriodoVigencia(fecha_desde=f_desde, fecha_hasta=f_hasta),
            modulos=modulos,
            es_cargo_base=es_cargo_base,
            horarios=horarios,
            motivo_cese=motivo_cese,
            observaciones=observaciones,
            cupof=cupof,
            secuencia=secuencia,
            codigo_acto=codigo_acto,
            escuela_numero=escuela_numero,
            reemplaza_a=reemplaza_a,
            articulo_licencia=articulo_licencia,
            creado_en=existente.creado_en,
        )

        guardada = self._repository.actualizar(updated_domain)
        return HorariosDocenciaMapper.designacion_to_dto(guardada) if guardada else None
