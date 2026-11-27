"""
Sing Of The Cross (SOTC) - Vercel Serverless Cloud Handler (Modo Cloud Mirror)
Lê a telemetria espelhada das VMs (sotc_vm_snapshots / sotc_vm_history) e os 42 projetos
diretamente do banco Neon PostgreSQL usando DATABASE_URL, sem expor chaves SSH na nuvem.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import devcentral_bridge


class handler(BaseHTTPRequestHandler):
    def send_data(self, data, kind="application/json; charset=utf-8", status=200):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                self.send_data((ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/gothic.css":
                self.send_data((ROOT / "gothic.css").read_bytes(), "text/css; charset=utf-8")
            elif path == "/background.jpg":
                self.send_data((ROOT / "background.jpg").read_bytes(), "image/jpeg")
            elif path == "/logo.png":
                self.send_data((ROOT / "logo.png").read_bytes(), "image/png")
            elif path == "/api/status":
                rows = devcentral_bridge.fetch_vm_snapshots_from_neon()
                self.send_data(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/history":
                rows = devcentral_bridge.fetch_vm_history_from_neon(500)
                self.send_data(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/guardian/events":
                rows = devcentral_bridge.fetch_audit_from_neon(100)
                self.send_data(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/devcentral":
                data = devcentral_bridge.fetch_overview()
                self.send_data(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/aliases":
                self.send_data(b'["radar-producao"]')
            else:
                self.send_error(404)
        except Exception as e:
            self.send_data(json.dumps({"error": str(e)}).encode("utf-8"), status=500)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length", "0"))
            item = json.loads(self.rfile.read(n)) if n > 0 else {}
            if path == "/api/devcentral/health":
                res = devcentral_bridge.check_http_health(item.get("url", ""))
                self.send_data(json.dumps(res, ensure_ascii=False).encode("utf-8"))
                return
            self.send_data(
                json.dumps({
                    "ok": False,
                    "error": "Modo Cloud Mirror (Vercel): Intervenções SSH/Power são exclusivas do Cockpit Local no Windows 11 (127.0.0.1:8765)."
                }, ensure_ascii=False).encode("utf-8"),
                status=403,
            )
        except Exception as e:
            self.send_data(json.dumps({"error": str(e)}).encode("utf-8"), status=400)
