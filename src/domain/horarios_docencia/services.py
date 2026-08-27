"""Servicios de dominio para la validación de compatibilidad horaria docente."""

from collections import defaultdict

from src.domain.horarios_docencia.entities import (
    CargoDocente,
    ConflictoHorario,
    DeclaracionHorariaDocente,
    HorarioBloque,
    ItemGrillaDia,
    ResultadoCompatibilidad,
)
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    NivelSeveridad,
    TipoConflicto,
)


class ValidadorHorariosDocenciaService:
    """Servicio de dominio puro que analiza solapamientos, traslados y topes estatutarios."""

    def validar(
        self,
        declaracion: DeclaracionHorariaDocente,
        margen_traslado_minutos: int = 20,
        tope_modulos_semanales: int = 30,
        tope_cargos_base: int = 2,
    ) -> ResultadoCompatibilidad:
        """Audita una declaración horaria docente y retorna el resultado de compatibilidad."""
        conflictos: list[ConflictoHorario] = []
        grilla_semanal: dict[str, list[ItemGrillaDia]] = defaultdict(list)

        # 1. Indexar bloques por día con referencia al cargo
        bloques_por_dia: dict[DiaSemana, list[tuple[CargoDocente, HorarioBloque]]] = (
            defaultdict(list)
        )

        for cargo in declaracion.cargos:
            for horario in cargo.horarios:
                bloques_por_dia[horario.dia].append((cargo, horario))

        total_minutos_semanales = 0

        # 2. Ordenar y auditar superposiciones y traslados por día
        for dia in DiaSemana:
            items_dia = bloques_por_dia.get(dia, [])
            if not items_dia:
                continue

            # Ordenar cronológicamente por hora de inicio
            items_dia.sort(key=lambda x: x[1].franja.inicio_minutos())

            # Poblar grilla visual del día
            for cargo, horario in items_dia:
                total_minutos_semanales += horario.franja.duracion_minutos()
                grilla_semanal[dia.value].append(
                    ItemGrillaDia(
                        id_cargo=cargo.id_cargo,
                        establecimiento=cargo.establecimiento,
                        distrito=cargo.distrito,
                        cargo_asignatura=cargo.cargo_asignatura,
                        revista=cargo.revista,
                        franja=horario.franja,
                        turno=horario.turno,
                        modulos=cargo.modulos,
                    )
                )

            # Validar solapamientos y traslados entre todos los pares del día
            for i in range(len(items_dia)):
                cargo_a, horario_a = items_dia[i]
                for j in range(i + 1, len(items_dia)):
                    cargo_b, horario_b = items_dia[j]

                    # A. Superposición Horaria (Overlap estricto)
                    if horario_a.franja.se_superpone_con(horario_b.franja):
                        minutos_overlap = horario_a.franja.minutos_solapamiento(
                            horario_b.franja
                        )
                        conflictos.append(
                            ConflictoHorario(
                                tipo=TipoConflicto.SUPERPOSICION_HORARIA,
                                severidad=NivelSeveridad.CRITICO,
                                dia=dia,
                                cargos_involucrados=(
                                    cargo_a.id_cargo,
                                    cargo_b.id_cargo,
                                ),
                                descripcion=(
                                    f"Superposición horaria el {dia.value} entre "
                                    f"'{cargo_a.cargo_asignatura}' ({cargo_a.establecimiento}, {horario_a.franja.hora_inicio}-{horario_a.franja.hora_fin}) "
                                    f"y '{cargo_b.cargo_asignatura}' ({cargo_b.establecimiento}, {horario_b.franja.hora_inicio}-{horario_b.franja.hora_fin}) "
                                    f"por {minutos_overlap} minutos."
                                ),
                                minutos_solapamiento_o_traslado=minutos_overlap,
                            )
                        )
                    else:
                        # B. Traslado Insuficiente (si son consecutivos en el tiempo y de escuelas distintas)
                        if j == i + 1:
                            tiempo_entre = horario_a.franja.minutos_hasta(
                                horario_b.franja
                            )
                            escuela_a = cargo_a.establecimiento.strip().lower()
                            escuela_b = cargo_b.establecimiento.strip().lower()

                            if (
                                escuela_a != escuela_b
                                and 0 <= tiempo_entre < margen_traslado_minutos
                            ):
                                conflictos.append(
                                    ConflictoHorario(
                                        tipo=TipoConflicto.TRASLADO_INSUFICIENTE,
                                        severidad=NivelSeveridad.ADVERTENCIA,
                                        dia=dia,
                                        cargos_involucrados=(
                                            cargo_a.id_cargo,
                                            cargo_b.id_cargo,
                                        ),
                                        descripcion=(
                                            f"Margen de traslado insuficiente el {dia.value} entre "
                                            f"'{cargo_a.establecimiento}' (termina {horario_a.franja.hora_fin}) "
                                            f"y '{cargo_b.establecimiento}' (inicia {horario_b.franja.hora_inicio}): "
                                            f"{tiempo_entre} min disponibles (mínimo sugerido: {margen_traslado_minutos} min)."
                                        ),
                                        minutos_solapamiento_o_traslado=tiempo_entre,
                                    )
                                )

        # 3. Totales y reglas estatutarias
        total_cargos = len(declaracion.cargos)
        total_cargos_base = sum(1 for c in declaracion.cargos if c.es_cargo_base)
        total_modulos = sum(c.modulos for c in declaracion.cargos)

        if total_modulos > tope_modulos_semanales:
            conflictos.append(
                ConflictoHorario(
                    tipo=TipoConflicto.EXCESO_MODULOS_SEMANALES,
                    severidad=NivelSeveridad.ADVERTENCIA,
                    dia=None,
                    cargos_involucrados=tuple(c.id_cargo for c in declaracion.cargos),
                    descripcion=(
                        f"La suma total de {total_modulos} módulos semanales supera el límite "
                        f"regular estatutario de {tope_modulos_semanales} módulos."
                    ),
                    minutos_solapamiento_o_traslado=0,
                )
            )

        if total_cargos_base > tope_cargos_base:
            conflictos.append(
                ConflictoHorario(
                    tipo=TipoConflicto.EXCESO_CARGOS_BASE,
                    severidad=NivelSeveridad.ADVERTENCIA,
                    dia=None,
                    cargos_involucrados=tuple(
                        c.id_cargo for c in declaracion.cargos if c.es_cargo_base
                    ),
                    descripcion=(
                        f"El docente declara {total_cargos_base} cargos de base, superando el límite "
                        f"estatutario regular de {tope_cargos_base} cargos."
                    ),
                    minutos_solapamiento_o_traslado=0,
                )
            )

        # 4. Determinación de Compatibilidad
        # Es compatible si no tiene ningún conflicto CRITICO (superposiciones)
        es_compatible = not any(
            c.severidad == NivelSeveridad.CRITICO for c in conflictos
        )

        return ResultadoCompatibilidad(
            es_compatible=es_compatible,
            total_cargos=total_cargos,
            total_cargos_base=total_cargos_base,
            total_modulos=total_modulos,
            total_minutos_semanales=total_minutos_semanales,
            cantidad_conflictos=len(conflictos),
            conflictos=tuple(conflictos),
            grilla_semanal=dict(grilla_semanal),
        )
