#!/usr/bin/env python3
"""CLI manual para gestión y seguimiento de postulaciones laborales en Vaca Muerta."""

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import cast

# Asegurar src en PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.controllers.dependencies import get_empleo_controller
from src.application.dtos.empleo_dtos import (
    ActualizarEstadoOportunidadDTO,
    RegistrarInteraccionDTO,
    RegistrarOportunidadDTO,
)


def cmd_listar(args: argparse.Namespace) -> None:
    controller = get_empleo_controller()
    estado = getattr(args, "estado", None)
    empresa = getattr(args, "empresa", None)
    oportunidades = controller.listar_oportunidades(
        estado=estado,
        empresa=empresa,
    )

    print(f"\n📋 Postulaciones / Oportunidades ({len(oportunidades)} encontradas):")
    print("=" * 95)
    print(
        f"{'ID':<5} | {'ESTADO':<12} | {'EMPRESA':<25} | {'TÍTULO':<32} | {'UBICACIÓN'}"
    )
    print("-" * 95)

    for op in oportunidades:
        titulo = (op.titulo[:30] + "..") if len(op.titulo) > 32 else op.titulo
        emp_nombre = (op.empresa[:23] + "..") if len(op.empresa) > 25 else op.empresa
        ubicacion = (
            (op.ubicacion[:18] + "..") if len(op.ubicacion) > 20 else op.ubicacion
        )
        print(
            f"{op.id or 0:<5} | {op.estado:<12} | {emp_nombre:<25} | {titulo:<32} | {ubicacion}"
        )
    print("=" * 95)


def cmd_ver(args: argparse.Namespace) -> None:
    controller = get_empleo_controller()
    oportunidades = controller.listar_oportunidades()
    op = next((o for o in oportunidades if o.id == args.id), None)
    if not op:
        print(f"❌ No se encontró la oportunidad con ID {args.id}")
        return

    print(f"\n📄 Detalle de Oportunidad #{op.id}")
    print("=" * 80)
    print(f"📌 Título:     {op.titulo}")
    print(f"🏢 Empresa:    {op.empresa or '-'}")
    print(f"👥 Consultora: {op.consultora or '-'}")
    print(f"📍 Ubicación:  {op.ubicacion or '-'}")
    print(f"🔄 Régimen:    {op.regimen or '-'}")
    print(f"⏱️  Jornada:    {op.jornada or '-'}")
    print(f"🏷️  Estado:     {op.estado}")
    print(f"🔗 Fuente:     {op.url_fuente or '-'}")
    if op.salario_min or op.salario_max:
        s_min = op.salario_min or 0
        s_max = op.salario_max or 0
        print(
            f"💰 Salario:    {op.salario_moneda} {s_min:,.2f} - {s_max:,.2f} ({op.salario_bruto_neto})"
        )
    print(f"📅 Publicación: {op.fecha_publicacion or '-'}")
    print(f"📬 Postulación: {op.fecha_postulacion or '-'}")
    print(f"📝 Notas:       {op.notas or '-'}")
    if op.requisitos:
        req_texts: list[str] = []
        for r in op.requisitos:
            item: object = r
            if isinstance(r, str) and r.strip().startswith("{"):
                try:
                    import ast

                    item = ast.literal_eval(r.strip())
                except (ValueError, SyntaxError):
                    item = r

            if isinstance(item, dict):
                item_dict = cast(dict[str, object], item)
                desc = str(item_dict.get("descripcion", str(item_dict)))
                excl = " (Excluyente)" if item_dict.get("excluyente") else ""
                req_texts.append(f"{desc}{excl}")
            else:
                req_texts.append(str(item))

        print("⚡ Requisitos:")
        for r_txt in req_texts:
            print(f"   • {r_txt}")

    interacciones = controller.listar_interacciones(oportunidad_id=op.id or 0)
    print(f"\n💬 Historial de Interacciones ({len(interacciones)}):")
    print("-" * 80)
    if not interacciones:
        print("   (Sin interacciones registradas aún)")
    else:
        for idx, inter in enumerate(interacciones, 1):
            print(
                f"   {idx}. [{inter.fecha}] ({inter.canal}) Contacto: {inter.contacto_nombre or '-'}"
            )
            print(f"      Resumen: {inter.resumen or '-'}")
            if inter.proxima_accion:
                print(
                    f"      Próxima acción: {inter.proxima_accion} ({inter.fecha_proxima_accion or 'Sin fecha'})"
                )
    print("=" * 80)


def cmd_nueva(args: argparse.Namespace) -> None:
    controller = get_empleo_controller()
    dto = RegistrarOportunidadDTO(
        titulo=args.titulo,
        empresa=args.empresa or "",
        consultora=args.consultora or "",
        ubicacion=args.ubicacion or "Neuquén",
        regimen=args.regimen or "",
        jornada=args.jornada or "",
        url_fuente=args.url or "",
        estado=args.estado or "DETECTADA",
        notas=args.notas or "",
    )
    creada = controller.registrar_oportunidad(dto)
    print(f"✅ Oportunidad #{creada.id} registrada exitosamente!")
    print(f"   Título:  {creada.titulo}")
    print(f"   Empresa: {creada.empresa}")
    print(f"   Estado:  {creada.estado}")


def cmd_estado(args: argparse.Namespace) -> None:
    controller = get_empleo_controller()
    dto = ActualizarEstadoOportunidadDTO(
        id_oportunidad=args.id,
        nuevo_estado=args.nuevo_estado,
        notas=args.notas,
    )
    actualizada = controller.actualizar_estado_oportunidad(dto)
    print(f"✅ Estado actualizado para Oportunidad #{actualizada.id}!")
    print(f"   Nuevo Estado: {actualizada.estado}")
    if actualizada.notas:
        print(f"   Notas:        {actualizada.notas}")


def cmd_interaccion(args: argparse.Namespace) -> None:
    controller = get_empleo_controller()
    fecha_hoy = datetime.now(timezone.utc).date().isoformat()
    dto = RegistrarInteraccionDTO(
        oportunidad_id=args.id,
        fecha=args.fecha or fecha_hoy,
        canal=args.canal or "MAIL",
        contacto_nombre=args.contacto or "",
        resumen=args.resumen,
        proxima_accion=args.proxima or "",
        fecha_proxima_accion=args.fecha_proxima or "",
    )
    inter = controller.registrar_interaccion(dto)
    print(
        f"✅ Interacción #{inter.id} registrada para Oportunidad #{inter.oportunidad_id}!"
    )
    print(f"   Canal:    {inter.canal}")
    print(f"   Contacto: {inter.contacto_nombre or '-'}")
    print(f"   Resumen:  {inter.resumen}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gestor y Tracker de Postulaciones Laborales en Vaca Muerta"
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # listar
    p_listar = subparsers.add_parser(
        "listar", aliases=["ls"], help="Listar oportunidades"
    )
    p_listar.add_argument(
        "-e",
        "--estado",
        default=None,
        help="Filtrar por estado (DETECTADA, POSTULADA, etc.)",
    )
    p_listar.add_argument(
        "-m", "--empresa", default=None, help="Filtrar por nombre de empresa"
    )

    # ver
    p_ver = subparsers.add_parser(
        "ver", help="Ver detalle e interacciones de una oportunidad"
    )
    p_ver.add_argument("id", type=int, help="ID de la oportunidad")

    # nueva
    p_nueva = subparsers.add_parser(
        "nueva", aliases=["add"], help="Registrar nueva oportunidad"
    )
    p_nueva.add_argument(
        "-t", "--titulo", required=True, help="Título o puesto laboral"
    )
    p_nueva.add_argument("-m", "--empresa", default="", help="Nombre de la empresa")
    p_nueva.add_argument(
        "-c", "--consultora", default="", help="Nombre de la consultora / headhunter"
    )
    p_nueva.add_argument(
        "-u", "--ubicacion", default="Neuquén", help="Ubicación o localidad"
    )
    p_nueva.add_argument(
        "-r", "--regimen", default="", help="Régimen laboral (ej: 14x14, 7x7)"
    )
    p_nueva.add_argument("-j", "--jornada", default="", help="Jornada laboral")
    p_nueva.add_argument("--url", default="", help="URL de la postulación o fuente")
    p_nueva.add_argument(
        "-e",
        "--estado",
        default="DETECTADA",
        help="Estado inicial (default: DETECTADA)",
    )
    p_nueva.add_argument("-n", "--notas", default="", help="Notas adicionales")

    # estado
    p_estado = subparsers.add_parser(
        "estado", help="Actualizar estado de una oportunidad"
    )
    p_estado.add_argument("id", type=int, help="ID de la oportunidad")
    p_estado.add_argument(
        "nuevo_estado",
        help="Nuevo estado (DETECTADA, POSTULADA, EN_CONTACTO, ENTREVISTA, OFERTA, DESCARTADA, CONGELADA)",
    )
    p_estado.add_argument(
        "-n", "--notas", default=None, help="Notas adicionales para la actualización"
    )

    # interaccion
    p_inter = subparsers.add_parser(
        "interaccion", help="Registrar una interacción / contacto"
    )
    p_inter.add_argument("id", type=int, help="ID de la oportunidad")
    p_inter.add_argument(
        "-r", "--resumen", required=True, help="Resumen del contacto o interacción"
    )
    p_inter.add_argument(
        "-c",
        "--canal",
        default="MAIL",
        help="Canal de contacto (MAIL, TELEFONO, LINKEDIN, ENTREVISTA, WHATSAPP)",
    )
    p_inter.add_argument(
        "--contacto", default="", help="Nombre del reclutador o contacto"
    )
    p_inter.add_argument(
        "--fecha", default="", help="Fecha de la interacción (YYYY-MM-DD)"
    )
    p_inter.add_argument("--proxima", default="", help="Próxima acción planificada")
    p_inter.add_argument(
        "--fecha-proxima", default="", help="Fecha de próxima acción (YYYY-MM-DD)"
    )

    args = parser.parse_args()
    if not args.subcommand or args.subcommand in ["listar", "ls"]:
        cmd_listar(args)
    elif args.subcommand == "ver":
        cmd_ver(args)
    elif args.subcommand in ["nueva", "add"]:
        cmd_nueva(args)
    elif args.subcommand == "estado":
        cmd_estado(args)
    elif args.subcommand == "interaccion":
        cmd_interaccion(args)


if __name__ == "__main__":
    main()
