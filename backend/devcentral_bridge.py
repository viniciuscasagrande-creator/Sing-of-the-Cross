import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEVCENTRAL_DIR = Path(r"D:\Projetos Vs Code\DevCentral")
LOCAL_PROJECTS_ROOTS = [Path(r"D:\Projetos Vs Code"), Path(r"E:\\")]
_SCHEMA_READY = False


def load_devcentral_env():
    """Lê variáveis de ambiente do processo (Vercel/Cloud) ou de D:\\Projetos Vs Code\\DevCentral\\.env.local."""
    env = {}
    env_file = DEVCENTRAL_DIR / ".env.local"
    if env_file.exists():
        for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("DATABASE_URL", "VERCEL_ACCOUNT_1_NAME", "VERCEL_ACCOUNT_2_NAME", "SOTC_ACCESS_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def neon_query(query, params=None):
    """Executa SQL direto no endpoint HTTP do Neon Serverless usando biblioteca padrão Python."""
    env = load_devcentral_env()
    db_url = env.get("DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise ValueError("DATABASE_URL do Neon não encontrada")

    parsed = urllib.parse.urlparse(db_url)
    host = parsed.hostname
    if not host:
        raise ValueError("Host inválido na DATABASE_URL do Neon")

    endpoint = f"https://{host}/sql"
    payload = json.dumps({"query": query, "params": params or []}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Neon-Connection-String": db_url,
            "Accept": "application/json",
            "User-Agent": "SignOfTheCross-TheSentinel/0.7.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("rows", [])


def ensure_sotc_neon_schema():
    """Cria as tabelas de persistência V0.7 The Sentinel no banco Neon PostgreSQL."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    neon_query(
        """
        CREATE TABLE IF NOT EXISTS sotc_agents (
            agent_id TEXT PRIMARY KEY,
            hostname TEXT NOT NULL,
            os_name TEXT NOT NULL DEFAULT 'Windows 11',
            version TEXT NOT NULL DEFAULT '0.7.0',
            interval_sec INTEGER NOT NULL DEFAULT 30,
            vms_count INTEGER NOT NULL DEFAULT 0,
            local_projects JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'ONLINE',
            last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_epoch BIGINT NOT NULL DEFAULT 0
        )
        """
    )
    neon_query(
        """
        CREATE TABLE IF NOT EXISTS sotc_vm_snapshots (
            ssh TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cloud TEXT NOT NULL,
            payload JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    neon_query(
        """
        CREATE TABLE IF NOT EXISTS sotc_vm_history (
            id SERIAL PRIMARY KEY,
            ts BIGINT NOT NULL,
            ssh TEXT NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    neon_query(
        """
        CREATE TABLE IF NOT EXISTS sotc_alerts (
            id SERIAL PRIMARY KEY,
            ts BIGINT NOT NULL,
            vm_ssh TEXT NOT NULL,
            metric TEXT NOT NULL,
            value TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            resolved BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    neon_query(
        """
        CREATE TABLE IF NOT EXISTS sotc_audit_log (
            id SERIAL PRIMARY KEY,
            ts BIGINT NOT NULL,
            alias TEXT NOT NULL,
            action TEXT NOT NULL,
            ok BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    neon_query(
        """
        CREATE TABLE IF NOT EXISTS sotc_incidents (
            id SERIAL PRIMARY KEY,
            incident_code TEXT UNIQUE NOT NULL,
            vm_ssh TEXT NOT NULL,
            title TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'HIGH',
            status TEXT NOT NULL DEFAULT 'OPEN',
            owner TEXT NOT NULL DEFAULT 'SRE On-Call (Vinicius)',
            sla_minutes INTEGER NOT NULL DEFAULT 60,
            opened_ts BIGINT NOT NULL,
            resolved_ts BIGINT,
            mttr_minutes NUMERIC(10,2),
            root_cause TEXT DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    neon_query(
        """
        CREATE TABLE IF NOT EXISTS sotc_hourly_rollups (
            hour_bucket BIGINT NOT NULL,
            ssh TEXT NOT NULL,
            samples_count INTEGER NOT NULL DEFAULT 1,
            avg_cpu NUMERIC(6,2) NOT NULL DEFAULT 0,
            max_cpu NUMERIC(6,2) NOT NULL DEFAULT 0,
            avg_ram NUMERIC(6,2) NOT NULL DEFAULT 0,
            avg_disk NUMERIC(6,2) NOT NULL DEFAULT 0,
            avg_latency_ms NUMERIC(10,2) NOT NULL DEFAULT 0,
            PRIMARY KEY (hour_bucket, ssh)
        )
        """
    )
    _SCHEMA_READY = True


def scan_local_projects_map():
    """Escaneia as pastas locais do Windows 11 para sincronizar com o banco Neon."""
    found = {}
    for root in LOCAL_PROJECTS_ROOTS:
        if not root.exists():
            continue
        try:
            for p in root.iterdir():
                if p.is_dir() and not p.name.startswith("."):
                    norm = re.sub(r"[^a-z0-9]", "", p.name.lower())
                    if norm:
                        found[norm] = str(p)
        except OSError:
            pass
    return found


def push_sentinel_cycle_to_neon(agent_id, hostname, os_name, interval_sec, vms_rows, alerts_rows, local_projects_map=None):
    """Registra heartbeat do Sentinel Agent, snapshots de VMs, histórico e alertas no Neon."""
    try:
        ensure_sotc_neon_schema()
        now = int(time.time())
        lmap = local_projects_map if local_projects_map is not None else scan_local_projects_map()

        neon_query(
            """
            INSERT INTO sotc_agents (agent_id, hostname, os_name, version, interval_sec, vms_count, local_projects, status, last_heartbeat, last_epoch)
            VALUES ($1, $2, $3, '0.7.0', $4, $5, $6::jsonb, 'ONLINE', NOW(), $7)
            ON CONFLICT (agent_id) DO UPDATE
            SET hostname = EXCLUDED.hostname,
                os_name = EXCLUDED.os_name,
                version = '0.7.0',
                interval_sec = EXCLUDED.interval_sec,
                vms_count = EXCLUDED.vms_count,
                local_projects = CASE WHEN EXCLUDED.local_projects::text != '{}' THEN EXCLUDED.local_projects ELSE sotc_agents.local_projects END,
                status = 'ONLINE',
                last_heartbeat = NOW(),
                last_epoch = EXCLUDED.last_epoch
            """,
            [agent_id, hostname, os_name, int(interval_sec), len(vms_rows), json.dumps(lmap, ensure_ascii=False), now],
        )

        for r in vms_rows:
            ssh_alias = r.get("ssh") or r.get("name") or "unknown"
            name = r.get("name") or ssh_alias
            cloud = r.get("cloud") or "Google Cloud"
            payload_json = json.dumps(r, ensure_ascii=False)
            neon_query(
                """
                INSERT INTO sotc_vm_snapshots (ssh, name, cloud, payload, updated_at)
                VALUES ($1, $2, $3, $4::jsonb, NOW())
                ON CONFLICT (ssh) DO UPDATE
                SET name = EXCLUDED.name,
                    cloud = EXCLUDED.cloud,
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
                """,
                [ssh_alias, name, cloud, payload_json],
            )
            neon_query(
                "INSERT INTO sotc_vm_history (ts, ssh, payload) VALUES ($1, $2, $3::jsonb)",
                [now, ssh_alias, payload_json],
            )
            hour_bucket = (now // 3600) * 3600
            cpu_v = float(r.get("cpu_pct") or 0)
            ram_v = float(r.get("ram_pct") or 0)
            try:
                disk_v = float(str(r.get("disk_pct") or "0").replace("%", ""))
            except ValueError:
                disk_v = 0.0
            lat_v = float(r.get("latency_ms") or 0)
            neon_query(
                """
                INSERT INTO sotc_hourly_rollups (hour_bucket, ssh, samples_count, avg_cpu, max_cpu, avg_ram, avg_disk, avg_latency_ms)
                VALUES ($1, $2, 1, $3, $3, $4, $5, $6)
                ON CONFLICT (hour_bucket, ssh) DO UPDATE
                SET samples_count = sotc_hourly_rollups.samples_count + 1,
                    avg_cpu = ROUND(((sotc_hourly_rollups.avg_cpu * sotc_hourly_rollups.samples_count + EXCLUDED.avg_cpu) / (sotc_hourly_rollups.samples_count + 1))::numeric, 2),
                    max_cpu = GREATEST(sotc_hourly_rollups.max_cpu, EXCLUDED.max_cpu),
                    avg_ram = ROUND(((sotc_hourly_rollups.avg_ram * sotc_hourly_rollups.samples_count + EXCLUDED.avg_ram) / (sotc_hourly_rollups.samples_count + 1))::numeric, 2),
                    avg_disk = ROUND(((sotc_hourly_rollups.avg_disk * sotc_hourly_rollups.samples_count + EXCLUDED.avg_disk) / (sotc_hourly_rollups.samples_count + 1))::numeric, 2),
                    avg_latency_ms = ROUND(((sotc_hourly_rollups.avg_latency_ms * sotc_hourly_rollups.samples_count + EXCLUDED.avg_latency_ms) / (sotc_hourly_rollups.samples_count + 1))::numeric, 2)
                """,
                [hour_bucket, ssh_alias, cpu_v, ram_v, disk_v, lat_v],
            )

        if alerts_rows is not None:
            neon_query("DELETE FROM sotc_alerts WHERE ts < $1", [now - 7 * 86400])
            for a in alerts_rows:
                neon_query(
                    """
                    INSERT INTO sotc_alerts (ts, vm_ssh, metric, value, severity, message, resolved)
                    VALUES ($1, $2, $3, $4, $5, $6, false)
                    """,
                    [now, a.get("vm_ssh", ""), a.get("metric", ""), a.get("value", ""), a.get("severity", "WARNING"), a.get("message", "")],
                )
                inc_code = f"INC-{a.get('vm_ssh','vm').upper()}-{a.get('metric','SYS').replace(' ','_')}-{time.strftime('%Y%m%d')}"
                neon_query(
                    """
                    INSERT INTO sotc_incidents (incident_code, vm_ssh, title, severity, status, owner, sla_minutes, opened_ts, root_cause)
                    VALUES ($1, $2, $3, $4, 'OPEN', 'SRE On-Call (Vinicius)', $5, $6, $7)
                    ON CONFLICT (incident_code) DO UPDATE
                    SET severity = EXCLUDED.severity,
                        title = EXCLUDED.title
                    """,
                    [
                        inc_code,
                        a.get("vm_ssh", "radar-producao"),
                        a.get("message", "Alerta automático detectado pelo Sentinel"),
                        "CRITICAL" if a.get("severity") == "CRITICAL" else "HIGH",
                        30 if a.get("severity") == "CRITICAL" else 120,
                        now,
                        f"Métrica {a.get('metric')} atingiu {a.get('value')} durante coleta contínua.",
                    ],
                )

        neon_query("DELETE FROM sotc_vm_history WHERE ts < $1", [now - 30 * 86400])
        return {"ok": True, "synced_vms": len(vms_rows), "alerts_logged": len(alerts_rows or []), "ts": now}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def push_vm_telemetry_to_neon(rows):
    """Atalho usado pelo app.py quando uma consulta ocorre no painel local."""
    import platform
    import socket
    from agent import sentinel
    cfg = sentinel.load_agent_config()
    alerts = sentinel.evaluate_alerts(rows, cfg)
    return push_sentinel_cycle_to_neon(
        agent_id=cfg.get("agent_id", "win11-sentinel-01"),
        hostname=socket.gethostname(),
        os_name=f"Windows {platform.release()}",
        interval_sec=int(cfg.get("interval_seconds", 30)),
        vms_rows=rows,
        alerts_rows=alerts,
    )


def fetch_sentinel_status():
    """Retorna estado dos agentes Sentinel, idade do heartbeat (staleness) e alertas recentes."""
    ensure_sotc_neon_schema()
    now = int(time.time())
    agents_raw = neon_query("SELECT * FROM sotc_agents ORDER BY last_epoch DESC")
    alerts_raw = neon_query("SELECT * FROM sotc_alerts ORDER BY id DESC LIMIT 30")

    agents = []
    for a in agents_raw:
        last_ep = int(a.get("last_epoch") or 0)
        age_sec = max(0, now - last_ep) if last_ep else 999999
        if age_sec <= 90:
            comm_state = "ONLINE"
        elif age_sec <= 180:
            comm_state = "ATENÇÃO (STALE)"
        else:
            comm_state = "OFFLINE / DESATUALIZADO"
        agents.append({
            "agent_id": a.get("agent_id", "win11-sentinel-01"),
            "hostname": a.get("hostname", "Windows-11"),
            "os_name": a.get("os_name", "Windows 11"),
            "version": a.get("version", "0.7.0"),
            "interval_sec": int(a.get("interval_sec") or 30),
            "vms_count": int(a.get("vms_count") or 0),
            "age_seconds": age_sec,
            "comm_state": comm_state,
            "last_heartbeat": str(a.get("last_heartbeat", "")),
        })

    return {
        "ok": True,
        "server_time": now,
        "agents": agents,
        "alerts": alerts_raw,
    }


def push_audit_to_neon(alias, action, ok):
    try:
        ensure_sotc_neon_schema()
        neon_query(
            "INSERT INTO sotc_audit_log (ts, alias, action, ok) VALUES ($1, $2, $3, $4)",
            [int(time.time()), str(alias), str(action), bool(ok)],
        )
    except Exception:
        pass


def fetch_vm_snapshots_from_neon():
    ensure_sotc_neon_schema()
    rows = neon_query("SELECT ssh, payload, updated_at FROM sotc_vm_snapshots ORDER BY ssh ASC")
    out = []
    for r in rows:
        p = r.get("payload")
        if isinstance(p, str):
            p = json.loads(p)
        if isinstance(p, dict):
            p["neon_synced_at"] = str(r.get("updated_at", ""))
            out.append(p)
    return out


def fetch_vm_history_from_neon(limit=500):
    ensure_sotc_neon_schema()
    rows = neon_query(
        f"SELECT ts, payload FROM sotc_vm_history ORDER BY ts DESC LIMIT {int(limit)}"
    )
    out = []
    for r in rows:
        p = r.get("payload")
        if isinstance(p, str):
            p = json.loads(p)
        if isinstance(p, dict):
            out.append({"ts": int(r.get("ts", 0)), **p})
    return out


def fetch_audit_from_neon(limit=100):
    ensure_sotc_neon_schema()
    rows = neon_query(
        f"SELECT ts, alias, action, ok FROM sotc_audit_log ORDER BY id DESC LIMIT {int(limit)}"
    )
    return [
        {
            "ts": int(r.get("ts", 0)),
            "alias": r.get("alias", ""),
            "action": r.get("action", ""),
            "ok": bool(r.get("ok")),
        }
        for r in rows
    ]


def match_local_folder(project_name, existing_local_path="", cached_map=None):
    """Procura pasta correspondente localmente ou no mapa sincronizado pelo Sentinel Agent no Neon."""
    if existing_local_path:
        return str(existing_local_path)
    norm = re.sub(r"[^a-z0-9]", "", project_name.lower())
    if not norm:
        return ""
    lmap = cached_map if cached_map is not None else scan_local_projects_map()
    for p_norm, full_path in lmap.items():
        if p_norm == norm or (len(norm) >= 5 and (norm in p_norm or p_norm in norm)):
            return full_path
    return ""


def infer_vm_link(project):
    text = f"{project.get('name', '')} {project.get('description', '')} {project.get('deploy_url', '')}".lower()
    if any(k in text for k in ("radar", "disk", "ingresso", "34.70.140.94", "gcp", "talent")):
        return {
            "vm_ssh": "radar-producao",
            "vm_name": "radar-producao",
            "cloud": "Google Cloud",
            "remote_folder": "/home/develop_diskingressos",
        }
    return None


def fetch_overview():
    """Retorna catálogo de projetos, último log de sync e estatísticas do DevCentral."""
    env = load_devcentral_env()
    projects_raw = neon_query(
        """
        SELECT id, name, description, tech, source, repo_url, deploy_url, state,
               visibility, default_branch, framework, vercel_accounts, deployments,
               last_commit_at, last_deploy_status, is_pinned, is_manual, local_path, tags
        FROM projects
        WHERE is_hidden = false
        ORDER BY is_pinned DESC, COALESCE(last_commit_at, updated_at) DESC, name ASC
        LIMIT 250
        """
    )

    try:
        sync_logs = neon_query(
            "SELECT id, synced_at, github_count, gitlab_count, vercel_count, vercel1_count, vercel2_count, status, details FROM sync_logs ORDER BY synced_at DESC LIMIT 1"
        )
    except Exception:
        sync_logs = []

    cached_local_map = scan_local_projects_map()
    if not cached_local_map:
        try:
            ag = neon_query("SELECT local_projects FROM sotc_agents ORDER BY last_epoch DESC LIMIT 1")
            if ag and ag[0].get("local_projects"):
                lp = ag[0]["local_projects"]
                cached_local_map = json.loads(lp) if isinstance(lp, str) else lp
        except Exception:
            cached_local_map = {}

    projects = []
    for r in projects_raw:
        deployments = r.get("deployments") or []
        if isinstance(deployments, str):
            try:
                deployments = json.loads(deployments)
            except ValueError:
                deployments = []
        vercel_accounts = r.get("vercel_accounts") or []
        if isinstance(vercel_accounts, str):
            vercel_accounts = [x for x in vercel_accounts.strip("{}").split(",") if x]

        local_dir = match_local_folder(r.get("name", ""), r.get("local_path", ""), cached_local_map)
        vm_link = infer_vm_link(r)

        projects.append({
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "description": r.get("description") or "",
            "tech": r.get("tech") or "Outro",
            "source": r.get("source") or "GitHub",
            "repo_url": r.get("repo_url") or "",
            "deploy_url": r.get("deploy_url") or "",
            "state": r.get("state") or "dev",
            "visibility": r.get("visibility") or "public",
            "branch": r.get("default_branch") or "main",
            "framework": r.get("framework") or "",
            "vercel_accounts": vercel_accounts,
            "deployments": deployments,
            "last_commit_at": r.get("last_commit_at") or "",
            "last_deploy_status": r.get("last_deploy_status") or "",
            "is_pinned": bool(r.get("is_pinned")),
            "local_path": local_dir,
            "vm_link": vm_link,
        })

    summary = {
        "total": len(projects),
        "github": sum(1 for p in projects if "github" in p["source"].lower()),
        "gitlab": sum(1 for p in projects if "gitlab" in p["source"].lower()),
        "with_deploy": sum(1 for p in projects if p["deploy_url"] or p["deployments"]),
        "linked_to_vm": sum(1 for p in projects if p["vm_link"]),
        "local_found": sum(1 for p in projects if p["local_path"]),
        "account1_name": env.get("VERCEL_ACCOUNT_1_NAME", "Vercel Conta 1"),
        "account2_name": env.get("VERCEL_ACCOUNT_2_NAME", "Vercel Conta 2"),
        "last_sync": sync_logs[0] if sync_logs else None,
    }

    return {
        "ok": True,
        "summary": summary,
        "projects": projects,
    }


def check_http_health(url):
    if not url or not isinstance(url, str):
        raise ValueError("URL inválida")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Apenas URLs HTTP/HTTPS válidas são permitidas")

    start = time.monotonic()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SignOfTheCross-HealthProbe/0.7.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            ms = round((time.monotonic() - start) * 1000)
            return {
                "ok": 200 <= resp.status < 400,
                "status": resp.status,
                "latency_ms": ms,
                "url": url,
            }
    except urllib.error.HTTPError as e:
        ms = round((time.monotonic() - start) * 1000)
        return {
            "ok": False,
            "status": e.code,
            "latency_ms": ms,
            "url": url,
            "error": f"HTTP {e.code}",
        }
    except Exception as e:
        ms = round((time.monotonic() - start) * 1000)
        return {
            "ok": False,
            "status": 0,
            "latency_ms": ms,
            "url": url,
            "error": str(e)[:140],
        }
