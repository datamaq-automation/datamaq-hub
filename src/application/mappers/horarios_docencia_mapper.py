"""Mapper para transformar entre DTOs y Entidades del subdominio horarios_docencia."""

from src.application.dtos.horarios_docencia_dto import (
    ConflictoDTO,
    DeclaracionHorariaInputDTO,
    ItemGrillaDiaDTO,
    ResultadoCompatibilidadDTO,
)
from src.domain.horarios_docencia.entities import (
    CargoDocente,
    DeclaracionHorariaDocente,
    HorarioBloque,
    ResultadoCompatibilidad,
)
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    SituacionRevista,
    Turno,
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
                # Normalizar dia
                dia_enum = DiaSemana[h_dto.dia.strip().upper()]
                # Normalizar turno
                turno_str = h_dto.turno.strip().upper()
                turno_enum = (
                    Turno[turno_str] if turno_str in Turno.__members__ else Turno.MANANA
                )
                franja = FranjaHoraria(
                    hora_inicio=h_dto.hora_inicio.strip(),
                    hora_fin=h_dto.hora_fin.strip(),
                )
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
                    modulos=c_dto.modulos,
                    es_cargo_base=c_dto.es_cargo_base,
                    horarios=tuple(horarios_dominio),
                )
            )

        return DeclaracionHorariaDocente(
            docente_nombre=dto.docente_nombre.strip(),
            cuit=dto.cuit.strip(),
            dni=dto.dni.strip(),
            cargos=tuple(cargos_dominio),
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
            conflictos=conflictos_dto,
            grilla_semanal=grilla_dto,
        )
