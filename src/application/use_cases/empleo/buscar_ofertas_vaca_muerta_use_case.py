"""Use case for searching and ranking job opportunities in Vaca Muerta."""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from src.application.dtos.empleo_dtos import (
    BuscarOfertasQueryDTO,
    ResultadoBusquedaDTO,
)
from src.application.mappers.empleo_mapper import EmpleoMapper
from src.domain.empleo.entities import (
    OfertaLaboral,
    ResultadoBusquedaEmpleo,
    obtener_perfil_agustin_bustos,
)
from src.domain.empleo.ports import OfertasCachePort, PortalEmpleoPort
from src.domain.empleo.services import (
    FiltroVacaMuertaService,
    ScoringOfertasService,
)
from src.domain.empleo.value_objects import (
    FuenteOferta,
)

# Perfil predeterminado configurado según el perfil profesional de Agustín Leonardo Bustos
PERFIL_DEFAULT = obtener_perfil_agustin_bustos()


class BuscarOfertasVacaMuertaUseCase:
    """Caso de uso orquestador para consultar portales y ponderar vacantes de Vaca Muerta."""

    def __init__(
        self,
        portales: list[PortalEmpleoPort],
        cache: OfertasCachePort | None = None,
        filtro_vaca_muerta: FiltroVacaMuertaService | None = None,
        scoring_service: ScoringOfertasService | None = None,
    ) -> None:
        self._portales = portales
        self._cache = cache
        self._filtro_vaca_muerta = filtro_vaca_muerta or FiltroVacaMuertaService()
        self._scoring_service = scoring_service or ScoringOfertasService()

    def execute(self, query: BuscarOfertasQueryDTO) -> ResultadoBusquedaDTO:
        """Ejecuta la búsqueda multifuente, filtra por Vaca Muerta y puntúa según perfil."""
        cache_key = f"empleo_vm:{':'.join(sorted(query.palabras_clave))}:{query.ubicacion}:{query.solo_vaca_muerta}"

        ofertas_recuperadas: list[OfertaLaboral] | None = None
        if self._cache:
            ofertas_recuperadas = self._cache.obtener_ofertas(cache_key)

        fuentes_consultadas: list[FuenteOferta] = []

        if ofertas_recuperadas is None:
            ofertas_recuperadas = []
            kw_tuple = tuple(query.palabras_clave)

            for portal in self._portales:
                try:
                    fuente = portal.obtener_fuente()
                    fuentes_consultadas.append(fuente)
                    encontradas = portal.buscar_ofertas(
                        palabras_clave=kw_tuple,
                        ubicacion=query.ubicacion,
                    )
                    ofertas_recuperadas.extend(encontradas)
                except Exception as exc:  # noqa: BLE001
                    # Tolerancia a fallos: la caída de un portal no aborta la búsqueda en los demás
                    logger.warning(
                        "Fallo al consultar portal de empleo %s: %s",
                        portal.obtener_fuente(),
                        exc,
                    )
                    continue

            # Filtrado por Vaca Muerta / Cuenca Neuquina si está habilitado
            if query.solo_vaca_muerta:
                ofertas_recuperadas = [
                    o
                    for o in ofertas_recuperadas
                    if self._filtro_vaca_muerta.es_relevante_vaca_muerta(o)
                ]

            if self._cache:
                self._cache.guardar_ofertas(cache_key, ofertas_recuperadas)
        else:
            fuentes_consultadas = [p.obtener_fuente() for p in self._portales]

        # Determinar el perfil a utilizar para el scoring
        perfil = (
            EmpleoMapper.perfil_dto_a_entidad(query.perfil)
            if query.perfil
            else PERFIL_DEFAULT
        )

        # Aplicar scoring
        ofertas_scored: list[OfertaLaboral] = [
            self._scoring_service.calcular_afinidad(o, perfil)
            for o in ofertas_recuperadas
        ]

        # Filtrar por score mínimo de afinidad
        if query.min_score_afinidad > 0.0:
            ofertas_scored = [
                o
                for o in ofertas_scored
                if o.score_afinidad >= query.min_score_afinidad
            ]

        # Ordenar de mayor a menor afinidad
        ofertas_scored.sort(key=lambda o: o.score_afinidad, reverse=True)

        now_str = datetime.now(timezone.utc).isoformat()
        agregado = ResultadoBusquedaEmpleo(
            ofertas=tuple(ofertas_scored),
            total_encontradas=len(ofertas_scored),
            fuentes_consultadas=tuple(fuentes_consultadas),
            fecha_consulta=now_str,
        )

        return EmpleoMapper.resultado_entidad_a_dto(agregado)
