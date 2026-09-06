#!/usr/bin/env python3
"""CLI manual para búsqueda y scoring de oportunidades laborales en Vaca Muerta."""

import argparse
import os
import sys

# Asegurar src en PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.controllers.dependencies import get_empleo_controller
from src.application.dtos.empleo_dtos import BuscarOfertasQueryDTO


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Búsqueda manual de empleo en Vaca Muerta ponderada por perfil profesional."
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="*",
        default=["confiabilidad", "mantenimiento", "telemetria", "vfd"],
        help="Palabras clave a buscar (ej: -k confiabilidad vfd scada)",
    )
    parser.add_argument(
        "-u",
        "--ubicacion",
        default=None,
        help="Filtro geográfico opcional (ej: -u Añelo)",
    )
    parser.add_argument(
        "--todas-las-zonas",
        action="store_true",
        help="Desactiva el filtro estricto de cuenca Vaca Muerta",
    )
    parser.add_argument(
        "-m",
        "--min-score",
        type=float,
        default=30.0,
        help="Puntaje mínimo de afinidad (0 a 100). Default: 30",
    )

    args = parser.parse_args()

    controller = get_empleo_controller()
    query = BuscarOfertasQueryDTO(
        palabras_clave=args.keywords,
        ubicacion=args.ubicacion,
        solo_vaca_muerta=not args.todas_las_zonas,
        min_score_afinidad=args.min_score,
    )

    print("\n🔍 Consultando portales de empleo: YPF, Tecpetrol, PAE, Vista Energy...")
    print(
        f"📌 Filtros: Keywords={args.keywords} | Ubicación={args.ubicacion or 'Cualquiera en Cuenca'} | Min Score={args.min_score}"
    )
    print("=" * 80)

    resultado = controller.buscar_ofertas_vaca_muerta(query)

    print(f"📊 Total ofertas encontradas y calificadas: {resultado.total_encontradas}")
    print(f"🌐 Fuentes consultadas: {', '.join(resultado.fuentes_consultadas)}")
    print("=" * 80)

    if not resultado.ofertas:
        print(
            "ℹ️ No se encontraron ofertas que superen el score mínimo en este momento."
        )
        return

    for idx, oferta in enumerate(resultado.ofertas, 1):
        color_tag = (
            "🟢 ALTA"
            if oferta.score_afinidad >= 70
            else ("🟡 MEDIA" if oferta.score_afinidad >= 45 else "⚪ BAJA")
        )
        print(f"\n[{idx}] {oferta.titulo}")
        print(f"    🏢 Empresa: {oferta.empresa} ({oferta.fuente})")
        print(f"    📍 Ubicación: {oferta.ubicacion} | Modalidad: {oferta.modalidad}")
        print(f"    🎯 Score de afinidad: {oferta.score_afinidad}% ({color_tag})")
        if oferta.url_postulacion:
            print(f"    🔗 Postulación: {oferta.url_postulacion}")
        if oferta.descripcion:
            desc_corta = (
                (oferta.descripcion[:160] + "...")
                if len(oferta.descripcion) > 160
                else oferta.descripcion
            )
            print(f"    📝 {desc_corta}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
