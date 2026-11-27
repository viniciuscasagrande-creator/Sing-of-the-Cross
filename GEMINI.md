# SING OF THE CROSS (SOTC) — Diretrizes Oficiais do Projeto

> **SING OF THE CROSS — DARK GOTHIC CINEMATIC EDITION**
> Uma central de operações multi-cloud com arquitetura tecnológica moderna e identidade visual gótica, sombria, medieval e espectral.

## 1. Identidade Visual Obrigatória (`Dark Gothic Cinematic`)
Todas as telas, módulos e componentes do **Sing Of The Cross (SOTC)** devem seguir obrigatoriamente a paleta e ambientação **Dark Gothic Cinematic**:

| Cor | Hex | Aplicação |
| :--- | :--- | :--- |
| **Preto Abissal** | `#080808` | Fundo principal |
| **Negro Obsidiana** | `#121216` | Menus e painéis |
| **Vermelho Sangue** | `#8B0000` | Bordas e destaques |
| **Carmesim Infernal** | `#B91C1C` | Alertas críticos |
| **Prata Envelhecida** | `#A8A9AD` | Ícones e ornamentos |
| **Branco Espectral** | `#E8E4DB` | Textos e informações |
| **Ouro Antigo** | `#B59B61` | Detalhes e indicadores |

### Componentes Personalizados
- **Dashboard (`The Cathedral`)**: Gótico sombrio cinematográfico com névoa, sombras profundas e pulsação carmesim.
- **Cockpit Controlador de Voo (`Flight Control Deck`) — OBRIGATÓRIO**: O topo do `index.html` deve sempre exibir:
  1. **8 Displays HUD Digitais** (Status SSH, Latência, Load Kernel, RAM MB, Storage GB, Tráfego RX/TX, Processos e Uptime).
  2. **6 Instrumentos Circulares de Aviação** (Propulsão CPU, Pressão RAM, Volume Disco, Swap, Carga por Núcleo e Ping/Latência).
  3. **4 Gráficos Operacionais em Tempo Real (Quad-View Canvas)**: Radar Tático 360° com varredura contínua, Osciloscópio de Latência SSH, Curva Multi-Camada (CPU/RAM/Disco) e Espectro de Carga & Ecossistema (Subsistemas + 42 Projetos).
  4. **Nunca remover ou substituir** o Cockpit Controlador de Voo por telas simplificadas sem gráficos.
- **Central Executiva SOTC (7 Dashboards + Mapa de Dependências via `/api/command-center`)**:
  1. `SOTC Command Center` (SLA, MTTR, MTBF, Score de Saúde, Worker 24/7 e Qualidade dos Dados)
  2. `SOTC Observability` (Métricas detalhadas, serviços systemd e Previsão de Capacidade / Headroom)
  3. `SOTC Sentinel` (Portas expostas, Certificados SSL/TLS e Matriz RBAC/MFA)
  4. `SOTC Incident Manager & Backup/DR` (Incidentes com SLA e rotinas RPO/RTO)
  5. `SOTC FinOps` (Custos USD/BRL por provedor e recomendações de Rightsizing)
  6. `SOTC DevOps Center` (42 projetos GitHub/GitLab/Vercel e topologia de ambientes)
  7. `SOTC Intelligence AI` (Análise preditiva de anomalias com botão de execução rápida)
  8. `Mapa de Dependências & Blast Radius` (Grafo de 3 colunas: Servidor/Domínios → Serviços/Impacto se parar → Bancos/Projetos)
- **Menu Lateral**: Ornamentos medievais metálicos.
- **Gráficos Circulares**: Anéis metálicos e iluminação.
- **Gráficos Históricos**: Linhas luminosas sobre fundo negro.
- **Botões & Barras de Rolagem**: Metálicos com bordas carmesim; scrollbars em preto metálico e vermelho.
- **Janelas de Confirmação (`Guardian Security Protocol` + Impact Preview)**: Sempre usar modais `<dialog>` góticos (nunca `prompt()` nativo do navegador) com Pré-Visualização de Impacto (*Blast Radius*), confirmação digitada (`<alias> <acao>`) e cooldown anti-repetição validado no servidor (`check_rate_limit`).

## 2. Nomes Oficiais dos Módulos Internos
- **The Cathedral**: Dashboard principal
- **The Watcher**: Monitoramento em tempo real
- **The Guardian**: Segurança e intervenções
- **The Reaper**: Terminal e gerenciamento SSH (V0.6)
- **The Crypt**: Histórico e banco de dados SQLite (`history.sqlite3`)
- **The Oracle**: Análise inteligente (V0.8)
- **The Sentinel**: Alertas e notificações (V0.7)
- **The Abyss**: Logs e diagnóstico avançado
- **The Altar**: Configurações gerais
- **The Grimoire**: Automação e scripts (V0.9)
- **The Throne**: Administração central

## 3. Ambiente Windows 11, SSH e Segurança em Produção
- **Python 3.13 Local**: `C:\laragon\bin\python\python-3.13\python.exe` (porta `127.0.0.1:8765`, zero dependências externas).
- **Regra de Ouro ao Editar o Backend Python**: Sempre que `app.py`, `oracle.py`, `guardian.py`, `reaper.py` ou `devcentral_bridge.py` forem modificados, o agente **DEVE** reiniciar o processo `python.exe` ativo na porta `127.0.0.1:8765` e validar as rotas HTTP antes de encerrar a tarefa (evitando que uma instância antiga devolva `403/404 HTML` para novas rotas).
- **Frontend Resiliente a Erros HTTP**: A função `req()` no `index.html` deve sempre ler `await r.text()` e fazer `JSON.parse` dentro de `try/catch`, exibindo mensagens claras caso o servidor retorne HTML ou erro HTTP.
- **Coleta 24/7 Independente do Navegador & Persistência Dual**: Manter o worker daemon `_background_collector_worker()` em `app.py` e `agent/sentinel.py` gravando simultaneamente no SQLite local (`history.sqlite3`) e no **Neon Serverless PostgreSQL** (`sotc_vm_snapshots`, `sotc_vm_history`, `sotc_hourly_rollups`, `sotc_incidents`, `sotc_audit_log`).
- **Configuração SSH**: `C:\Users\vinad\.ssh\config` com alias `radar-producao` (`34.70.140.94`, usuário `vinad`, chave `~/.ssh/google_compute_engine`, projeto `gen-lang-client-0023634133`, zona `us-central1-a`).
- **Segurança em Produção**: Todas as sondas de telemetria e diagnóstico devem ser estritamente somente-leitura. Intervenções exigem confirmação explícita pelo **Guardian Security Protocol**.
- **GitHub**: Repositório `https://github.com/viniciuscasagrande-creator/Sing-of-the-Cross.git` (`main`).
