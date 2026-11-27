"""
Sing Of The Cross (SOTC) - Vercel Serverless Cloud Handler (V1.0 The Throne & Mobile APK)
Lê a telemetria espelhada das VMs, o status do Sentinel Agent (heartbeat/alertas),
os 7 Dashboards Executivos e os 42 projetos do DevCentral diretamente do Neon PostgreSQL.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
for _path_item in (str(ROOT), str(BACKEND_DIR)):
    if _path_item not in sys.path:
        sys.path.insert(0, _path_item)

from backend import devcentral_bridge  # pylint: disable=wrong-import-position
from backend import oracle  # pylint: disable=wrong-import-position


class handler(BaseHTTPRequestHandler):  # pylint: disable=invalid-name
    """Vercel Serverless HTTP Request Handler para o Cloud Mirror e APK Mobile do SOTC."""

    def send_data(self, data, kind="application/json; charset=utf-8", status=200):
        """Envia resposta HTTP com cabeçalhos de segurança e controle de cache."""
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # pylint: disable=invalid-name
        """Processa requisições GET de interface, assets, APK e telemetria Neon."""
        path = urlparse(self.path).path
        assets_dir = ROOT / "frontend" / "assets"
        apk_type = "application/vnd.android.package-archive"
        try:
            if path in ("/", "/index.html"):
                html_bytes = (ROOT / "frontend" / "index.html").read_bytes()
                self.send_data(html_bytes, "text/html; charset=utf-8")
            elif path == "/gothic.css":
                css_bytes = (ROOT / "frontend" / "gothic.css").read_bytes()
                self.send_data(css_bytes, "text/css; charset=utf-8")
            elif path == "/background.jpg":
                bg_bytes = (assets_dir / "background.jpg").read_bytes()
                self.send_data(bg_bytes, "image/jpeg")
            elif path == "/logo.png":
                logo_bytes = (assets_dir / "logo.png").read_bytes()
                self.send_data(logo_bytes, "image/png")
            elif path == "/sotc.ico":
                ico_bytes = (assets_dir / "sotc.ico").read_bytes()
                self.send_data(ico_bytes, "image/x-icon")
            elif path in ("/SingOfTheCross.apk", "/SOTC-Monitor-v1.0.0.apk"):
                apk_file = assets_dir / "SOTC-Monitor-v1.0.0.apk"
                if not apk_file.exists():
                    apk_file = assets_dir / "SingOfTheCross.apk"
                self.send_data(apk_file.read_bytes(), apk_type)
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
            elif path in (
                "/api/sentinel/heartbeat",
                "/api/sentinel/alerts",
                "/api/sentinel/telemetry",
            ):
                data = devcentral_bridge.fetch_sentinel_status()
                self.send_data(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/oracle":
                rows = devcentral_bridge.fetch_vm_snapshots_from_neon()
                data = oracle.analyze_infrastructure(rows)
                self.send_data(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/command-center":
                rows = devcentral_bridge.fetch_vm_snapshots_from_neon()
                try:
                    dc_ov = devcentral_bridge.fetch_overview()
                except (ValueError, OSError, RuntimeError):
                    dc_ov = {}
                try:
                    sent_st = devcentral_bridge.fetch_sentinel_status()
                except (ValueError, OSError, RuntimeError):
                    sent_st = {}
                try:
                    aud = devcentral_bridge.fetch_audit_from_neon(50)
                except (ValueError, OSError, RuntimeError):
                    aud = []
                suite = oracle.build_command_center_suite(rows, dc_ov, sent_st, aud)
                self.send_data(json.dumps(suite, ensure_ascii=False).encode("utf-8"))
            elif path == "/api/aliases":
                self.send_data(b'["radar-producao"]')
            else:
                self.send_error(404)
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
            err_payload = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_data(err_payload, status=500)

    def do_POST(self):  # pylint: disable=invalid-name
        """Processa verificações HTTP de saúde e bloqueia intervenções SSH no Cloud Mirror."""
        path = urlparse(self.path).path
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            item = json.loads(raw_body)
            if path == "/api/devcentral/health":
                res = devcentral_bridge.check_http_health(item.get("url", ""))
                self.send_data(json.dumps(res, ensure_ascii=False).encode("utf-8"))
                return
            msg = (
                "Modo Cloud Mirror / Mobile: Intervenções diretas de energia/SSH "
                "exigem confirmação no Cockpit Local Windows 11 (127.0.0.1:8765)."
            )
            err_resp = json.dumps({"ok": False, "error": msg}, ensure_ascii=False)
            self.send_data(err_resp.encode("utf-8"), status=403)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            err_payload = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_data(err_payload, status=400)
