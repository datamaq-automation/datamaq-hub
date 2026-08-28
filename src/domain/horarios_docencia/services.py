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
                        ige=cargo.ige,
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

        # Validación de consistencia módulos vs minutos de bloques
        for cargo in declaracion.cargos:
            if cargo.modulos > 0 and cargo.horarios:
                duracion_bloques = sum(
                    h.franja.duracion_minutos() for h in cargo.horarios
                )
                minutos_esperados_60 = cargo.modulos * 60
                minutos_esperados_40 = cargo.modulos * 40
                minutos_esperados_45 = cargo.modulos * 45

                if (
                    duracion_bloques != minutos_esperados_60
                    and duracion_bloques != minutos_esperados_40
                    and duracion_bloques != minutos_esperados_45
                ):
                    promedio_min = duracion_bloques / cargo.modulos
                    conflictos.append(
                        ConflictoHorario(
                            tipo=TipoConflicto.DESVIO_DURACION_MODULO,
                            severidad=NivelSeveridad.ADVERTENCIA,
                            dia=None,
                            cargos_involucrados=(cargo.id_cargo,),
                            descripcion=(
                                f"El cargo '{cargo.cargo_asignatura}' ({cargo.establecimiento}) declara {cargo.modulos} módulos "
                                f"pero sus bloques suman {duracion_bloques} min semanales ({promedio_min:.1f} min/módulo)."
                            ),
                            minutos_solapamiento_o_traslado=abs(
                                duracion_bloques - minutos_esperados_60
                            ),
                        )
                    )

        if total_modulos > tope_modulos_semanales:
            conflictos.append(
                ConflictoHorario(
                    tipo=TipoConflicto.EXCESO_MODULOS_SEMANALES,
                    severidad=NivelSeveridad.ADVERTENCIA,
                    dia=None,
                    cargos_involucrados=(),
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
                    cargos_involucrados=(),
                    descripcion=(
                        f"El docente declara {total_cargos_base} cargos de base, superando el límite "
                        f"estatutario regular de {tope_cargos_base} cargos."
                    ),
                    minutos_solapamiento_o_traslado=0,
                )
            )

        # 4. Determinación de Compatibilidad y métricas discriminadas
        cant_incompatibilidades = sum(
            1 for c in conflictos if c.severidad == NivelSeveridad.CRITICO
        )
        cant_advertencias = sum(
            1 for c in conflictos if c.severidad == NivelSeveridad.ADVERTENCIA
        )
        es_compatible = cant_incompatibilidades == 0

        return ResultadoCompatibilidad(
            es_compatible=es_compatible,
            total_cargos=total_cargos,
            total_cargos_base=total_cargos_base,
            total_modulos=total_modulos,
            total_minutos_semanales=total_minutos_semanales,
            cantidad_conflictos=len(conflictos),
            cantidad_incompatibilidades=cant_incompatibilidades,
            cantidad_advertencias=cant_advertencias,
            tiene_advertencias=cant_advertencias > 0,
            conflictos=tuple(conflictos),
            grilla_semanal=dict(grilla_semanal),
        )
