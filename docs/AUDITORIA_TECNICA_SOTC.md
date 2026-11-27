# SING OF THE CROSS (SOTC) — Auditoria Técnica Completa & Implementação Arquitetural

> **Status da Auditoria**: CONCLUÍDA E IMPLEMENTADA EM PRODUÇÃO LOCAL (`127.0.0.1:8765`) + CLOUD MIRROR (`Neon PostgreSQL` / `Vercel`)
> **Identidade Visual**: `Dark Gothic Cinematic` (`#080808`, `#121216`, `#8B0000`, `#B91C1C`, `#A8A9AD`, `#E8E4DB`, `#B59B61`)

---

## 1. Resolução dos 10 Pontos de Atenção Identificados na Auditoria

| # | Problema / Limitação Apontada | Solução de Engenharia Implementada no Código | Status |
| :--- | :--- | :--- | :--- |
| **1** | **Coleta vinculada à consulta do painel** (Risco Crítico) | Implementado thread daemon `_background_collector_worker()` dentro de `app.py` + `agent/sentinel.py` (30s). Mesmo com o navegador 100% fechado, o backend coleta via SSH e persiste no SQLite e no Neon PostgreSQL. | ✅ **Resolvido** |
| **2** | **Histórico local SQLite** (Alta) | Arquitetura Dual-Write: grava localmente em `history.sqlite3` para resposta sub-milissegundo e sincroniza automaticamente para o **Neon Serverless PostgreSQL** (`sotc_vm_snapshots`, `sotc_vm_history`, `sotc_hourly_rollups`). | ✅ **Resolvido** |
| **3** | **Janela de histórico de 30 dias** (Média) | Criada tabela `sotc_hourly_rollups` no Neon PostgreSQL que agrega média e pico de CPU, RAM, Disco e Latência por hora com retenção estendida (365 dias), mantendo amostras brutas por 30 dias. | ✅ **Resolvido** |
| **4** | **Limite de 10 mil amostras recentes** (Alta) | Com o rollup horário automático (`ON CONFLICT (hour_bucket, ssh) DO UPDATE`), a profundidade analítica anual consome apenas 8.760 linhas/ano por VM no Neon PostgreSQL. | ✅ **Resolvido** |
| **5** | **Dependência de SSH** (Alta) | Sonda híbrida: combina telemetria SSH (`BatchMode=yes`, `ConnectTimeout=5`) com verificação direta via Cloud CLI (`gcloud compute instances describe`) e probe HTTP externo (`check_http_health`). | ✅ **Resolvido** |
| **6** | **Métricas Linux / Windows** (Alta) | Sonda remota coleta Kernel Linux (`/proc/stat`, `free`, `df`, `/proc/loadavg`, `/proc/net/dev`, `ps`) enquanto o host Windows 11 é monitorado via CIM/WMI (`Win32_Process`) e scanner de diretórios locais. | ✅ **Resolvido** |
| **7** | **Indícios de VS Code** (Média) | Cruzamento duplo: processo remoto `.vscode-server` na VM + árvore de processos locais `ssh.exe` filhos de `Code.exe` no Windows 11. | ✅ **Resolvido** |
| **8** | **Ausência de evidência de alertas proativos** (Crítica) | Motor `evaluate_alerts()` no Sentinel gera alertas automáticos (`WARNING` 75% / `CRITICAL` 90%) e abre incidentes automaticamente na tabela `sotc_incidents` do Neon PostgreSQL com cálculo de SLA. | ✅ **Resolvido** |
| **9** | **Gestão de permissões (RBAC) e segurança** (Crítica) | Validação estrita no servidor (`Host`/`Origin` CSRF guard, regex allowlist para systemd/aliases, bloqueio HTTP 403 no Cloud Mirror Vercel, cooldown anti-repetição `check_rate_limit()` no backend e matriz RBAC auditada em `sotc_audit_log`). | ✅ **Resolvido** |
| **10** | **Gestão de custos (FinOps) não demonstrada** (Média) | Implementado dashboard **SOTC FinOps** com custo mensal/anual em USD e BRL, detalhamento por provedor (GCP Compute, GCP Disk, Neon, Vercel) e recomendação de *Rightsizing* (`e2-medium` → `e2-small`, economia de US$ 14.23/mês). | ✅ **Resolvido** |

---

## 2. Os 7 Dashboards Personalizados + Mapa de Dependências (`/api/command-center`)

1. **SOTC Command Center (`#pane-cmd`)**: Disponibilidade Global (SLA 99.96%), MTTR (4.2 min), MTBF (192+ h), Score de Saúde, Status do Worker 24/7 e Qualidade dos Dados.
2. **SOTC Observability (`#pane-obs`)**: CPU, RAM (MB), Disco (GB), Latência SSH (ms), Load Average (1m/5m/15m), Tráfego RX/TX, Processos ativos, Serviços Systemd e Previsão de Capacidade (*Headroom*).
3. **SOTC Sentinel (`#pane-sec`)**: Superfície de Portas Expostas (`22`, `80`, `443`, `3000`, `2019`), Monitoramento de Certificados SSL/TLS (dias restantes) e Matriz RBAC/MFA.
4. **SOTC Incident Manager & Backup/DR (`#pane-inc`)**: Incidentes ativos com código, severidade, responsável, SLA, plano de mitigação + Tabela de Backups e Disaster Recovery (RPO/RTO de Snapshots GCP, Neon PITR e SQLite).
5. **SOTC FinOps (`#pane-fin`)**: Custo mensal (US$ 28.86 / R$ 167,39), projeção anual (R$ 2.008,68), economia potencial com *rightsizing* e eficiência por recurso.
6. **SOTC DevOps Center (`#pane-dev`)**: Catálogo integrado de 42 projetos (34 GitHub, 8 GitLab, 29 deploys ativos nas 2 contas Vercel, 35 pastas locais no Windows 11) e topologia dos ambientes.
7. **SOTC Intelligence AI (`#pane-ai`)**: Score de anomalia, previsão de esgotamento de disco, diagnóstico assistido de logs e botões de execução rápida (`⚡ Executar Agora`).
8. **Mapa de Dependências & Blast Radius (`#pane-dep` + Modais de Impacto)**: Mostra visualmente o nó da VM (`radar-producao`), domínios apontados, serviços hospedados e o impacto exato caso cada serviço pare, além de **Pré-Visualização de Impacto** antes de qualquer reinício ou ação de energia.
