"""
Cloud VM Monitor - Versão Python + Streamlit
Execute com: streamlit run streamlit_app.py
Compartilha o mesmo arquivo de configuração vms.json com o servidor Node.js.
"""

import json
import subprocess
from pathlib import Path
import streamlit as st

CONFIG_PATH = Path(__file__).parent / "vms.json"

REMOTE_PROBE_CMD = (
    'export LC_ALL=C; '
    'CPU=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk \'{print 100 - $8}\' | cut -d. -f1); '
    'RAM=$(free -m 2>/dev/null | awk \'/Mem:/ { printf("%d", ($3/$2)*100) }\'); '
    'DISK=$(df -h / 2>/dev/null | awk \'NR==2 {gsub("%","",$5); print $5}\'); '
    'EXT_HOST=$(ps aux 2>/dev/null | grep -E "(vscode-server|antigravity-server).*extensionHost|node.*bootstrap-fork.*--type=extensionHost" | grep -v grep | wc -l); '
    'echo "CPU=${CPU:-0}|RAM=${RAM:-0}|DISK=${DISK:-0}|EXT_HOST=${EXT_HOST:-0}"'
)


def load_config():
    if not CONFIG_PATH.exists():
        return {"refreshIntervalSeconds": 10, "vms": []}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def check_vm(vm: dict) -> dict:
    if vm.get("demoMode"):
        st_data = vm.get("demoState", {})
        return {
            "vmOnline": bool(st_data.get("vmOnline")),
            "vscodeConnected": bool(st_data.get("vscodeConnected")),
            "activeSessions": st_data.get("activeSessions", 1 if st_data.get("vscodeConnected") else 0),
            "cpu": st_data.get("cpu", 0),
            "ram": st_data.get("ram", 0),
            "disk": st_data.get("disk", 0),
        }

    target = f"{vm.get('user', 'ubuntu')}@{vm['host']}"
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=4",
        "-p", str(vm.get("port", 22)),
        target,
        REMOTE_PROBE_CMD,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        if proc.returncode != 0:
            return {"vmOnline": False, "vscodeConnected": False, "activeSessions": 0, "cpu": 0, "ram": 0, "disk": 0}
        kv = dict(item.split("=", 1) for item in proc.stdout.strip().split("|") if "=" in item)
        ext = int(kv.get("EXT_HOST", 0))
        return {
            "vmOnline": True,
            "vscodeConnected": ext > 0,
            "activeSessions": ext,
            "cpu": int(kv.get("CPU", 0)),
            "ram": int(kv.get("RAM", 0)),
            "disk": int(kv.get("DISK", 0)),
        }
    except Exception:
        return {"vmOnline": False, "vscodeConnected": False, "activeSessions": 0, "cpu": 0, "ram": 0, "disk": 0}


st.set_page_config(page_title="Cloud VM Monitor", page_icon="☁️", layout="wide")
st.title("☁️ Cloud VM Monitor")
st.caption("Painel de conexões VS Code (Multi-Cloud • Remote SSH & Tunnels)")

cfg = load_config()
vms = cfg.get("vms", [])
statuses = [(vm, check_vm(vm)) for vm in vms]

total = len(statuses)
connected = sum(1 for _, s in statuses if s["vmOnline"] and s["vscodeConnected"])
disconnected = total - connected

c1, c2, c3 = st.columns(3)
c1.metric("Total de VMs", total)
c2.metric("Conectadas", connected)
c3.metric("Desconectadas", disconnected)

st.divider()

cols = st.columns(2)
for idx, (vm, st_info) in enumerate(statuses):
    with cols[idx % 2]:
        with st.container(border=True):
            if st_info["vmOnline"] and st_info["vscodeConnected"]:
                badge = "🟢 **Online** • VS Code **Conectado**"
            elif st_info["vmOnline"]:
                badge = "🟡 **Online** • VS Code **Desconectado**"
            else:
                badge = "🔴 **Offline** • VS Code **Desconectado**"

            st.subheader(f"{vm['name']} (`{vm['host']}`)")
            st.markdown(badge)

            if st_info["vmOnline"]:
                m1, m2, m3 = st.columns(3)
                m1.progress(st_info["cpu"] / 100.0, text=f"CPU: {st_info['cpu']}%")
                m2.progress(st_info["ram"] / 100.0, text=f"RAM: {st_info['ram']}%")
                m3.progress(st_info["disk"] / 100.0, text=f"Disco: {st_info['disk']}%")

            ws = vm.get("workspacePath", f"/home/{vm.get('user', 'ubuntu')}").lstrip("/")
            if vm.get("connectionType") == "tunnel" and vm.get("tunnelName"):
                uri = f"vscode://vscode-remote/tunnel+{vm['tunnelName']}/{ws}"
            else:
                uri = f"vscode://vscode-remote/ssh-remote+{vm.get('user', 'ubuntu')}@{vm['host']}/{ws}"
            st.link_button("💻 Abrir no VS Code", uri)
