"""Diagnóstico integral no invasivo de hardware, OpenClaw y Datamaq Hub en el VPS.

Etapa 1 (100% solo lectura / cero downtime). Releva y consolida en un único reporte
Markdown las métricas de: host/kernel, procesos & memoria, límites systemd/cgroups,
contexto de OpenClaw y benchmark de latencia/payload de los endpoints loopback.

Uso (en el VPS):
    python scripts/diagnose_vps_hardware.py --output /tmp/diagnostico_vps.md
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, cast

# Asegura que la raíz del proyecto esté en sys.path (para leer Settings si hay .env).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

API_BASE = "http://127.0.0.1:8013"

# Endpoints del benchmark: (descripción, ruta completa)
# La ruta se mide con GET; compacto=true se usa cuando corresponde.
BENCHMARK_ENDPOINTS: list[tuple[str, str, str]] = [
    (
        "Resumen no leídos (mail)",
        "/api/v1/mail/inbox/sin-leer",
        "GET /api/v1/mail/inbox/sin-leer",
    ),
    (
        "Contactos full",
        "/api/v1/contactos?compact=false",
        "GET /api/v1/contactos (full)",
    ),
    (
        "Contactos compact",
        "/api/v1/contactos?compact=true",
        "GET /api/v1/contactos (compact)",
    ),
    (
        "Calendario full",
        "/api/v1/calendario/eventos?compact=false",
        "GET /api/v1/calendario/eventos (full)",
    ),
    (
        "Calendario compact",
        "/api/v1/calendario/eventos?compact=true",
        "GET /api/v1/calendario/eventos (compact)",
    ),
]


# --------------------------------------------------------------------------- #
# Colectores de métricas
# --------------------------------------------------------------------------- #
def collect_cpu_and_load() -> dict[str, Any]:
    """Releva vCPUs, load average y steal time."""
    data: dict[str, Any] = {}
    data["vcpus"] = os.cpu_count()

    try:
        load1, load5, load15 = os.getloadavg()
        data["load_avg"] = {
            "1m": round(load1, 2),
            "5m": round(load5, 2),
            "15m": round(load15, 2),
        }
    except OSError:
        data["load_avg"] = {}

    # Steal % vía vmstat (tiempo de espera del hipervisor DonWeb).
    steal = _run_cmd(["vmstat", "1", "2"])
    if steal is not None:
        # Toma la segunda línea de medición (promedio previo descartado).
        lines = [
            ln.split()
            for ln in steal.splitlines()
            if ln.strip() and ln.split()[0].isdigit()
        ]
        if len(lines) >= 2:
            data["steal_ms"] = lines[1][-1] if len(lines[1]) >= 17 else "n/d"
    return data


def collect_memory_and_swap() -> dict[str, Any]:
    """Releva RAM, swap y vm.swappiness desde /proc."""
    mem_info: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                key, rest = line.split(":", 1)
                val_kb = rest.strip().split()[0]
                if val_kb.isdigit():
                    mem_info[key.strip()] = int(val_kb) // 1024  # KB -> MB
    except OSError:
        pass

    data: dict[str, Any] = {"meminfo_mb": mem_info}
    try:
        data["swappiness"] = int(Path("/proc/sys/vm/swappiness").read_text().strip())
    except (OSError, ValueError):
        data["swappiness"] = None
    return data


def collect_processes() -> dict[str, Any]:
    """Releva procesos OpenClaw (Node), Datamaq Hub (uvicorn) y servicios (mysqld, dovecot)."""
    procs: dict[str, Any] = {}

    patrones: dict[str, list[tuple[str, ...]]] = {
        # `args` es el cmdline completo (path del ejecutable incluido), no el `comm`
        # (token único). Se usa el path para distinguir el venv de datamaq-hub de
        # otros servicios Python del VPS sin capturarlos por error.
        "openclaw": [("openclaw",)],
        "datamaq_hub": [("datamaq-hub",)],
        "mysql": [("mysqld",)],
        "dovecot": [("dovecot",)],
    }

    for key, patterns in patrones.items():
        rows = _ps_rows()
        matched = [r for r in rows if _all_in(r, patterns)]
        procs[key] = {
            "total": len(matched),
            "pids": [r.get("pid") for r in matched],
            "rss_mb_consolidado": round(sum(r.get("rss", 0) for r in matched), 1),
        }

    return procs


def collect_systemd_limits() -> dict[str, Any]:
    """Consulta límites/cgroups de openclaw.service y datamaq-hub.service."""
    services = ["openclaw.service", "datamaq-hub.service"]
    out: dict[str, Any] = {}
    for svc in services:
        show = _run_cmd(["systemctl", "show", svc, "--no-pager"])
        out[svc] = _parse_systemctl_properties(
            show,
            [
                "MemoryMax",
                "MemoryCurrent",
                "TasksMax",
                "CPUQuota",
                "LimitNOFILE",
                "ActiveState",
                "MainPID",
            ],
        )
    return out


def collect_storage_and_dbs() -> dict[str, Any]:
    """Releva espacio en disco y tamaños de bases de datos locales."""
    data: dict[str, Any] = {}

    disk = _run_cmd(["df", "-h"])
    if disk is not None:
        data["disk_df"] = disk

    data["data_archives"] = {}
    for name, rel in {
        "datamaq_hub.db": "data/datamaq_hub.db",
        "datamaq_hub.db-wal": "data/datamaq_hub.db-wal",
        "datamaq_hub.db-shm": "data/datamaq_hub.db-shm",
        "roundcube.db": "data/roundcube.db",
    }.items():
        p = ROOT / rel
        data["data_archives"][name] = (
            round(p.stat().st_size / 1024 / 1024, 2) if p.exists() else None
        )  # MB

    data["openclaw_home"] = {}
    oc_home = Path("/home/openclaw/.openclaw")
    if oc_home.exists():
        data["openclaw_home"]["total_mb"] = round(_dir_size_mb(oc_home), 2)
        for sub in ["transcripts", "log", "cache"]:
            sp = oc_home / sub
            data["openclaw_home"][f"{sub}_mb"] = (
                round(_dir_size_mb(sp), 2) if sp.exists() else 0.0
            )
    return data


def bench_endpoints(extra_message: str = "") -> list[dict[str, Any]]:
    """Mide TTFB y tamaño de payload de los endpoints loopback."""
    results: list[dict[str, Any]] = []
    for label, path, _ in BENCHMARK_ENDPOINTS:
        url = f"{API_BASE}{path}"
        ttfb_ms, size_bytes, status = _http_get_metrics(url)
        results.append(
            {
                "label": label,
                "ttfb_ms": ttfb_ms,
                "size_bytes": size_bytes,
                "size_kb": round((size_bytes or 0) / 1024, 1),
                "status": status,
            }
        )
    return results


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _ps_rows() -> list[dict[str, Any]]:
    """Lista procesos con pid/rss/cpu/cmdline completo vía ps."""
    try:
        raw = subprocess.run(
            ["ps", "axo", "pid=,rss=,%cpu=,args="],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        rows: list[dict[str, str | float]] = []
        for ln in raw.splitlines():
            parts = ln.split(None, 3)
            if len(parts) < 2:
                continue
            try:
                rss_mb = round(float(parts[1]) / 1024, 1)
            except ValueError:
                rss_mb = 0.0
            rows.append(
                {
                    "pid": parts[0],
                    "rss": rss_mb,
                    "cpu": parts[2] if len(parts) > 2 else "0",
                    "comm": parts[3] if len(parts) > 3 else "",
                }
            )
        return rows
    except Exception:  # noqa: BLE001
        return []


def _all_in(row: dict[str, Any], patterns: list[tuple[str, ...]]) -> bool:
    """True si la fila coincide con alguna tupla de subcadenas (todas deben estar)."""
    comm = row.get("comm", "")
    for grp in patterns:
        if all(g in comm for g in grp):
            return True
    return False


def _run_cmd(cmd: list[str]) -> str | None:
    """Ejecuta un comando y retorna stdout (o None si falla)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
        return r.stdout if r.returncode == 0 else None
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def _parse_systemctl_properties(
    raw: str | None, props: list[str]
) -> dict[str, str | None]:
    """Extrae propiedades 'clave=valor' de la salida de systemctl show."""
    out: dict[str, str | None] = {}
    if not raw:
        return out
    for line in raw.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            if k in props:
                out[k] = v or None
    return out


def _dir_size_mb(path: Path) -> float:
    """Calcula el tamaño recursivo de un directorio en MB."""
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total / 1024 / 1024


def _http_get_metrics(
    url: str, timeout: int = 12
) -> tuple[float, int | None, int | None]:
    """GET a la URL y retorna (TTFB ms, size bytes, status) o (0, None, None) si falla."""
    t0 = time.perf_counter()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ttfb_ms = (time.perf_counter() - t0) * 1000.0
            return round(ttfb_ms, 1), len(body), resp.status
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0.0, None, getattr(exc, "code", None)


# --------------------------------------------------------------------------- #
# Render del reporte Markdown
# --------------------------------------------------------------------------- #
def render_report(data: dict[str, Any], briefing_result: dict[str, Any] | None) -> str:
    """Compone el reporte Markdown estructurado."""
    lines: list[str] = []
    lines.append(
        f"# Diagnóstico VPS — Datamaq Hub & OpenClaw\n> Fecha: {datetime.now().astimezone().date().isoformat()}"
    )
    lines.append("> Fase: **Etapa 1 (solo lectura / no invasivo)**\n")

    # Pilar 1: CPU
    cpu = data["cpu_and_load"]
    lines.append("## 1. CPU & Load Average")
    lines.append(f"- vCPUs: `{cpu.get('vcpus')}`")
    la = cpu.get("load_avg", {})
    if la:
        lines.append(
            f"- Load Avg: **1m {la.get('1m')} | 5m {la.get('5m')} | 15m {la.get('15m')}**"
        )
    if "steal_ms" in cpu:
        lines.append(f"- Steal (vmstat): `{cpu['steal_ms']}` ms")
    lines.append("")

    # Pilar 1: Memoria
    mem = data["memory_and_swap"]
    mi = mem.get("meminfo_mb", {})
    lines.append("## 2. Memoria & Swap")
    lines.append(
        f"- RAM total: `{mi.get('MemTotal')}` MB | usada: `{mi.get('MemUsed') or mi.get('Active')}`"
        f" | libre: `{mi.get('MemFree')}` | disponible: `{mi.get('MemAvailable')}`"
    )
    lines.append(
        f"- Swap total: `{mi.get('SwapTotal')}` MB | usada: `{mi.get('SwapUsed')}`"
    )
    swappiness = mem.get("swappiness")
    lines.append(
        f"- vm.swappiness: `{swappiness if swappiness is not None else 'n/d'}`"
    )
    lines.append("")

    # Pilar 2: Procesos
    procs = data["processes"]
    lines.append("## 3. Procesos & Memoria de Procesos (RSS MB)")
    for key, p in procs.items():
        lines.append(
            f"- **{key}**: {p['total']} instancia(s) | RSS consolidado: {p['rss_mb_consolidado']} MB"
            f" | PIDs: {', '.join(str(x) for x in p['pids'][:5])}"
        )
    lines.append("")

    # Pilar 3: Systemd
    sd = data["systemd_limits"]
    lines.append("## 4. Límites Systemd / Cgroups")
    for svc, props in sd.items():
        if not props:
            lines.append(f"- {svc}: (sin servicio/permisos)")
            continue
        values = [f"`{k}={v}`" for k, v in props.items() if v]
        lines.append(f"- **{svc}**: {' · '.join(values) if values else '(sin datos)'}")
    lines.append("")

    # Pilar 5: Almacenamiento
    storage_raw = cast(dict[str, Any], data["storage"])
    if storage_raw.get("disk_df"):
        lines.append("## 5. Almacenamiento (df -h)")
        lines.append("```\n" + str(storage_raw["disk_df"]) + "```")
    lines.append("### Bases de datos locales & logs")
    archives: dict[str, float | None] = cast(
        dict[str, float | None], storage_raw.get("data_archives") or {}
    )
    for name in sorted(archives.keys()):
        mb = archives[name]
        lines.append(
            f"- `{name}`: {mb} MB"
            if isinstance(mb, (int, float))
            else f"- `{name}`: ausente"
        )
    oc: dict[str, float] = cast(
        dict[str, float], storage_raw.get("openclaw_home") or {}
    )
    if oc:
        lines.append("- **OpenClaw home** `~/.openclaw`:")
        for k in sorted(oc.keys()):
            v = oc[k]
            lines.append(f"    - {k}: {v} MB")
    lines.append("")

    # Pilar 4: Benchmark
    lines.append("## 6. Benchmark Loopback (127.0.0.1:8013)")
    bench = data["bench"]

    def _fmt_size(r: dict[str, Any]) -> str:
        st_ = r.get("status")
        return (
            f"`{st_}` · {r.get('size_kb')} KB · {r.get('ttfb_ms')} ms"
            if st_
            else f"`err` ({r.get('status')})"
        )

    for r in bench:
        lines.append(f"- **{r['label']}** → {_fmt_size(r)}")

    if briefing_result is not None:
        lines.append(
            f"- **Briefing diario** → `{briefing_result.get('status')}` · "
            f"{briefing_result.get('size_kb')} KB · {briefing_result.get('ttfb_ms')} ms"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnóstico integral no invasivo de hardware, OpenClaw y Datamaq Hub en el VPS."
    )
    parser.add_argument(
        "--output",
        "-o",
        default="",
        help="Ruta del archivo para guardar el reporte Markdown.",
    )
    parser.add_argument(
        "--cuit",
        default="",
        help="CUIT del docente para el benchmark de briefing diario (opcional).",
    )
    parser.add_argument(
        "--api-base",
        default=API_BASE,
        help=f"URL base de la API (default: {API_BASE}).",
    )
    args = parser.parse_args()

    report: dict[str, Any] = {}

    # 1. CPU & Load
    report["cpu_and_load"] = collect_cpu_and_load()
    # 2. Memoria
    report["memory_and_swap"] = collect_memory_and_swap()
    # 3. Procesos
    report["processes"] = collect_processes()
    # 4. Systemd
    report["systemd_limits"] = collect_systemd_limits()
    # 5. Almacenamiento
    report["storage"] = collect_storage_and_dbs()
    # 6. Benchmark
    report["bench"] = bench_endpoints()

    # Briefing (opcional, requiere cuit)
    briefing_result: dict[str, Any] | None = None
    if args.cuit:
        url = f"{args.api_base}/api/v1/agenda/briefing?cuit={args.cuit}"
        ttfb, size, status = _http_get_metrics(url)
        briefing_result = {
            "ttfb_ms": ttfb,
            "size_kb": round((size or 0) / 1024, 1) if size else 0,
            "status": status,
        }

    markdown = render_report(report, briefing_result)
    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
        print(f"✅ Reporte generado en: {args.output}")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
