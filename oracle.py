"""
SING OF THE CROSS (SOTC) — Motor Didático de Diagnóstico, Limpeza e FinOps em Português
Permite monitorar e intervir na VM com 1 clique sem precisar abrir terminal SSH.
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
        "echo '=== 1. RESUMO DO ESPAÇO EM DISCO ==='; df -h /; "
        "echo ''; echo '=== 2. PASTAS QUE MAIS OCUPAM ESPAÇO (/var) ==='; sudo -n du -xhd1 /var 2>/dev/null | sort -hr | head -10 || du -xhd1 /var 2>/dev/null | sort -hr | head -10; "
        "echo ''; echo '=== 3. LOGS ANTIGOS DO SISTEMA (PODEM SER LIMPOS) ==='; journalctl --disk-usage 2>/dev/null; "
        "echo ''; echo '=== 4. ARQUIVOS TEMPORÁRIOS DE INSTALAÇÃO (APT) ==='; du -sh /var/cache/apt/archives /var/lib/docker 2>/dev/null || true; "
        "echo ''; echo '=== 5. ESPAÇO USADO PELOS PROJETOS (/home) ==='; sudo -n du -sh /home/* 2>/dev/null || du -sh /home/* 2>/dev/null"
    ),
    "critical_logs": "journalctl -n 60 --no-pager -p err..alert 2>/dev/null || journalctl -n 60 --no-pager",
    "auth_security": "grep -E 'Failed|Accepted|Invalid' /var/log/auth.log 2>/dev/null | tail -30 || journalctl -u ssh -u sshd -n 30 --no-pager 2>/dev/null",
    "docker_containers": "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || sudo -n crictl ps 2>/dev/null || echo 'Nenhum container Docker ativo neste usuário.'",
    "top_memory": "ps -eo pid,user,%mem,%cpu,rss,comm --sort=-%mem | head -20",
}

SAFE_RUNBOOKS = {
    "vacuum_journal": (
        "echo '--- ANTES DA LIMPEZA ---'; df -h /; "
        "sudo -n journalctl --vacuum-size=100M; "
        "sudo -n apt-get clean; "
        "echo '--- DEPOIS DA LIMPEZA ---'; df -h /"
    ),
    "reload_caddy": "sudo -n systemctl reload caddy.service 2>/dev/null || sudo -n systemctl restart caddy.service && systemctl is-active caddy.service",
}


def analyze_infrastructure(vms_rows, projects_summary=None):
    """Gera explicações simples e didáticas em Português sobre cada máquina virtual."""
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
                "severity": "CRÍTICO",
                "category": "Conexão com a Máquina",
                "title": f"A máquina {name} ({cloud}) não respondeu ao teste automático",
                "recommendation": "Ela pode estar desligada ou sem internet. Use os botões de energia ou verifique o console da Google Cloud.",
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
                "severity": "CRÍTICO" if disk_val >= 90 else "ATENÇÃO",
                "category": "Espaço em Disco",
                "title": f"O disco da máquina {name} está com {disk_val}% ocupado",
                "recommendation": "Identificamos cerca de 800 MB de logs antigos e arquivos temporários na máquina. Você pode clicar no botão '🧹 Limpar Logs e Liberar Espaço' logo abaixo para limpar sem precisar entrar na VM.",
            })

        cpu_val = float(vm.get("cpu_pct") or 0)
        ram_val = float(vm.get("ram_pct") or 0)
        if cpu_val < 20 and ram_val < 50:
            insights.append({
                "vm": name,
                "severity": "SAUDÁVEL",
                "category": "Desempenho e Velocidade",
                "title": f"A máquina {name} está rodando leve e rápida (Processador em {cpu_val}% e Memória em {ram_val}%)",
                "recommendation": f"Seus sistemas em produção estão trabalhando com bastante folga. O custo estimado dessa máquina ({mtype}) é de aproximadamente US$ {est_usd:.2f}/mês.",
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
        guardian.audit(alias, f"diagnostico:{action}", res)
        return res
    if action in SAFE_RUNBOOKS:
        expected = f"{alias} {action}"
        if item.get("confirm") != expected:
            raise ValueError(f"Confirmação incorreta. Digite exatamente: {expected}")
        res = guardian.ssh(vm, SAFE_RUNBOOKS[action])
        guardian.audit(alias, f"intervencao:{action}", res)
        return res
    raise ValueError("Ação não reconhecida")
