"""
SING OF THE CROSS (SOTC) — V0.7 THE SENTINEL
Agente Local Windows 11 para Monitoramento Contínuo (Independente do Navegador)
Coleta telemetria SSH, latência (ms), processos locais do VS Code e sincroniza com Neon PostgreSQL.
"""
import json
import platform
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
for p in (str(ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import app
import devcentral_bridge

CONFIG_FILE = Path(__file__).resolve().parent / "config.example.json"
FAILURE_COUNTS = {}


def load_agent_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "agent_id": "win11-sentinel-01",
        "interval_seconds": 30,
        "thresholds": {
            "cpu_warn": 75,
            "cpu_crit": 90,
            "ram_warn": 75,
            "ram_crit": 90,
            "disk_warn": 75,
            "disk_crit": 90,
            "latency_warn_ms": 150,
            "latency_crit_ms": 500,
            "ssh_consecutive_failures_warn": 2,
            "ssh_consecutive_failures_crit": 3,
        },
    }


def evaluate_alerts(rows, cfg):
    th = cfg.get("thresholds", {})
    alerts = []
    now = int(time.time())

    for r in rows:
        alias = r.get("ssh", "unknown")
        if r.get("ssh_status") != "ok":
            FAILURE_COUNTS[alias] = FAILURE_COUNTS.get(alias, 0) + 1
            fails = FAILURE_COUNTS[alias]
            sev = "CRITICAL" if fails >= th.get("ssh_consecutive_failures_crit", 3) else "WARNING"
            alerts.append({
                "ts": now,
                "vm_ssh": alias,
                "metric": "SSH",
                "value": f"{fails} falha(s)",
                "severity": sev,
                "message": f"Falha de conexão SSH em {alias} ({fails} tentativa(s) consecutiva(s)): {r.get('detail', '')}",
            })
        else:
            FAILURE_COUNTS[alias] = 0

        for key, label, w_key, c_key in [
            ("cpu_pct", "CPU", "cpu_warn", "cpu_crit"),
            ("ram_pct", "RAM", "ram_warn", "ram_crit"),
        ]:
            val = r.get(key)
            if val is not None:
                num = float(val)
                if num >= th.get(c_key, 90):
                    alerts.append({
                        "ts": now,
                        "vm_ssh": alias,
                        "metric": label,
                        "value": f"{num}%",
                        "severity": "CRITICAL",
                        "message": f"{label} em nível CRÍTICO na VM {alias}: {num}% (limite {th.get(c_key, 90)}%)",
                    })
                elif num >= th.get(w_key, 75):
                    alerts.append({
                        "ts": now,
                        "vm_ssh": alias,
                        "metric": label,
                        "value": f"{num}%",
                        "severity": "WARNING",
                        "message": f"{label} em ATENÇÃO na VM {alias}: {num}% (limite {th.get(w_key, 75)}%)",
                    })

        disk_raw = r.get("disk_pct")
        if disk_raw:
            try:
                d_num = float(str(disk_raw).replace("%", ""))
                if d_num >= th.get("disk_crit", 90):
                    alerts.append({
                        "ts": now,
                        "vm_ssh": alias,
                        "metric": "DISCO",
                        "value": f"{d_num}%",
                        "severity": "CRITICAL",
                        "message": f"Disco raiz (/) em nível CRÍTICO na VM {alias}: {d_num}% (limite {th.get('disk_crit', 90)}%)",
                    })
                elif d_num >= th.get("disk_warn", 75):
                    alerts.append({
                        "ts": now,
                        "vm_ssh": alias,
                        "metric": "DISCO",
                        "value": f"{d_num}%",
                        "severity": "WARNING",
                        "message": f"Disco raiz (/) em ATENÇÃO na VM {alias}: {d_num}% (limite {th.get('disk_warn', 75)}%)",
                    })
            except ValueError:
                pass

        lat = r.get("latency_ms")
        if lat is not None:
            l_num = float(lat)
            if l_num >= th.get("latency_crit_ms", 500):
                alerts.append({
                    "ts": now,
                    "vm_ssh": alias,
                    "metric": "LATÊNCIA SSH",
                    "value": f"{int(l_num)} ms",
                    "severity": "CRITICAL",
                    "message": f"Latência SSH crítica em {alias}: {int(l_num)} ms",
                })
            elif l_num >= th.get("latency_warn_ms", 150):
                alerts.append({
                    "ts": now,
                    "vm_ssh": alias,
                    "metric": "LATÊNCIA SSH",
                    "value": f"{int(l_num)} ms",
                    "severity": "WARNING",
                    "message": f"Latência SSH elevada em {alias}: {int(l_num)} ms",
                })

    return alerts


def run_cycle(cfg=None):
    if cfg is None:
        cfg = load_agent_config()
    rows = app.status()
    alerts = evaluate_alerts(rows, cfg)
    local_map = devcentral_bridge.scan_local_projects_map()
    hb = devcentral_bridge.push_sentinel_cycle_to_neon(
        agent_id=cfg.get("agent_id", "win11-sentinel-01"),
        hostname=socket.gethostname(),
        os_name=f"Windows {platform.release()}",
        interval_sec=int(cfg.get("interval_seconds", 30)),
        vms_rows=rows,
        alerts_rows=alerts,
        local_projects_map=local_map,
    )
    return {
        "ok": True,
        "checked_at": time.strftime("%H:%M:%S"),
        "vms_count": len(rows),
        "alerts_count": len(alerts),
        "local_projects_detected": len(local_map),
        "neon_sync": hb,
    }


def main():
    cfg = load_agent_config()
    interval = int(cfg.get("interval_seconds", 30))
    print("=================================================================")
    print("  SING OF THE CROSS - V0.7 THE SENTINEL AGENT (WINDOWS 11)")
    print(f"  Agente: {cfg.get('agent_id')} | Ciclo: {interval}s | Destino: Neon PostgreSQL")
    print("=================================================================")
    while True:
        try:
            res = run_cycle(cfg)
            print(
                f"[{res['checked_at']}] Sentinel Heartbeat OK | "
                f"VMs: {res['vms_count']} | Alertas: {res['alerts_count']} | "
                f"Pastas Locais Win11: {res['local_projects_detected']}"
            )
        except KeyboardInterrupt:
            print("\nSentinel Agent encerrado pelo usuário.")
            break
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Erro no ciclo Sentinel: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(json.dumps(run_cycle(), indent=2, ensure_ascii=False))
    else:
        main()
