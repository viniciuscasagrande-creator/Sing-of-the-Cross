# SING OF THE CROSS (SOTC) — Dark Gothic Multi-Cloud Command Center

> **Cockpit Controlador de Voo • 7 Dashboards Executivos • Mapa de Dependências • Intervenção Rápida com 1 Clique**

---

## 1. Estrutura Organizada do Projeto

```text
F:\Sing Of The Cross\
├── app.py                        # Servidor HTTP principal + Worker Daemon 24/7 (porta 127.0.0.1:8765)
├── SingOfTheCross.exe            # Aplicativo nativo Windows 11 (também na Área de Trabalho)
├── vms.json                      # Inventário local das máquinas virtuais (radar-producao)
├── vercel.json                   # Configuração Serverless da Vercel (Cloud Mirror)
├── GEMINI.md                     # Diretrizes oficiais e arquitetura do projeto
├── LEIA-ME.md                    # Documentação principal e guia de pastas
│
├── api/                          # Camada Serverless (Vercel Cloud Mirror)
│   └── index.py                  # Handler HTTP conectado ao Neon PostgreSQL
│
├── backend/                      # Módulos Python do Motor SOTC
│   ├── discovery.py              # Descoberta automática de hosts em ~/.ssh/config
│   ├── guardian.py               # Segurança, Cloud CLI, RBAC Cooldown e Auditoria
│   ├── reaper.py                 # Operações controladas SSH e Energia
│   ├── oracle.py                 # Motor dos 7 Dashboards Executivos, FinOps, AI e Dependências
│   └── devcentral_bridge.py      # Integração Neon PostgreSQL, Rollups Horários e 42 Projetos DevCentral
│
├── frontend/                     # Interface Visual Dark Gothic Cinematic
│   ├── index.html                # Cockpit Controlador de Voo + 7 Dashboards + Ações de 1 Clique
│   ├── gothic.css                # Estilização gótica, anéis metálicos e tabelas
│   └── assets/                   # Imagens e ícones (logo.png, background.jpg, gothic_bg.jpg, sotc.ico)
│
├── agent/                        # Monitoramento Contínuo 24/7 Independente do Navegador
│   ├── sentinel.py               # Worker Windows 11 -> Neon PostgreSQL
│   ├── config.example.json       # Configuração de limites e intervalos
│   └── install.ps1               # Registro no Agendador de Tarefas do Windows
│
├── database/                     # Camada de Persistência Dual (SQLite Local + Neon Cloud)
│   ├── sentinel.sql              # Schema SQL completo (Snapshots, Rollups, Incidentes, SSL, Backups)
│   └── history.sqlite3           # Banco local SQLite para telemetria imediata
│
├── scripts/                      # Utilitários de Inicialização e Build
│   ├── iniciar_sotc.bat          # Inicia o servidor local e abre o navegador
│   ├── Iniciar_Sentinel_Agent.bat# Inicia o agente Sentinel dedicado em janela própria
│   ├── Iniciar_Tunel_Cloudflare.bat # Abre túnel Cloudflare Zero-Trust
│   └── launcher.cs               # Código-fonte C# do executável SingOfTheCross.exe
│
├── docs/                         # Documentação de Engenharia e Referências
│   ├── AUDITORIA_TECNICA_SOTC.md # Auditoria Técnica e Matriz de Implementação
│   ├── PROJETO.md                # Histórico de evolução das versões
│   └── referencias-visuais/      # Referências de identidade visual Dark Gothic
│
└── archive/                      # Versões legadas arquivadas localmente (V0.1 a V0.6)
```

---

## 2. Como Executar

- **Pelo Aplicativo Windows 11**: Dê dois cliques em `SingOfTheCross.exe` (na raiz do projeto ou na sua Área de Trabalho).
- **Via Script ou Terminal**: Execute `scripts\iniciar_sotc.bat` ou:
  ```powershell
  C:\laragon\bin\python\python-3.13\python.exe app.py
  ```
- **Acesso Local (Com Intervenções SSH)**: `http://127.0.0.1:8765`
- **Acesso Cloud Mirror (Web / Celular)**: `https://cloud-vm-monitor.vercel.app`
