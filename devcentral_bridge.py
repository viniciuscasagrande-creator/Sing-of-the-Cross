import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEVCENTRAL_DIR = Path(r"D:\Projetos Vs Code\DevCentral")
LOCAL_PROJECTS_ROOT = Path(r"D:\Projetos Vs Code")


def load_devcentral_env():
    """Lê variáveis de D:\\Projetos Vs Code\\DevCentral\\.env.local em memória sem expor segredos."""
    env = {}
    env_file = DEVCENTRAL_DIR / ".env.local"
    if not env_file.exists():
        return env
    for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def neon_query(query, params=None):
    """Executa SQL direto no endpoint HTTP do Neon Serverless usando biblioteca padrão Python."""
    env = load_devcentral_env()
    db_url = env.get("DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise ValueError("DATABASE_URL do DevCentral não encontrada em .env.local")

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
            "User-Agent": "SingOfTheCross-TheGrimoire/0.6.5",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("rows", [])


def match_local_folder(project_name, existing_local_path=""):
    """Procura pasta correspondente em D:\\Projetos Vs Code para abertura direta no VS Code."""
    if existing_local_path and Path(existing_local_path).exists():
        return str(Path(existing_local_path))
    if not LOCAL_PROJECTS_ROOT.exists():
        return ""
    norm = re.sub(r"[^a-z0-9]", "", project_name.lower())
    if not norm:
        return ""
    try:
        for p in LOCAL_PROJECTS_ROOT.iterdir():
            if p.is_dir():
                p_norm = re.sub(r"[^a-z0-9]", "", p.name.lower())
                if p_norm == norm or (len(norm) >= 5 and (norm in p_norm or p_norm in norm)):
                    return str(p)
    except OSError:
        pass
    return ""


def infer_vm_link(project):
    """Associa automaticamente projetos relacionados ao Radar/GCP com a VM radar-producao."""
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
    """Retorna catálogo de projetos, último log de sync, recomendações e estatísticas do DevCentral."""
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

    try:
        recs = neon_query(
            "SELECT id, project_name, platform_label, severity, kind, title, status FROM telemetry_recommendations ORDER BY updated_at DESC LIMIT 12"
        )
    except Exception:
        recs = []

    try:
        tasks = neon_query(
            "SELECT id, project_name, title, priority, status, assignee FROM project_tasks ORDER BY updated_at DESC LIMIT 12"
        )
    except Exception:
        tasks = []

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

        local_dir = match_local_folder(r.get("name", ""), r.get("local_path", ""))
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
        "recommendations": recs,
        "tasks": tasks,
    }


def check_http_health(url):
    """Verifica a disponibilidade e latência HTTP de um deploy_url do DevCentral."""
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
        headers={"User-Agent": "SingOfTheCross-HealthProbe/0.6.5"},
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
