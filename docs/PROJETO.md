# Sign Of The Cross — especificação central

Nome oficial: Sign Of The Cross (SOTC). Plataforma local Windows 11, interface web no navegador, VS Code Remote SSH. Google Cloud, AWS, Azure e Oracle Cloud. Primeira VM: radar-producao, Google Cloud, us-central1-a. Alias presumido: radar-producao.

## Diretriz visual obrigatória
Dark Gothic Cinematic em todos os componentes: preto abissal #080808, obsidiana #121216, sangue #8B0000, carmesim #B91C1C, prata #A8A9AD, osso #E8E4DB, ouro antigo #B59B61. Logo oficial, cruz gótica, ceifador, dragões, molduras metálicas, névoa opcional, gráficos circulares e históricos. Legibilidade, contraste e desempenho prioritários. Referências originais na pasta referencias-visuais.

## Módulos planejados
The Cathedral (dashboard), The Watcher (telemetria), The Guardian (segurança e intervenções), The Reaper (SSH), The Crypt (histórico), The Oracle (análise), The Sentinel (alertas), The Abyss (logs), The Altar (configuração), The Grimoire (automação), The Throne (administração).

## Estado atual
Base V0.5 Guardian: inventário, descoberta de aliases, indicadores SSH e VS Code, CPU/RAM/disco Linux, histórico SQLite, alertas locais, CSV, consultas CLI das quatro clouds, diagnóstico Linux e reinício de serviço com confirmação. Não confundir indícios de processo com sessão ativa. Não confundir falha SSH com VM desligada. Tema reforçado nesta edição; terminal, login, instalador e módulos futuros ainda não implementados.

## Roadmap
V0.6 The Reaper: terminal e gerenciamento avançado, energia das VMs com autorização e auditoria. V0.7 The Sentinel: monitoramento contínuo e notificações. V0.8 The Oracle: análise de falhas e custos. V0.9 The Apocalypse: automação e orquestração. V1.0: instalador Windows e consolidação.

## Segurança
Localhost somente. Não armazenar credenciais. Permissões mínimas, ações críticas confirmadas, sem agentes ou alterações automáticas em produção. Validar em VM de testes antes de intervenções reais.

## V0.6 — THE REAPER
Tema Dark Gothic Cinematic reforçado no código; console de diagnóstico controlado e terminal SSH externo; energia multi-cloud com habilitação por VM e confirmação. Terminal web interativo, gestão de processos por PID, snapshots e integração DevCentral continuam planejados. Testes de sintaxe e operações simuladas concluídos; validação real no Windows pendente.
