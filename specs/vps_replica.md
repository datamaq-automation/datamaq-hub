# Especificación Técnica: Sincronización y Réplica Local desde el VPS (SSOT)

> **Ámbito:** Réplica local fiel y segura de los datos persistentes y operativos del **VPS DonWeb** (`/var/www/datamaq-hub/`).
> **Patrón:** Spec-Driven Development (SDD) + Clean Architecture.
> **Direccionalidad:** Unidireccional **VPS (SSOT) ➔ Local (Réplica)**. Nunca escribe datos en el VPS.

---

## 1. Objetivo y Contexto

El VPS DonWeb es la **Fuente de Verdad (SSOT)** de datos persistentes: contactos, eventos de
calendario de OpenClaw, caché de analítica, liquidaciones y tareas. El entorno local
(`/home/agustin/proyectos_software/datamaq-hub/`) debe funcionar como réplica fiel para desarrollo,
tests, analítica y ejecución de agentes.

Actualmente existe infraestructura para desplegar código local ➔ VPS (`deploy_with_check.sh`,
CI/CD), pero **no existe** un mecanismo para replicar datos VPS ➔ local.

### Alcance
- Script CLI en Python (stdlib pura) + wrapper shell para ejecutar la réplica.
- Snapshot atómico **WAL-safe** de las bases SQLite en producción mediante `sqlite3.Connection.backup()`.
- Respaldo local preventivo, filtrado de artefactos efímeros y verificación de integridad.
- Runbook operativo y documentación.

### Límites (fuera de alcance)
- No desplegar código (eso sigue usando Git y `deploy_with_check.sh`).
- No escribir datos en el VPS.
- No sincronizar bases efímeras de tests (`test_calendar_*.db`, `test_contacts_*.db`).

---

## 2. Topología de Datos (SSOT en VPS)

| Recurso | Ruta en VPS | Contenido | Modo |
|---|---|---|---|
| `roundcube.db` | `data/roundcube.db` | Contactos y +340 eventos de calendario (OpenClaw/Roundcube) | SQLite WAL |
| `datamaq_hub.db` | `data/datamaq_hub.db` | Caché persistente Google Ads, GA4, Clarity, designaciones | SQLite WAL |
| `leads.db` | `data/leads.db` | Recibos de sueldo parseados y horarios de designaciones | SQLite |
| `hub.db` | `data/hub.db` | Registro de tareas internas | SQLite |
| `data/paritarias/` | `data/paritarias/` | Tablas y escalas salariales JSON | Archivos |
| `data/google_ads/` | `data/google_ads/` | Estructura de campañas y metadatos | Archivos |
| `data/*.pdf` | `data/*.pdf` | Recibos de prueba y fixtures reales | Archivos |

### Artefactos efímeros a EXCLUIR
- Bases de tests: `test_calendar_*.db`, `test_contacts_*.db`.
- Archivos de journaling WAL: `*.db-wal`, `*.db-shm`.
- Sockets, cachés y temporales.

---

## 3. Principios de Diseño

1. **Consistencia Atómica en Caliente (WAL-Safe):** los servicios Uvicorn/OpenClaw corren con
   SQLite en WAL; copiar `.db` en caliente con `rsync` plano puede corromper. Se ejecuta un
   mini-hook Python en el VPS que usa `sqlite3.Connection.backup()` para generar snapshots
   atómicos en `/tmp/datamaq_snap_XXXX/`.
2. **Defensa en Profundidad:** antes de sobreescribir la base local se crea un backup en
   `data/.backups/backup_YYYYMMDD_HHMMSS/`.
3. **Filtrado Estricto:** se excluyen los artefactos efímeros listados en §2.
4. **Verificación Post-Sincronización:** `PRAGMA integrity_check;` + conteo de registros.
5. **Guardia Anti-Sobrescritura:** valida que el script se ejecute **únicamente** desde la
   máquina local, nunca dentro del VPS.

---

## 4. Componentes y Contratos

### 4.1 `scripts/sync_from_vps.py` (stdlib pura, sin dependencias externas)

Interfaz CLI:
| Flag | Descripción | Default |
|---|---|---|
| `--dry-run` | Lista bases remotas (tamaños/conteos) sin transferir ni modificar | `False` |
| `--only-dbs` | Sincroniza solo las bases SQLite principales | `False` |
| `--host` | Alias/IP SSH | `vps` |
| `--remote-dir` | Ruta en VPS | `/var/www/datamaq-hub` |
| `--no-backup` | Omite backup local preventivo | `False` |

Funciones puras testables (contrato de tests):
- `BASE_DE_DATOS` → `list[str]`: `["roundcube.db", "datamaq_hub.db", "leads.db", "hub.db"]`.
- `PATRONES_EXCLUIDOS` → `list[str]`: `["test_calendar_", "test_contacts_", "-wal", "-shm"]`.
- `es_excluido(nombre_archivo: str) -> bool`: True si el nombre coincide con algún patrón.
- `construir_script_snapshot(ruta_datos_remota: str, dir_snapshot: str, bases: list[str] | None) -> str`:
  genera el script Python ejecutable en el VPS (via SSH) que crea el directorio de snapshot y
  ejecuta `sqlite3.Connection.backup()` para cada base.
- `construir_comando_ssh(host: str, script: str) -> list[str]`: arma `["ssh", host, "python3", "-c", script]`.
- `construir_comando_rsync(host: str, origen: str, destino: str) -> list[str]`.
- `parsear_argumentos(argv: list[str] | None) -> argparse.Namespace`.

Flujo `main()`:
1. Parsear argumentos.
2. Guardia anti-sobrescritura (detectar ejecución dentro del VPS).
3. `--dry-run`: listar remoto sin transferir.
4. Snapshot atómico remoto via SSH.
5. Backup local preventivo (salvo `--no-backup`).
6. Transferencia via `rsync` (snapshot de bases + assets `paritarias`, `google_ads`, `*.pdf`).
7. Limpieza de temporales remotos en `/tmp/`.
8. Verificación de integridad SQLite local + resumen de métricas (contactos, eventos, tareas).

### 4.2 `scripts/sync_replica.sh`
Wrapper ejecutable: `#!/usr/bin/env bash` que invoca `python3 scripts/sync_from_vps.py "$@"`.

---

## 5. Matriz de Pruebas (RED Suite) — `tests/unit/test_sync_from_vps.py`

| ID | Escenario | Verificación |
|---|---|---|
| R-S1 | `es_excluido` filtra `test_calendar_*`, `test_contacts_*`, `-wal`, `-shm` | `True` |
| R-S2 | `es_excluido` permite `roundcube.db`, `datamaq_hub.db` | `False` |
| R-S3 | `construir_script_snapshot` incluye las 4 bases y usa `backup` | contiene `roundcube.db` y `backup(` |
| R-S4 | `construir_script_snapshot` respeta lista de bases custom | solo bases pasadas |
| R-S5 | `construir_comando_ssh` arma comando correcto | `["ssh", "vps", "python3", "-c", script]` |
| R-S6 | `construir_comando_rsync` incluye origen `host:path` y destino | contiene `vps:/tmp/...` |
| R-S7 | `parsear_argumentos` defaults | `host == "vps"`, `remote_dir == "/var/www/datamaq-hub"` |
| R-S8 | `parsear_argumentos` flags | `--dry-run`, `--only-dbs`, `--no-backup` en `True` |

---

## 6. Criterios del Gauntlet

1. `python scripts/verify_architecture.py` → 0 violaciones.
2. `ruff check .` y `ruff format --check .` → 0 errores.
3. `pyright` (modo strict sobre `src/`) → 0 diagnósticos.
4. `agy-opt audit-dip` → 0 violaciones DIP (cero `import logging` en `adapters/`).
5. `pytest -n auto -q tests/unit/ tests/test_architecture_boundaries.py` → 100% verdes.
6. Los tests de gateway de calendario/contactos no dejan `test_*.db` residual en `data/`.
