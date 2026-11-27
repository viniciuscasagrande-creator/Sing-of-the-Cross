# Sing Of The Cross — V0.2
Windows 11, Python 3 e cliente OpenSSH. Sem bibliotecas adicionais.

1. Extraia o ZIP completo. Execute Iniciar_SOTC.bat (mantenha o terminal aberto).
2. Abra http://127.0.0.1:8765 no navegador.
3. A VM radar-producao já está no inventário. O alias SSH foi presumido igual ao nome da instância. Confira no PowerShell local: `Get-Content "$env:USERPROFILE\.ssh\config"`. Se necessário, edite o campo `ssh` em vms.json para coincidir com o Host usado pelo VS Code. Não coloque senhas, tokens ou chaves privadas no JSON.
4. Atualize o painel. O teste usa SSH não interativo com verificação de chave de host. Se falhar, confira se o mesmo alias funciona no seu terminal e se a autenticação não exige interação. Não desative a verificação de chave de host.
5. Para adicionar outras VMs, acrescente objetos ao array de vms.json com name, cloud (Google Cloud, AWS, Azure ou Oracle Cloud), ssh e folder (opcional, caminho remoto absoluto). O botão VS Code depende do protocolo vscode registrado e da extensão Remote SSH.

O painel consulta processos locais por PowerShell e procura SSH com alias correspondente e ancestral Code.exe. É apenas um indício: processos podem persistir ou ter argumentos diferentes. O teste SSH abre conexão separada, executa uma consulta de processos na VM Linux e encerra. Não instala agentes, não altera serviços. Não confirma sessão ativa, nem estado de energia da cloud. A API cloud e métricas estão pendentes. O serviço HTTP escuta somente no loopback, sem autenticação; não exponha a rede. Para encerrar, Ctrl+C no terminal.
