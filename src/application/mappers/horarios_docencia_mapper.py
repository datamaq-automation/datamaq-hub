"""Mapper para transformar entre DTOs y Entidades del subdominio horarios_docencia."""

import uuid
from datetime import date

from src.application.dtos.horarios_docencia_dto import (
    ConflictoDTO,
    DeclaracionHorariaInputDTO,
    DesignacionDocenteDTO,
    HorarioBloqueDTO,
    ItemGrillaDiaDTO,
    RegistrarDesignacionInputDTO,
    ResultadoCompatibilidadDTO,
)
from src.domain.horarios_docencia.entities import (
    CargoDocente,
    DeclaracionHorariaDocente,
    DesignacionDocente,
    HorarioBloque,
    ResultadoCompatibilidad,
)
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    PeriodoVigencia,
    SituacionRevista,
    Turno,
    inferir_turno,
    normalizar_cuit,
)


class HorariosDocenciaMapper:
    """Mapeador bidireccional entre DTOs y Entidades de Dominio."""

    @staticmethod
    def to_domain(dto: DeclaracionHorariaInputDTO) -> DeclaracionHorariaDocente:
        """Convierte DeclaracionHorariaInputDTO a la entidad de dominio DeclaracionHorariaDocente."""
        cargos_dominio: list[CargoDocente] = []

        for c_dto in dto.cargos:
            horarios_dominio: list[HorarioBloque] = []
            for h_dto in c_dto.horarios:
                dia_enum = DiaSemana[h_dto.dia.strip().upper()]
                franja = FranjaHoraria(
                    hora_inicio=h_dto.hora_inicio.strip(),
                    hora_fin=h_dto.hora_fin.strip(),
                )
                if h_dto.turno and h_dto.turno.strip().upper() in Turno.__members__:
                    turno_enum = Turno[h_dto.turno.strip().upper()]
                else:
                    turno_enum = inferir_turno(franja)

                horarios_dominio.append(
                    HorarioBloque(
                        dia=dia_enum,
                        franja=franja,
                        turno=turno_enum,
                    )
                )

            revista_str = c_dto.revista.strip().upper()
            revista_enum = (
                SituacionRevista[revista_str]
                if revista_str in SituacionRevista.__members__
                else SituacionRevista.TITULAR
            )

            cargos_dominio.append(
                CargoDocente(
                    id_cargo=c_dto.id_cargo.strip(),
                    establecimiento=c_dto.establecimiento.strip(),
                    distrito=c_dto.distrito.strip(),
                    cargo_asignatura=c_dto.cargo_asignatura.strip(),
                    revista=revista_enum,
                    ige=c_dto.ige.strip(),
                    modulos=c_dto.modulos,
                    es_cargo_base=c_dto.es_cargo_base,
                    cupof=c_dto.cupof.strip(),
                    secuencia=c_dto.secuencia,
                    observaciones=c_dto.observaciones.strip(),
                    escuela_numero=c_dto.escuela_numero.strip(),
                    horarios=tuple(horarios_dominio),
                )
            )

        return DeclaracionHorariaDocente(
            docente_nombre=dto.docente_nombre.strip(),
            cuit=normalizar_cuit(dto.cuit),
            dni=dto.dni.strip(),
            cargos=tuple(cargos_dominio),
        )

    @staticmethod
    def to_designacion_domain(dto: RegistrarDesignacionInputDTO) -> DesignacionDocente:
        """Convierte RegistrarDesignacionInputDTO a la entidad temporal DesignacionDocente."""
        horarios_dominio: list[HorarioBloque] = []
        for h_dto in dto.horarios:
            dia_enum = DiaSemana[h_dto.dia.strip().upper()]
            franja = FranjaHoraria(
                hora_inicio=h_dto.hora_inicio.strip(),
                hora_fin=h_dto.hora_fin.strip(),
            )
            if h_dto.turno and h_dto.turno.strip().upper() in Turno.__members__:
                turno_enum = Turno[h_dto.turno.strip().upper()]
            else:
                turno_enum = inferir_turno(franja)

            horarios_dominio.append(
                HorarioBloque(
                    dia=dia_enum,
                    franja=franja,
                    turno=turno_enum,
                )
            )

        revista_str = dto.revista.strip().upper()
        revista_enum = (
            SituacionRevista[revista_str]
            if revista_str in SituacionRevista.__members__
            else SituacionRevista.TITULAR
        )

        f_desde = date.fromisoformat(dto.fecha_desde.strip())
        f_hasta = (
            date.fromisoformat(dto.fecha_hasta.strip()) if dto.fecha_hasta else None
        )

        return DesignacionDocente(
            id_designacion=str(uuid.uuid4()),
            docente_cuit=normalizar_cuit(dto.docente_cuit),
            ige=dto.ige.strip(),
            establecimiento=dto.establecimiento.strip(),
            distrito=dto.distrito.strip(),
            cargo_asignatura=dto.cargo_asignatura.strip(),
            revista=revista_enum,
            vigencia=PeriodoVigencia(fecha_desde=f_desde, fecha_hasta=f_hasta),
            modulos=dto.modulos,
            es_cargo_base=dto.es_cargo_base,
            observaciones=dto.observaciones.strip(),
            cupof=dto.cupof.strip(),
            secuencia=dto.secuencia,
            codigo_acto=dto.codigo_acto.strip(),
            escuela_numero=dto.escuela_numero.strip(),
            reemplaza_a=dto.reemplaza_a.strip(),
            articulo_licencia=dto.articulo_licencia.strip(),
            horarios=tuple(horarios_dominio),
        )

    @staticmethod
    def designacion_to_dto(domain: DesignacionDocente) -> DesignacionDocenteDTO:
        """Convierte una entidad DesignacionDocente a DesignacionDocenteDTO."""
        horarios_dto = [
            HorarioBloqueDTO(
                dia=h.dia.value,
                hora_inicio=h.franja.hora_inicio,
                hora_fin=h.franja.hora_fin,
                turno=h.turno.value,
            )
            for h in domain.horarios
        ]

        return DesignacionDocenteDTO(
            id_designacion=domain.id_designacion,
            docente_cuit=domain.docente_cuit,
            ige=domain.ige,
            establecimiento=domain.establecimiento,
            distrito=domain.distrito,
            cargo_asignatura=domain.cargo_asignatura,
            revista=domain.revista.value,
            modulos=domain.modulos,
            es_cargo_base=domain.es_cargo_base,
            fecha_desde=domain.vigencia.fecha_desde.isoformat(),
            fecha_hasta=(
                domain.vigencia.fecha_hasta.isoformat()
                if domain.vigencia.fecha_hasta
                else None
            ),
            motivo_cese=domain.motivo_cese.value if domain.motivo_cese else None,
            observaciones=domain.observaciones,
            cupof=domain.cupof,
            secuencia=domain.secuencia,
            codigo_acto=domain.codigo_acto,
            escuela_numero=domain.escuela_numero,
            reemplaza_a=domain.reemplaza_a,
            articulo_licencia=domain.articulo_licencia,
            horarios=horarios_dto,
            creado_en=domain.creado_en.isoformat(),
        )

    @staticmethod
    def to_dto(domain: ResultadoCompatibilidad) -> ResultadoCompatibilidadDTO:
        """Convierte la entidad ResultadoCompatibilidad a ResultadoCompatibilidadDTO."""
        conflictos_dto: list[ConflictoDTO] = [
            ConflictoDTO(
                tipo=c.tipo.value,
                severidad=c.severidad.value,
                dia=c.dia.value if c.dia else None,
                cargos_involucrados=list(c.cargos_involucrados),
                descripcion=c.descripcion,
                minutos_solapamiento_o_traslado=c.minutos_solapamiento_o_traslado,
            )
            for c in domain.conflictos
        ]

        grilla_dto: dict[str, list[ItemGrillaDiaDTO]] = {}
        for dia_str, items in domain.grilla_semanal.items():
            grilla_dto[dia_str] = [
                ItemGrillaDiaDTO(
                    id_cargo=item.id_cargo,
                    establecimiento=item.establecimiento,
                    distrito=item.distrito,
                    cargo_asignatura=item.cargo_asignatura,
                    revista=item.revista.value,
                    hora_inicio=item.franja.hora_inicio,
                    hora_fin=item.franja.hora_fin,
                    turno=item.turno.value,
                    modulos=item.modulos,
                    ige=item.ige,
                )
                for item in items
            ]

        return ResultadoCompatibilidadDTO(
            es_compatible=domain.es_compatible,
            total_cargos=domain.total_cargos,
            total_cargos_base=domain.total_cargos_base,
            total_modulos=domain.total_modulos,
            total_minutos_semanales=domain.total_minutos_semanales,
            cantidad_conflictos=domain.cantidad_conflictos,
            cantidad_incompatibilidades=domain.cantidad_incompatibilidades,
            cantidad_advertencias=domain.cantidad_advertencias,
            tiene_advertencias=domain.tiene_advertencias,
            conflictos=conflictos_dto,
            grilla_semanal=grilla_dto,
        )
