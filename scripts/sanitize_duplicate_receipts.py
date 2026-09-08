#!/usr/bin/env python3
"""Script de higiene para detectar y sanear recibos duplicados en la base de datos."""

import argparse

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

# Importar modelo
from src.adapters.gateways.sql_recibo_gateway import ReciboModel


def sanitize_receipts(db_url: str, apply_changes: bool = False) -> None:
    engine = create_engine(db_url)
    with Session(engine) as session:
        # Obtener todos los recibos
        stmt = select(ReciboModel).order_by(ReciboModel.creado_en.asc())
        recibos = session.scalars(stmt).all()

        grupos: dict[tuple[str, str, str | None], list[ReciboModel]] = {}
        for r in recibos:
            key = (r.docente_cuit, r.mes_pago, r.pdf_hash)
            grupos.setdefault(key, []).append(r)

        duplicados_a_eliminar: list[str] = []
        for (cuit, mes, pdf_hash), lista in grupos.items():
            if len(lista) > 1:
                print(
                    f"🔍 Grupo duplicado detectado CUIT={cuit} MES={mes} HASH={pdf_hash}:"
                )
                # Preservar el primero (o el de referencia conocido)
                preservado = lista[0]
                # Buscar si el de referencia a6c1baa7 está en la lista
                for item in lista:
                    if item.id_recibo == "a6c1baa7-a9c2-4d97-8624-a68c98940e52":
                        preservado = item
                        break

                print(
                    f"   ✅ Conservando recibo ID: {preservado.id_recibo} (creado {preservado.creado_en})"
                )
                for dup in lista:
                    if dup.id_recibo != preservado.id_recibo:
                        print(f"   ❌ Marcado para borrar: {dup.id_recibo}")
                        duplicados_a_eliminar.append(dup.id_recibo)

        if not duplicados_a_eliminar:
            print("✨ No se encontraron recibos duplicados en la base de datos.")
            return

        print(
            f"\n📊 Total de recibos duplicados a eliminar: {len(duplicados_a_eliminar)}"
        )
        if apply_changes:
            del_stmt = delete(ReciboModel).where(
                ReciboModel.id_recibo.in_(duplicados_a_eliminar)
            )
            session.execute(del_stmt)
            session.commit()
            print("🎉 Saneamiento ejecutado con éxito. Base de datos higienizada.")
        else:
            print(
                "⚠️ Modo DRY-RUN. Ejecute con '--apply' para confirmar la eliminación de los duplicados."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sanear recibos de sueldo duplicados en BD."
    )
    parser.add_argument(
        "--db-url", default="sqlite:///data/leads.db", help="URL de la base de datos"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Confirmar y aplicar eliminación de duplicados",
    )
    args = parser.parse_args()

    sanitize_receipts(db_url=args.db_url, apply_changes=args.apply)
