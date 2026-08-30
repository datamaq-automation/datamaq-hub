"""Tests unitarios para scripts/sync_from_vps.py (réplica VPS → Local SSOT)."""

import shlex

from scripts.sync_from_vps import (
    BASE_DE_DATOS,
    PATRONES_EXCLUIDOS,
    construir_comando_rsync,
    construir_comando_ssh,
    construir_script_snapshot,
    es_excluido,
    parsear_argumentos,
)


def test_es_excluido_filtra_artefactos_efimeros() -> None:
    """R-S1: test_*, -wal y -shm quedan excluidos."""
    assert es_excluido("test_calendar_abc123.db") is True
    assert es_excluido("test_contacts_xyz.db") is True
    assert es_excluido("roundcube.db-wal") is True
    assert es_excluido("datamaq_hub.db-shm") is True


def test_es_excluido_permite_bases_principales() -> None:
    """R-S2: las bases operativas no se excluyen."""
    assert es_excluido("roundcube.db") is False
    assert es_excluido("datamaq_hub.db") is False
    assert es_excluido("leads.db") is False
    assert es_excluido("hub.db") is False


def test_construir_script_snapshot_incluye_bases_y_backup() -> None:
    """R-S3: el script remoto incluye las 4 bases y usa sqlite3 backup."""
    script = construir_script_snapshot("/var/www/datamaq-hub/data", "/tmp/snap_x")
    assert "roundcube.db" in script
    assert "datamaq_hub.db" in script
    assert "leads.db" in script
    assert "hub.db" in script
    assert "backup(" in script
    assert "/var/www/datamaq-hub/data" in script
    assert "/tmp/snap_x" in script


def test_construir_script_snapshot_respeta_lista_custom() -> None:
    """R-S4: solo se incluyen las bases pasadas por parámetro."""
    script = construir_script_snapshot(
        "/data", "/tmp/snap", bases=["leads.db", "hub.db"]
    )
    assert "leads.db" in script
    assert "hub.db" in script
    assert "roundcube.db" not in script


def test_construir_comando_ssh() -> None:
    """R-S5: el script remoto se envuelve con shlex.quote para shell remoto."""
    script = "import sqlite3; print('hola')"
    comando = construir_comando_ssh("vps", script)
    assert comando == ["ssh", "vps", f"python3 -c {shlex.quote(script)}"]


def test_construir_comando_rsync_incluye_host_y_origen() -> None:
    """R-S6: rsync apunta a host:origen y destino local."""
    comando = construir_comando_rsync("vps", "/tmp/snap_x/", "data/")
    assert "vps:/tmp/snap_x/" in comando
    assert "data/" in comando


def test_parsear_argumentos_defaults() -> None:
    """R-S7: defaults de host y remote-dir."""
    args = parsear_argumentos([])
    assert args.host == "vps"
    assert args.remote_dir == "/var/www/datamaq-hub"
    assert args.dry_run is False
    assert args.only_dbs is False
    assert args.no_backup is False


def test_parsear_argumentos_flags() -> None:
    """R-S8: flags --dry-run, --only-dbs y --no-backup se activan."""
    args = parsear_argumentos(["--dry-run", "--only-dbs", "--no-backup"])
    assert args.dry_run is True
    assert args.only_dbs is True
    assert args.no_backup is True


def test_constantes_de_contrato() -> None:
    """Verifica las constantes de bases y exclusiones del contrato."""
    assert BASE_DE_DATOS == ["roundcube.db", "datamaq_hub.db", "leads.db", "hub.db"]
    assert PATRONES_EXCLUIDOS == ["test_calendar_", "test_contacts_", "-wal", "-shm"]
