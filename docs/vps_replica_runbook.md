# Runbook: Réplica Local desde el VPS (SSOT)

> **Ámbito:** Operación diaria de sincronización de datos persistentes y operativos.
> **Direccionalidad:** Unidireccional **VPS DonWeb (SSOT) ➔ Local (Réplica)**. Nunca escribe en el VPS.
> **Especificación formal:** [`specs/vps_replica.md`](../specs/vps_replica.md).

---

## 1. Modelo de Fuente de Verdad (SSOT)

El VPS DonWeb (`/var/www/datamaq-hub/`) es la fuente de verdad de todos los datos
persistentes y operativos:

| Base / Recurso | Contenido |
|---|---|
| `data/roundcube.db` | Contactos y +340 eventos de calendario de OpenClaw/Roundcube |
| `data/datamaq_hub.db` | Caché persistente Google Ads, GA4, Clarity, designaciones |
| `data/leads.db` | Recibos de sueldo parseados y horarios de designaciones |
| `data/hub.db` | Registro de tareas internas |
| `data/paritarias/`, `data/google_ads/`, `data/*.pdf` | Tablas salariales, campañas y recibos |

El entorno local es una **réplica** para desarrollo, tests, analítica y ejecución de
agentes. Cualquier cambio de datos operativos se produce en el VPS y se replica hacia
local; **nunca al revés**.

---

## 2. Sincronizar la Réplica en 1 Comando

### Requisito previo
- Alias SSH `vps` configurado en `~/.ssh/config` (o `vps4` vía `--host vps4`).
- `rsync` disponible localmente.
- Clave SSH con acceso al VPS.

### Comando principal
```bash
./scripts/sync_replica.sh
```

Esto:
1. Genera un snapshot atómico **WAL-safe** de las bases en el VPS (via `sqlite3.backup()`).
2. Crea un backup local preventivo en `data/.backups/backup_YYYYMMDD_HHMMSS/`.
3. Descarga los snapshots y assets (`paritarias/`, `google_ads/`, `*.pdf`).
4. Limpia temporales remotos.
5. Verifica integridad SQLite (`PRAGMA integrity_check`) y reporta métricas.

### Variantes útiles
```bash
# Solo bases SQLite (sin assets ni PDFs)
./scripts/sync_replica.sh --only-dbs

# Vista previa sin transferir nada
./scripts/sync_replica.sh --dry-run

# Usar otro host SSH
./scripts/sync_replica.sh --host vps4

# Omitir el backup local preventivo
./scripts/sync_replica.sh --no-backup
```

---

## 3. Restaurar un Backup Local

Cada sincronización deja una copia en `data/.backups/backup_YYYYMMDD_HHMMSS/`.
Para restaurar:

```bash
# 1. Identificar el backup a restaurar
ls -1 data/.backups/

# 2. Restaurar las bases deseadas (ejemplo)
cp data/.backups/backup_20260829_123456/roundcube.db data/roundcube.db
cp data/.backups/backup_20260829_123456/datamaq_hub.db data/datamaq_hub.db
cp data/.backups/backup_20260829_123456/leads.db data/leads.db
cp data/.backups/backup_20260829_123456/hub.db data/hub.db
```

> ⚠️ Si los servicios locales (uvicorn) están corriendo, detenerlos antes de restaurar
> para evitar escrituras concurrentes sobre las bases.

---

## 4. Validar la Integridad de los Datos

El script reporta `PRAGMA integrity_check` automáticamente al final. Para validar
manualmente:

```bash
python3 - <<'PY'
import sqlite3
for db in ("roundcube.db", "datamaq_hub.db", "leads.db", "hub.db"):
    conn = sqlite3.connect(f"data/{db}")
    print(db, conn.execute("PRAGMA integrity_check;").fetchone()[0])
    conn.close()
PY
```

### Verificación funcional
- **Calendario:** consultar el endpoint local `/api/v1/calendario/proximos` y confirmar
  que refleja los eventos del VPS (más de 340 eventos).
- **Analítica:** confirmar que el caché local (`datamaq_hub.db`) responde sin refetch
  a las APIs externas.

---

## 5. Resolución de Problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| `⛔ Guardia anti-sobrescritura` | Script ejecutado dentro del VPS | Ejecutar desde la máquina local |
| `rsync` falla con permiso | Clave SSH sin acceso | Verificar `ssh vps echo ok` |
| Base corrupta tras sincronización | Snapshot no usado | Confirmar salida `OK <base>` del snapshot |
| Backup ausente | `--no-backup` activo | Re-sincronizar sin el flag |
