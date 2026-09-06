#!/usr/bin/env python3
"""Sincronizador unidireccional de búsqueda laboral: VPS (MySQL SSOT) ➔ Local (SQLite réplica para pruebas)."""

import json
import os
import subprocess
import sys
from typing import Any, cast

# Asegurar src en PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.adapters.gateways.empleo.sql_oportunidades_gateway import (
    SQLOportunidadesGateway,
    init_busqueda_laboral_db,
)
from src.domain.empleo.entities import (
    InteraccionPostulacion,
    OportunidadLaboral,
)
from src.domain.empleo.value_objects import EstadoOportunidad


def sync_from_vps() -> None:
    print(
        "🔄 Conectando al VPS vía SSH para extraer datos de MySQL (busqueda_laboral)..."
    )

    query_oportunidades = """
    SELECT JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', id,
            'titulo', titulo,
            'empresa', COALESCE(empresa, ''),
            'consultora', COALESCE(consultora, ''),
            'ubicacion', ubicacion,
            'regimen', COALESCE(regimen, ''),
            'jornada', COALESCE(jornada, ''),
            'salario_min', salario_min,
            'salario_max', salario_max,
            'salario_moneda', COALESCE(salario_moneda, 'ARS'),
            'salario_bruto_neto', COALESCE(salario_bruto_neto, ''),
            'url_fuente', COALESCE(url_fuente, ''),
            'estado', estado,
            'fecha_publicacion', fecha_publicacion,
            'fecha_postulacion', fecha_postulacion,
            'fecha_entrevista', fecha_entrevista,
            'fecha_oferta', fecha_oferta,
            'fecha_descarte', fecha_descarte,
            'fecha_congelacion', fecha_congelacion,
            'notas', COALESCE(notas, ''),
            'requisitos', requisitos,
            'origen', origen,
            'tipo_modalidad', tipo_modalidad,
            'canal_adquisicion', canal_adquisicion,
            'id_campania', id_campania
        )
    ) FROM oportunidades;
    """

    cmd_op = [
        "ssh",
        "vps",
        f'mysql busqueda_laboral -e "{query_oportunidades}" -B -N',
    ]

    ops_data: list[dict[str, Any]]
    try:
        raw_ops = subprocess.check_output(cmd_op, text=True).strip()
        if not raw_ops or raw_ops == "NULL":
            ops_data = []
        else:
            ops_data = cast("list[dict[str, Any]]", json.loads(raw_ops))
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"❌ Error al consultar oportunidades en VPS: {exc}")
        sys.exit(1)

    query_interacciones = """
    SELECT JSON_ARRAYAGG(
        JSON_OBJECT(
            'id', id,
            'oportunidad_id', oportunidad_id,
            'fecha', fecha,
            'canal', canal,
            'contacto_nombre', COALESCE(contacto_nombre, ''),
            'contacto_email', COALESCE(contacto_email, ''),
            'contacto_telefono', COALESCE(contacto_telefono, ''),
            'contacto_empresa', COALESCE(contacto_empresa, ''),
            'resumen', COALESCE(resumen, ''),
            'proxima_accion', COALESCE(proxima_accion, ''),
            'fecha_proxima_accion', fecha_proxima_accion
        )
    ) FROM interacciones;
    """

    cmd_int = [
        "ssh",
        "vps",
        f'mysql busqueda_laboral -e "{query_interacciones}" -B -N',
    ]

    ints_data: list[dict[str, Any]]
    try:
        raw_ints = subprocess.check_output(cmd_int, text=True).strip()
        if not raw_ints or raw_ints == "NULL":
            ints_data = []
        else:
            ints_data = cast("list[dict[str, Any]]", json.loads(raw_ints))
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"⚠️ Advertencia al consultar interacciones: {exc}")
        ints_data = []

    local_db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data/busqueda_laboral.db")
    )
    os.makedirs(os.path.dirname(local_db_path), exist_ok=True)
    local_db_url = f"sqlite:///{local_db_path}"

    init_busqueda_laboral_db(local_db_url)
    gateway = SQLOportunidadesGateway(local_db_url)

    print(
        f"📦 Guardando {len(ops_data)} oportunidades en réplica local: {local_db_path}..."
    )
    for item in ops_data:
        reqs: object = item.get("requisitos")
        reqs_tuple: tuple[str, ...]
        if isinstance(reqs, list):
            reqs_list = cast("list[object]", reqs)
            reqs_tuple = tuple(str(r) for r in reqs_list)
        elif isinstance(reqs, str):
            try:
                p = json.loads(reqs)
                if isinstance(p, list):
                    p_list = cast("list[object]", p)
                    reqs_tuple = tuple(str(r) for r in p_list)
                else:
                    reqs_tuple = (reqs,)
            except (json.JSONDecodeError, TypeError, ValueError):
                reqs_tuple = (reqs,)
        else:
            reqs_tuple = ()

        try:
            estado_vo = EstadoOportunidad(item.get("estado"))
        except ValueError:
            estado_vo = EstadoOportunidad.DETECTADA

        op = OportunidadLaboral(
            id=item.get("id"),
            titulo=item.get("titulo", ""),
            empresa=item.get("empresa", ""),
            consultora=item.get("consultora", ""),
            ubicacion=item.get("ubicacion", "Neuquén"),
            regimen=item.get("regimen", ""),
            jornada=item.get("jornada", ""),
            salario_min=item.get("salario_min"),
            salario_max=item.get("salario_max"),
            salario_moneda=item.get("salario_moneda", "ARS"),
            salario_bruto_neto=item.get("salario_bruto_neto", ""),
            url_fuente=item.get("url_fuente", ""),
            estado=estado_vo,
            fecha_publicacion=item.get("fecha_publicacion") or "",
            fecha_postulacion=item.get("fecha_postulacion") or "",
            fecha_entrevista=item.get("fecha_entrevista") or "",
            fecha_oferta=item.get("fecha_oferta") or "",
            fecha_descarte=item.get("fecha_descarte") or "",
            fecha_congelacion=item.get("fecha_congelacion") or "",
            notas=item.get("notas", ""),
            requisitos=reqs_tuple,
            origen=item.get("origen", "MANUAL"),
            tipo_modalidad=item.get("tipo_modalidad", "RELACION_DEPENDENCIA"),
            canal_adquisicion=item.get("canal_adquisicion", "DIRECTO"),
            id_campania=item.get("id_campania"),
        )
        gateway.guardar(op)

    print(f"📝 Guardando {len(ints_data)} interacciones...")
    for item in ints_data:
        op_id_val = item.get("oportunidad_id")
        op_id: int = int(op_id_val) if op_id_val is not None else 0
        inter = InteraccionPostulacion(
            id=item.get("id"),
            oportunidad_id=op_id,
            fecha=item.get("fecha") or "",
            canal=item.get("canal", "MAIL"),
            contacto_nombre=item.get("contacto_nombre", ""),
            contacto_email=item.get("contacto_email", ""),
            contacto_telefono=item.get("contacto_telefono", ""),
            contacto_empresa=item.get("contacto_empresa", ""),
            resumen=item.get("resumen", ""),
            proxima_accion=item.get("proxima_accion", ""),
            fecha_proxima_accion=item.get("fecha_proxima_accion") or "",
        )
        gateway.registrar_interaccion(inter)

    print("✅ Sincronización exitosa. Base local réplica lista para pruebas.")


if __name__ == "__main__":
    sync_from_vps()
