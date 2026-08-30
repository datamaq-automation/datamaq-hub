#!/usr/bin/env python3
"""Réplica local de datos desde el VPS DonWeb (SSOT) hacia la máquina local.

Script CLI en Python (stdlib pura, sin dependencias externas pesadas) que:
1. Genera un snapshot atómico WAL-safe de las bases SQLite del VPS mediante
   `sqlite3.Connection.backup()` en un directorio temporal remoto.
2. Crea un backup local preventivo en `data/.backups/` antes de sobreescribir.
3. Transfiere los snapshots y assets (`paritarias`, `google_ads`, `*.pdf`) con `rsync`.
4. Verifica integridad SQLite local y reporta métricas (contactos, eventos, tareas).

Direccionalidad estricta: VPS (SSOT) ➔ Local (Réplica). Nunca escribe en el VPS.

Uso:
    python3 scripts/sync_from_vps.py [--dry-run] [--only-dbs] [--host vps] \
        [--remote-dir /var/www/datamaq-hub] [--no-backup]
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DE_DATOS = ["roundcube.db", "datamaq_hub.db", "leads.db", "hub.db"]
PATRONES_EXCLUIDOS = ["test_calendar_", "test_contacts_", "-wal", "-shm"]

HOST_DEFAULT = "vps"
REMOTE_DIR_DEFAULT = "/var/www/datamaq-hub"
SNAPSHOT_PREFIX = "/tmp/datamaq_snap_"
LOCAL_DATA_DIR = "data"


def es_excluido(nombre_archivo: str) -> bool:
    """Indica si un archivo es un artefacto efímero que no debe sincronizarse."""
    return any(patron in nombre_archivo for patron in PATRONES_EXCLUIDOS)


def construir_script_snapshot(
    ruta_datos_remota: str, dir_snapshot: str, bases: list[str] | None = None
) -> str:
    """Construye el script Python ejecutable en el VPS que genera snapshots atómicos."""
    bases_objetivo = bases or BASE_DE_DATOS
    return (
        "import os, sqlite3\n"
        f"snap = {dir_snapshot!r}\n"
        "os.makedirs(snap, exist_ok=True)\n"
        f"bases = {bases_objetivo!r}\n"
        f"ruta = {ruta_datos_remota!r}\n"
        "for base in bases:\n"
        "    src = os.path.join(ruta, base)\n"
        "    if not os.path.exists(src):\n"
        "        print(f'SKIP {base}')\n"
        "        continue\n"
        "    dst = os.path.join(snap, base)\n"
        "    origen = sqlite3.connect(src)\n"
        "    destino = sqlite3.connect(dst)\n"
        "    try:\n"
        "        origen.backup(destino)\n"
        "        print(f'OK {base}')\n"
        "    finally:\n"
        "        destino.close()\n"
        "        origen.close()\n"
    )


def construir_comando_ssh(host: str, script: str) -> list[str]:
    """Arma el comando SSH que ejecuta `script` en el host remoto de forma segura."""
    return ["ssh", host, f"python3 -c {shlex.quote(script)}"]


def construir_comando_rsync(host: str, origen: str, destino: str) -> list[str]:
    """Arma el comando rsync de transferencia remota a local."""
    return ["rsync", "-avz", "--progress", f"{host}:{origen}", destino]


def parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    """Construye y parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Réplica local de datos desde el VPS DonWeb (SSOT)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista bases remotas sin transferir ni modificar archivos locales.",
    )
    parser.add_argument(
        "--only-dbs",
        action="store_true",
        help="Sincroniza solo las bases SQLite principales.",
    )
    parser.add_argument(
        "--host",
        default=HOST_DEFAULT,
        help=f"Alias o IP de SSH (default: {HOST_DEFAULT}).",
    )
    parser.add_argument(
        "--remote-dir",
        default=REMOTE_DIR_DEFAULT,
        help=f"Ruta en el VPS (default: {REMOTE_DIR_DEFAULT}).",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Omite la creación del backup local preventivo.",
    )
    return parser.parse_args(argv)


def _ejecutar(comando: list[str], descripcion: str) -> int:
    """Ejecuta un comando externo y reporta el resultado; retorna el código de salida."""
    print(f"⏳ {descripcion}")
    print(f"   $ {' '.join(shlex.quote(c) for c in comando)}")
    return subprocess.run(comando, check=False).returncode


def _esta_en_vps(remote_dir: str) -> bool:
    """Guardia anti-sobrescritura: detecta si se está ejecutando dentro del VPS."""
    return Path(remote_dir).exists()


def _verificar_integridad_sqlite(ruta_db: Path) -> str:
    """Ejecuta PRAGMA integrity_check y retorna el resultado."""
    conexion = sqlite3.connect(ruta_db)
    try:
        resultado = conexion.execute("PRAGMA integrity_check;").fetchone()
    finally:
        conexion.close()
    return resultado[0] if resultado else "desconocido"


def _contar_tabla(ruta_db: Path, tabla: str) -> int:
    """Cuenta los registros de una tabla SQLite; retorna 0 si no existe."""
    conexion = sqlite3.connect(ruta_db)
    try:
        cursor = conexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
        )
        if cursor.fetchone() is None:
            return 0
        return conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        conexion.close()


def _reportar_metricas(data_dir: Path) -> None:
    """Reporta integridad y conteos de las bases locales sincronizadas."""
    metricas: dict[str, tuple[str, ...]] = {
        "roundcube.db": ("events", "contacts"),
        "datamaq_hub.db": ("cache_entries",),
        "leads.db": ("recibos",),
        "hub.db": ("tareas",),
    }
    print("\n📊 Resumen de la réplica local:")
    for base, tablas in metricas.items():
        ruta = data_dir / base
        if not ruta.exists():
            print(f"   {base}: ausente")
            continue
        integridad = _verificar_integridad_sqlite(ruta)
        conteos = ", ".join(f"{t}={_contar_tabla(ruta, t)}" for t in tablas)
        print(f"   {base}: integrity={integridad} [{conteos}]")


def _marca_temporal() -> str:
    """Marca de tiempo UTC para nombres de backup y snapshot."""
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def _backup_local(data_dir: Path, no_backup: bool) -> None:
    """Crea un backup local preventivo de las bases actuales."""
    if no_backup:
        print("ℹ️  Backup local omitido (--no-backup).")
        return
    marca = _marca_temporal()
    destino = data_dir / ".backups" / f"backup_{marca}"
    destino.mkdir(parents=True, exist_ok=True)
    for base in BASE_DE_DATOS:
        origen = data_dir / base
        if origen.exists():
            shutil.copy2(origen, destino / base)
    print(f"🛡️  Backup local preventivo en {destino}")


def _limpiar_snapshot_remoto(host: str, dir_snapshot: str) -> None:
    """Elimina el directorio temporal de snapshot en el VPS."""
    _ejecutar(["ssh", host, "rm", "-rf", dir_snapshot], "Limpieza remota")


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del CLI de sincronización VPS ➔ Local."""
    args = parsear_argumentos(argv)

    if _esta_en_vps(args.remote_dir):
        print("⛔ Guardia anti-sobrescritura: se detectó ejecución dentro del VPS.")
        print(
            "   Este script replica VPS ➔ Local y debe ejecutarse en la máquina local."
        )
        return 2

    data_dir = Path(LOCAL_DATA_DIR)
    ruta_datos_remota = f"{args.remote_dir}/data"
    dir_snapshot = f"{SNAPSHOT_PREFIX}{_marca_temporal()}"

    # 1. Snapshot atómico remoto (WAL-safe)
    script = construir_script_snapshot(ruta_datos_remota, dir_snapshot)
    codigo = _ejecutar(
        construir_comando_ssh(args.host, script),
        "Generando snapshot atómico remoto (WAL-safe)",
    )
    if codigo != 0:
        print("❌ Falló la generación del snapshot remoto.")
        return 1

    if args.dry_run:
        print(f"🔎 [DRY-RUN] Snapshot remoto listo en {args.host}:{dir_snapshot}")
        _ejecutar(
            ["ssh", args.host, "ls", "-lh", dir_snapshot],
            "Listando bases remotas (dry-run)",
        )
        _limpiar_snapshot_remoto(args.host, dir_snapshot)
        return 0

    # 2. Backup local preventivo
    _backup_local(data_dir, args.no_backup)

    # 3. Transferencia de snapshots de bases
    codigo = _ejecutar(
        construir_comando_rsync(args.host, f"{dir_snapshot}/", f"{LOCAL_DATA_DIR}/"),
        "Descargando snapshots de bases SQLite",
    )
    if codigo != 0:
        print("❌ Falló la transferencia de bases.")
        return 1

    # 4. Transferencia de assets (salvo --only-dbs)
    if not args.only_dbs:
        for asset in ("paritarias/", "google_ads/"):
            _ejecutar(
                construir_comando_rsync(
                    args.host,
                    f"{ruta_datos_remota}/{asset}",
                    f"{LOCAL_DATA_DIR}/{asset}",
                ),
                f"Descargando assets: {asset}",
            )
        _ejecutar(
            construir_comando_rsync(
                args.host, f"{ruta_datos_remota}/*.pdf", f"{LOCAL_DATA_DIR}/"
            ),
            "Descargando PDFs de recibos",
        )

    # 5. Limpieza de temporales remotos
    _limpiar_snapshot_remoto(args.host, dir_snapshot)

    # 6. Verificación de integridad local
    _reportar_metricas(data_dir)
    print("✅ Réplica local sincronizada correctamente desde el VPS (SSOT).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
