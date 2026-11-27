"""
SING OF THE CROSS (SOTC) — V0.8 THE ORACLE & V0.9 THE ABYSS
Motor de Análise Inteligente, Diagnóstico Profundo de Disco/Logs,
Estimativa de Custos Multi-Cloud e Runbooks Controlados (Somente-Leitura + Limpeza Segura).
"""
import guardian

CLOUD_COST_ESTIMATES_USD = {
    "e2-micro": 7.11,
    "e2-small": 14.23,
    "e2-medium": 28.46,
    "n1-standard-1": 34.67,
    "t3.micro": 8.47,
    "t3.small": 16.93,
    "t3.medium": 33.87,
    "Standard_B1s": 8.76,
    "Standard_B2s": 35.04,
    "VM.Standard.E2.1.Micro": 0.00,
}

ABYSS_PROBES = {
    "disk_hotspots": (
        "echo '=== USO DO DISCO RAIZ ==='; df -h /; "
        "echo ''; echo '=== TOP DIRETÓRIOS EM /var ==='; sudo -n du -xhd1 /var 2>/dev/null | sort -hr | head -10 || du -xhd1 /var 2>/dev/null | sort -hr | head -10; "
        "echo ''; echo '=== TAMANHO DOS LOGS SYSTEMD (JOURNAL) ==='; journalctl --disk-usage 2>/dev/null; "
        "echo ''; echo '=== CACHE APT & DOCKER ==='; du -sh /var/cache/apt/archives /var/lib/docker 2>/dev/null || true; "
        "echo ''; echo '=== USO EM /home ==='; sudo -n du -sh /home/* 2>/dev/null || du -sh /home/* 2>/dev/null"
    ),
    "critical_logs": "journalctl -n 80 --no-pager -p err..alert 2>/dev/null || journalctl -n 80 --no-pager",
    "auth_security": "grep -E 'Failed|Accepted|Invalid' /var/log/auth.log 2>/dev/null | tail -35 || journalctl -u ssh -u sshd -n 35 --no-pager 2>/dev/null",
    "docker_containers": "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || sudo -n crictl ps 2>/dev/null || echo 'Nenhum container Docker visível para este usuário'",
    "top_memory": "ps -eo pid,user,%mem,%cpu,rss,comm --sort=-%mem | head -20",
}

SAFE_RUNBOOKS = {
    "vacuum_journal": "sudo -n journalctl --vacuum-size=100M && sudo -n apt-get clean && df -h /",
}


def analyze_infrastructure(vms_rows, projects_summary=None):
    """Gera recomendações inteligentes do The Oracle cruzando telemetria das VMs e projetos."""
    insights = []
    total_monthly_usd = 0.0

    for vm in vms_rows:
        name = vm.get("name") or vm.get("ssh") or "VM"
        cloud = vm.get("cloud", "Google Cloud")
        mtype = vm.get("machine_type") or ("e2-medium" if cloud == "Google Cloud" else "t3.small")
        est_usd = CLOUD_COST_ESTIMATES_USD.get(mtype, 28.46)
        total_monthly_usd += est_usd

        if vm.get("ssh_status") != "ok":
            insights.append({
                "vm": name,
                "severity": "CRITICAL",
                "category": "Conectividade SSH",
                "title": f"Inacessibilidade SSH em {name} ({cloud})",
                "recommendation": "Verifique se a instância está RUNNING no console da cloud, se o IP externo mudou ou se a regra de firewall TCP/22 permite conexão.",
            })
            continue

        disk_raw = vm.get("disk_pct")
        try:
            disk_val = float(str(disk_raw).replace("%", "")) if disk_raw else 0.0
        except ValueError:
            disk_val = 0.0

        if disk_val >= 75:
            insights.append({
                "vm": name,
                "severity": "CRITICAL" if disk_val >= 90 else "WARNING",
                "category": "Armazenamento & Disco Raiz",
                "title": f"Disco raiz de {name} em {disk_val}% (Atenção Operacional)",
                "recommendation": "Execute a sonda 'Raio-X de Espaço em Disco (86%)' no módulo The Abyss abaixo para identificar logs do systemd (journald) ou cache APT acumulando espaço, ou acione o Runbook 'Limpar Journald & Cache APT'.",
            })

        cpu_val = float(vm.get("cpu_pct") or 0)
        ram_val = float(vm.get("ram_pct") or 0)
        if cpu_val < 15 and ram_val < 40:
            insights.append({
                "vm": name,
                "severity": "INFO",
                "category": "Eficiência & FinOps",
                "title": f"{name} opera com folga de recursos (CPU {cpu_val}%, RAM {ram_val}%)",
                "recommendation": f"Instância {mtype} (~US$ {est_usd:.2f}/mês) está saudável e dimensionada com margem segura para picos dos workers Node.js.",
            })

        lat_val = float(vm.get("latency_ms") or 0)
        if lat_val >= 250:
            insights.append({
                "vm": name,
                "severity": "WARNING",
                "category": "Rede & Latência",
                "title": f"Handshake SSH elevado ({int(lat_val)} ms) entre Windows 11 e {vm.get('zone', cloud)}",
                "recommendation": "A latência de abertura de nova sessão SSH inclui negociação criptográfica entre Brasil e us-central1-a. Use multiplexação SSH ou mantenha a janela do VS Code Remote-SSH aberta.",
            })

    return {
        "ok": True,
        "estimated_monthly_usd": round(total_monthly_usd, 2),
        "estimated_monthly_brl": round(total_monthly_usd * 5.80, 2),
        "insights": insights,
    }


def execute_abyss(vm, item):
    action = item.get("action", "")
    alias = guardian.field(vm, "ssh")
    if action in ABYSS_PROBES:
        res = guardian.ssh(vm, ABYSS_PROBES[action])
        guardian.audit(alias, f"abyss:{action}", res)
        return res
    if action in SAFE_RUNBOOKS:
        expected = f"{alias} {action}"
        if item.get("confirm") != expected:
            raise ValueError(f"Confirmação incorreta. Digite exatamente: {expected}")
        res = guardian.ssh(vm, SAFE_RUNBOOKS[action])
        guardian.audit(alias, f"runbook:{action}", res)
        return res
    raise ValueError("Operação desconhecida no módulo The Abyss")
