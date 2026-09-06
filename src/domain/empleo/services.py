"""Domain services for empleo bounded context."""

import re
from dataclasses import replace

from src.domain.empleo.entities import OfertaLaboral, PerfilProfesional
from src.domain.empleo.value_objects import (
    NivelAfinidad,
    UbicacionCuenca,
)


class FiltroVacaMuertaService:
    """Servicio de dominio para identificar ofertas relacionadas con Vaca Muerta y Oil & Gas."""

    TERMINOS_INDUSTRIA_CUENCA: tuple[str, ...] = (
        "vaca muerta",
        "upstream",
        "wellsite",
        "fractura",
        "perforacion",
        "perforación",
        "drilling",
        "pozo",
        "pozos",
        "yacimiento",
        "yacimientos",
        "oil & gas",
        "oil and gas",
        "petroleo",
        "petróleo",
        "gas y petroleo",
        "hidrocarburos",
        "cuenca neuquina",
    )

    def es_relevante_vaca_muerta(self, oferta: OfertaLaboral) -> bool:
        """Determina si la oferta laboral pertenece a la cuenca o al ecosistema de Vaca Muerta."""
        if UbicacionCuenca.es_vaca_muerta(oferta.ubicacion):
            return True

        texto_completo = (
            f"{oferta.titulo} {oferta.descripcion} {' '.join(oferta.tags)}".lower()
        )
        for termino in self.TERMINOS_INDUSTRIA_CUENCA:
            if re.search(r"\b" + re.escape(termino) + r"\b", texto_completo):
                return True

        return False


class ScoringOfertasService:
    """Servicio de dominio para calcular la afinidad entre una oferta y un perfil profesional."""

    def calcular_afinidad(
        self,
        oferta: OfertaLaboral,
        perfil: PerfilProfesional,
    ) -> OfertaLaboral:
        """Evalúa y asigna el puntaje de afinidad a la oferta laboral en base al perfil."""
        score: float = 0.0

        texto_titulo = oferta.titulo.lower()
        texto_cuerpo = f"{oferta.descripcion} {' '.join(oferta.tags)}".lower()

        # 1. Calce de título profesional deseado (hasta 35 pts)
        if perfil.titulo_deseado:
            tokens_titulo_deseado = [
                t for t in perfil.titulo_deseado.lower().split() if len(t) > 3
            ]
            if tokens_titulo_deseado:
                coincidencias_titulo = sum(
                    1 for t in tokens_titulo_deseado if t in texto_titulo
                )
                # Al menos 2 términos clave en el título otorgan el puntaje pleno del título
                umbral_titulo = min(2, len(tokens_titulo_deseado))
                score += min(35.0, (coincidencias_titulo / umbral_titulo) * 35.0)

        # 2. Palabras clave prioritarias (hasta 35 pts)
        if perfil.palabras_clave_prioritarias:
            hits_prio = 0
            for kw in perfil.palabras_clave_prioritarias:
                kw_norm = kw.lower()
                # Mayor peso si está en el título
                if kw_norm in texto_titulo:
                    hits_prio += 2
                elif kw_norm in texto_cuerpo:
                    hits_prio += 1

            # Saturación realista: 6 puntos de impacto alcanzan el 100% del bloque prioritario
            umbral_prio = min(
                6.0, max(2.0, len(perfil.palabras_clave_prioritarias) * 0.35)
            )
            score += min(35.0, (hits_prio / umbral_prio) * 35.0)

        # 3. Palabras clave secundarias (hasta 15 pts)
        if perfil.palabras_clave_secundarias:
            hits_sec = sum(
                1
                for kw in perfil.palabras_clave_secundarias
                if kw.lower() in texto_cuerpo or kw.lower() in texto_titulo
            )
            # 2 o 3 términos secundarios alcanzan el 100% del bloque secundario
            umbral_sec = min(
                3.0, max(1.0, len(perfil.palabras_clave_secundarias) * 0.25)
            )
            score += min(15.0, (hits_sec / umbral_sec) * 15.0)

        # 4. Ubicación preferida (hasta 10 pts)
        if perfil.ubicaciones_preferidas:
            ub_oferta = oferta.ubicacion.lower()
            if any(pref.lower() in ub_oferta for pref in perfil.ubicaciones_preferidas):
                score += 10.0

        # 5. Modalidad admitida (hasta 5 pts)
        if (
            perfil.modalidades_admitidas
            and oferta.modalidad in perfil.modalidades_admitidas
        ):
            score += 5.0

        score = round(min(100.0, max(0.0, score)), 2)

        # Clasificación cualitativa
        if score >= 70.0:
            nivel = NivelAfinidad.ALTA
        elif score >= 45.0:
            nivel = NivelAfinidad.MEDIA
        elif score >= 20.0:
            nivel = NivelAfinidad.BAJA
        else:
            nivel = NivelAfinidad.NULA

        return replace(
            oferta,
            score_afinidad=score,
            nivel_afinidad=nivel,
        )
