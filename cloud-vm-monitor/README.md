# Cloud VM Monitor — Painel de Conexões VS Code

Painel web local e leve para monitorar suas máquinas virtuais (Google Cloud, AWS, Azure, Oracle Cloud ou servidores SSH diretos) e identificar em tempo real quais estão com sessão ativa do **VS Code** (**Remote - SSH** ou **Remote Tunnels**).

## O que foi implementado

- 🟢 **Verde (`status-green`)**: VM ligada e VS Code com sessão ativa (`extensionHost` conectado).
- 🟡 **Amarelo (`status-yellow`)**: VM ligada, mas sem sessão ativa do VS Code (mesmo que o processo `.vscode-server` esteja ocioso em segundo plano).
- 🔴 **Vermelho (`status-red`)**: VM desligada ou inacessível via SSH.
- **Monitoramento de Recursos**: Barras de progresso em tempo real para **CPU**, **RAM**, **Disco (`/`)**, **SO** e **Uptime**.
- **Abertura com 1 Clique**: Botão **"💻 Abrir no VS Code"** que dispara `code --remote` ou o protocolo `vscode://vscode-remote/` tanto para `ssh-remote+` quanto para `tunnel+`.
- **Auto-Descoberta Multi-Cloud & SSH**: Importa automaticamente hosts do seu `~/.ssh/config` e instâncias das CLIs `gcloud`, `aws` e `az`.
- **Modo Demo & Modo SSH Real**: Inicia com as 4 VMs de demonstração do seu layout (`VM-Desenvolvimento`, `VM-Produção`, `VM-Testes`, `VM-Backup`) e permite alternar qualquer VM para **SSH Real** com um clique ou cadastrar novas VMs pela interface.

## Como executar

### Opção 1: Servidor Web Local Zero-Dependências (Recomendado — pronto para rodar)
Como o **Node.js** já está instalado na sua máquina, basta dar duplo-clique em:
- `iniciar_monitor.bat`

Ou executar no terminal:
```powershell
& "C:\Program Files\nodejs\node.exe" "F:\Sing Of The Cross\cloud-vm-monitor\server.js"
```
E abrir no navegador: **http://localhost:8501**

### Opção 2: Python + Streamlit
Caso instale Python + Streamlit no ambiente:
```powershell
streamlit run "F:\Sing Of The Cross\cloud-vm-monitor\streamlit_app.py"
```
Ambas as versões leem o mesmo arquivo `vms.json`.
