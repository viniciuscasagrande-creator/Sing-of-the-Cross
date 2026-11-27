import concurrent.futures
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
VMS_FILE = ROOT / "vms.json"
LOGO_FILE = ROOT / "logo.png"
BG_FILE = ROOT / "gothic_bg.jpg"
INDEX_FILE = ROOT / "index.html"
DB_FILE = ROOT / "sotc.db"

VALID_CLOUDS = ("Google Cloud", "AWS", "Azure", "Oracle Cloud")

REMOTE_PROBE_SCRIPT = (
    "export LC_ALL=C; "
    "if ps -eo args 2>/dev/null | grep -E '[.]vscode-server|[.]vscode-remote|[.]vscode-server-insiders|[.]antigravity-server|code-tunnel' >/dev/null; "
    "then SRV='present'; else SRV='not_detected'; fi; "
    "SESS=$(ps -eo args 2>/dev/null | grep -E '(vscode-server|antigravity-server).*extensionHost|bootstrap-fork.*--type=extensionHost' | grep -v grep | wc -l); "
    "SSH_PTS=$(who 2>/dev/null | wc -l); "
    "CPU=$(top -bn1 2>/dev/null | grep 'Cpu(s)' | awk '{print int(100 - $8)}'); "
    "RAM=$(free -m 2>/dev/null | awk '/Mem:/ { printf(\"%d\", ($3/$2)*100) }'); "
    "RAM_DETAIL=$(free -m 2>/dev/null | awk '/Mem:/ { printf(\"%dMB / %dMB\", $3, $2) }'); "
    "DISK=$(df -h / 2>/dev/null | awk 'NR==2 {gsub(\"%\",\"\",$5); print $5}'); "
    "DISK_DETAIL=$(df -h / 2>/dev/null | awk 'NR==2 {printf(\"%s / %s\", $3, $2)}'); "
    "UPT=$(uptime -p 2>/dev/null | sed 's/up //'); "
    "OS=$(grep -E '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"'); "
    "echo \"SOTC_SRV=${SRV}|SOTC_SESS=${SESS:-0}|SOTC_PTS=${SSH_PTS:-0}|SOTC_CPU=${CPU:-0}|SOTC_RAM=${RAM:-0}|SOTC_RAM_D=${RAM_DETAIL}|SOTC_DISK=${DISK:-0}|SOTC_DISK_D=${DISK_DETAIL}|SOTC_UPT=${UPT:-Online}|SOTC_OS=${OS:-Linux}\""
)


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vm_id TEXT,
                vm_name TEXT,
                cloud TEXT,
                state_badge TEXT,
                cloud_status TEXT,
                ssh_status TEXT,
                server_status TEXT,
                session_status TEXT,
                cpu INTEGER,
                ram INTEGER,
                disk INTEGER,
                checked_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vm_id TEXT,
                vm_name TEXT,
                severity TEXT,
                message TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()


def record_telemetry(result):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                """
                INSERT INTO telemetry_history
                (vm_id, vm_name, cloud, state_badge, cloud_status, ssh_status, server_status, session_status, cpu, ram, disk, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.get("id", ""),
                    result.get("name", ""),
                    result.get("cloud", ""),
                    result.get("state_badge", "UNKNOWN"),
                    result.get("cloud_status", "UNKNOWN"),
                    result.get("ssh_status", "unknown"),
                    result.get("server_status", "unknown"),
                    result.get("session_status", "disconnected"),
                    int(result.get("cpu", 0)),
                    int(result.get("ram", 0)),
                    int(result.get("disk", 0)),
                    result.get("checked", time.strftime("%Y-%m-%d %H:%M:%S")),
                ),
            )
            conn.execute("DELETE FROM telemetry_history WHERE id NOT IN (SELECT id FROM telemetry_history ORDER BY id DESC LIMIT 100)")

            if result.get("ssh_status") != "ok":
                conn.execute(
                    "INSERT INTO alerts (vm_id, vm_name, severity, message, created_at) VALUES (?, ?, ?, ?, ?)",
                    (result.get("id"), result.get("name"), "CRITICAL", result.get("detail", "Falha SSH"), result.get("checked")),
                )
            elif int(result.get("cpu", 0)) >= 85 or int(result.get("ram", 0)) >= 85 or int(result.get("disk", 0)) >= 85:
                conn.execute(
                    "INSERT INTO alerts (vm_id, vm_name, severity, message, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        result.get("id"),
                        result.get("name"),
                        "CRITICAL" if int(result.get("disk", 0)) >= 85 else "WARNING",
                        f"Alerta de recursos em {result.get('name')}: CPU {result.get('cpu')}%, RAM {result.get('ram')}%, Disco {result.get('disk')}%",
                        result.get("checked"),
                    ),
                )
            conn.execute("DELETE FROM alerts WHERE id NOT IN (SELECT id FROM alerts ORDER BY id DESC LIMIT 30)")
            conn.commit()
    except Exception:
        pass


def get_recent_history():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM telemetry_history ORDER BY id DESC LIMIT 20").fetchall()
            alerts = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 10").fetchall()
            return {
                "history": [dict(r) for r in rows],
                "alerts": [dict(a) for a in alerts],
            }
    except Exception:
        return {"history": [], "alerts": []}


def inventory():
    if not VMS_FILE.exists():
        return []
    data = json.loads(VMS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("vms.json deve conter uma lista")
    for vm in data:
        ssh_target = vm.get("ssh", "")
        if not re.fullmatch(r"[A-Za-z0-9_@][A-Za-z0-9_.@-]*", ssh_target):
            raise ValueError("Alias/Host SSH inválido: " + str(ssh_target))
        if vm.get("cloud") not in VALID_CLOUDS:
            vm["cloud"] = "Google Cloud"
    return data


def save_inventory(data):
    VMS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def check_local_windows_ssh_processes():
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name = 'ssh.exe'\" | Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if p.returncode == 0 and p.stdout.strip():
            raw = json.loads(p.stdout.strip())
            return raw if isinstance(raw, list) else [raw]
    except Exception:
        pass
    return []


def check_gcloud_instance_status(vm):
    if vm.get("cloud") != "Google Cloud" or not vm.get("project") or not vm.get("zone"):
        return "UNKNOWN"
    gcloud_bin = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud_bin:
        return "UNKNOWN"
    try:
        p = subprocess.run(
            [
                gcloud_bin,
                "compute",
                "instances",
                "describe",
                vm["name"],
                f"--project={vm['project']}",
                f"--zone={vm['zone']}",
                "--format=value(status)",
            ],
            capture_output=True,
            text=True,
            timeout=7,
        )
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip().upper()
    except Exception:
        pass
    return "RUNNING" if vm.get("host") else "UNKNOWN"


def parse_ssh_environment():
    ssh_dir = Path.home() / ".ssh"
    discovered = []
    seen = set()

    cfg_path = ssh_dir / "config"
    cfg_content = ""
    if cfg_path.exists():
        cfg_content = cfg_path.read_text(encoding="utf-8", errors="ignore")
        current = None
        for raw in cfg_content.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            k, v = parts[0].lower(), parts[1].strip().strip('"')
            if k == "host":
                if current and current["ssh"] not in seen and "*" not in current["ssh"]:
                    seen.add(current["ssh"])
                    discovered.append(current)
                current = {
                    "name": v,
                    "ssh": v,
                    "host": v,
                    "user": "vinad",
                    "port": 22,
                    "identity_file": "~/.ssh/google_compute_engine",
                    "source": "~/.ssh/config",
                }
            elif current:
                if k == "hostname":
                    current["host"] = v
                elif k == "user":
                    current["user"] = v
                elif k == "port":
                    current["port"] = int(v) if v.isdigit() else 22
                elif k == "identityfile":
                    current["identity_file"] = v
        if current and current["ssh"] not in seen and "*" not in current["ssh"]:
            seen.add(current["ssh"])
            discovered.append(current)

    keys = [p.name for p in ssh_dir.glob("*") if p.is_file() and not p.name.endswith((".pub", ".ppk", "known_hosts", "config"))] if ssh_dir.exists() else []
    local_procs = check_local_windows_ssh_processes()
    return {
        "os": "Windows 11",
        "has_ssh_config": cfg_path.exists(),
        "ssh_config_path": str(cfg_path),
        "ssh_config_content": cfg_content,
        "keys_found": keys,
        "local_ssh_processes": local_procs,
        "discovered_hosts": discovered,
    }


def probe(vm):
    checked_time = time.strftime("%H:%M:%S")
    local_procs = check_local_windows_ssh_processes()
    local_match = any(
        (vm.get("ssh", "") in (proc.get("CommandLine") or ""))
        or (vm.get("host", "") in (proc.get("CommandLine") or ""))
        for proc in local_procs
    )

    out = dict(
        vm,
        state_badge="UNKNOWN",
        cloud_status="UNKNOWN",
        ssh_status="unknown",
        server_status="unknown",
        session_status="disconnected",
        active_sessions=0,
        ssh_pts=0,
        local_ssh_tunnel=local_match,
        cpu=0,
        ram=0,
        ram_detail="",
        disk=0,
        disk_detail="",
        uptime="Offline",
        os_name="Linux",
        detail="",
        checked=checked_time,
    )

    if not shutil.which("ssh"):
        out["detail"] = "Cliente OpenSSH não encontrado no PATH"
        return out

    target = vm.get("ssh") or vm.get("host")
    if vm.get("user") and "@" not in target and vm.get("host"):
        target = f"{vm['user']}@{vm['host']}"

    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=5",
        "-o", "ConnectionAttempts=1",
        "-o", "ClearAllForwardings=yes",
        "-o", "RequestTTY=no",
    ]
    if vm.get("port") and int(vm["port"]) != 22:
        cmd.extend(["-p", str(vm["port"])])
    if vm.get("identity_file"):
        key_path = os.path.expanduser(vm["identity_file"])
        if os.path.exists(key_path):
            cmd.extend(["-i", key_path])

    cmd.extend([target, REMOTE_PROBE_SCRIPT])

    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if p.returncode == 0:
            out["ssh_status"] = "ok"
            out["cloud_status"] = "RUNNING"
            kv = {}
            for line in p.stdout.splitlines():
                if "SOTC_SRV=" in line:
                    for item in line.split("|"):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            kv[k.strip()] = v.strip()
            out["server_status"] = kv.get("SOTC_SRV", "not_detected")
            sess_count = int(kv.get("SOTC_SESS", "0") or 0)
            pts_count = int(kv.get("SOTC_PTS", "0") or 0)
            out["active_sessions"] = sess_count
            out["ssh_pts"] = pts_count

            # Determina os 5 estados oficiais: CONNECTED, STANDBY, OFFLINE, CONNECTING, UNKNOWN
            if sess_count > 0 or local_match:
                out["session_status"] = "active"
                out["state_badge"] = "CONNECTED"
            else:
                out["session_status"] = "idle" if out["server_status"] == "present" else "disconnected"
                out["state_badge"] = "STANDBY"

            out["cpu"] = int(kv.get("SOTC_CPU", "0") or 0)
            out["ram"] = int(kv.get("SOTC_RAM", "0") or 0)
            out["ram_detail"] = kv.get("SOTC_RAM_D", "")
            out["disk"] = int(kv.get("SOTC_DISK", "0") or 0)
            out["disk_detail"] = kv.get("SOTC_DISK_D", "")
            out["uptime"] = kv.get("SOTC_UPT", "Online")
            out["os_name"] = kv.get("SOTC_OS", "Linux")

            if out["state_badge"] == "CONNECTED":
                out["detail"] = f"CONNECTED • Sessão VS Code ativa ({sess_count or 1}) • Uptime: {out['uptime']}"
            else:
                out["detail"] = f"STANDBY • VM Online ({out['os_name']}) • VS Code Server pronto • Uptime: {out['uptime']}"
        else:
            out["ssh_status"] = "failed"
            out["cloud_status"] = check_gcloud_instance_status(vm)
            out["state_badge"] = "OFFLINE" if out["cloud_status"] in ("TERMINATED", "STOPPED") else "UNKNOWN"
            err_msg = p.stderr.strip().splitlines()[-1][:160] if p.stderr.strip() else "falha na conexão remota"
            out["detail"] = "SSH não confirmado: " + err_msg
    except (subprocess.TimeoutExpired, OSError):
        out["ssh_status"] = "failed"
        out["cloud_status"] = check_gcloud_instance_status(vm)
        out["state_badge"] = "OFFLINE"
        out["detail"] = "Tempo limite esgotado (Timeout SSH)"

    record_telemetry(out)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_data(self, data, kind="application/json; charset=utf-8", status=200):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/":
                self.send_data(INDEX_FILE.read_bytes(), "text/html; charset=utf-8")
            elif path == "/logo.png":
                self.send_data(LOGO_FILE.read_bytes(), "image/png")
            elif path == "/gothic_bg.jpg" and BG_FILE.exists():
                self.send_data(BG_FILE.read_bytes(), "image/jpeg")
            elif path == "/api/status":
                vms = inventory()
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(probe, vms))
                self.send_data(json.dumps(results, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/ssh-discovery":
                info = parse_ssh_environment()
                self.send_data(json.dumps(info, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/history":
                self.send_data(json.dumps(get_recent_history(), ensure_ascii=False).encode("utf-8"))
            else:
                self.send_error(404)
        except Exception as e:
            self.send_data(json.dumps({"error": str(e)}).encode("utf-8"), status=500)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self.read_json()
            vms = inventory()

            if path == "/api/vms":
                vm_id = body.get("id") or f"SOTC-VM-{len(vms)+1:03d}"
                new_vm = {
                    "id": vm_id,
                    "name": (body.get("name") or "nova-vm").strip(),
                    "cloud": body.get("cloud") if body.get("cloud") in VALID_CLOUDS else "Google Cloud",
                    "project": (body.get("project") or "").strip(),
                    "region": (body.get("region") or "").strip(),
                    "zone": (body.get("zone") or "").strip(),
                    "environment": (body.get("environment") or "Produção").strip(),
                    "ssh": (body.get("ssh") or body.get("host") or "localhost").strip(),
                    "host": (body.get("host") or body.get("ssh") or "localhost").strip(),
                    "user": (body.get("user") or "vinad").strip(),
                    "port": int(body.get("port") or 22),
                    "identity_file": (body.get("identity_file") or "~/.ssh/google_compute_engine").strip(),
                    "workspace": (body.get("workspace") or f"/home/{body.get('user') or 'vinad'}").strip(),
                    "mode": "real",
                }
                idx = next((i for i, item in enumerate(vms) if item.get("id") == vm_id or item.get("name") == new_vm["name"]), -1)
                if idx >= 0:
                    vms[idx] = {**vms[idx], **new_vm}
                else:
                    vms.append(new_vm)
                save_inventory(vms)
                self.send_data(json.dumps({"ok": True, "vm": new_vm}, ensure_ascii=False).encode("utf-8"))

            elif path == "/api/vms/delete":
                target_id = body.get("id")
                vms = [item for item in vms if item.get("id") != target_id and item.get("name") != target_id]
                save_inventory(vms)
                self.send_data(json.dumps({"ok": True}).encode("utf-8"))

            elif path == "/api/open-vscode":
                ssh_alias = body.get("ssh") or "radar-producao"
                workspace = body.get("workspace") or "/home/vinad"
                subprocess.Popen(
                    f'code --remote "ssh-remote+{ssh_alias}" "{workspace}"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.send_data(json.dumps({"ok": True}).encode("utf-8"))
            else:
                self.send_error(404)
        except Exception as e:
            self.send_data(json.dumps({"error": str(e)}).encode("utf-8"), status=400)


if __name__ == "__main__":
    init_db()
    print("=====================================================")
    print("  SING OF THE CROSS (SOTC) - DARK GOTHIC CINEMATIC")
    print("  URL: http://127.0.0.1:8765")
    print("=====================================================")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
