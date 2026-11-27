# Abrir no VS Code
Extraia o ZIP, abra a pasta Sing_Of_The_Cross localmente (não em uma janela Remote SSH), selecione o Python 3 e execute app.py no terminal ou F5 com a extensão Python instalada. Também pode usar Iniciar_SOTC.bat. Consulte PROJETO.md para as diretrizes e roadmap.

# Sing Of The Cross V0.5 — The Guardian
Windows 11, Python 3, OpenSSH e VS Code Remote SSH. Extraia o ZIP e execute Iniciar_SOTC.bat ou `python app.py`. Abra http://127.0.0.1:8765. Encerre com Ctrl+C no terminal. Não execute versões simultaneamente na mesma porta.

Use Descobrir aliases SSH e cadastre os aliases do arquivo local com a cloud correspondente. radar-producao vem cadastrada; ajuste seu alias em vms.json se necessário. O SSH não solicita senhas e exige host previamente confiável. Configure o acesso no VS Code primeiro. O diagnóstico usa comandos Linux de leitura, sem instalar agentes. CPU calculada por amostragem de /proc/stat por um segundo; memória via free, disco via df, carga via /proc/loadavg. Ausência de dados não significa zero. A presença de processos não comprova sessão ativa VS Code; falha SSH não comprova VM desligada.

Selecione uma VM na tabela para ver medidores circulares, detalhes, alertas e histórico. Os alertas são locais na tela: atenção >=75%, crítico >=90%. O histórico SQLite registra consultas reais, conserva 30 dias e a API retorna até 10 mil amostras recentes globais. A coleta depende do painel aberto e atualização automática ligada. CSV exporta as amostras disponíveis da VM e período selecionado. Para manter inventário de uma instalação anterior, copie seu vms.json com o painel encerrado. Os dados ficam locais, sem serviços externos de armazenamento.

Intervenções disponíveis: abrir VS Code, copiar comando SSH e abrir console GCP da VM cadastrada. A V0.5 acrescenta consultas cloud e reinício de serviços, conforme seção abaixo. Não há controle de energia da VM. O painel deve ficar restrito a localhost; não exponha a porta na rede. Testado em ambiente Linux com dados simulados para o parser e SQLite; Windows e VM real requerem validação.

## V0.5 — THE GUARDIAN
Mantém os gráficos circulares, histórico e descoberta SSH da V0.4. Selecione a VM na telemetria e use a seção Guardian para consultar estado na cloud, processos, serviços, rede, armazenamento, sistema e logs de alerta. A saída é limitada a 16 mil caracteres e exibida como texto. Consultas CLI não são automáticas.

Instale apenas as CLIs necessárias (gcloud, aws, az, oci) e autentique-se localmente pelos métodos oficiais. Utilize permissões mínimas de leitura. Não coloque credenciais em vms.json. Campos adicionais por VM: Google Cloud: name, project, zone (radar-producao já preenchida); AWS: instance_id, region; Azure: name, resource_group, subscription; Oracle Cloud: instance_id (OCID), region. Além desses campos, mantenha cloud, ssh e folder. Ajuste o alias SSH para corresponder ao VS Code. A descoberta não preenche IDs de cloud automaticamente.

Reiniciar serviço é opcional e altera a VM Linux: informe uma unidade systemd terminada em .service e digite o alias e nome do serviço exatamente como solicitado. O comando usa sudo -n e não concede permissões adicionais. Não teste em serviços críticos de produção sem janela autorizada. Um timeout não garante que a ação foi cancelada remotamente. A auditoria registra resultados retornados, sem armazenar saída de logs; erros antes da execução ou timeouts podem não aparecer. Não há controles de energia nesta versão. A interface é local (127.0.0.1), não exponha na internet. Não há autenticação multiusuário. A confirmação é uma proteção contra acionamento acidental, não um controle de autorização.

Validação: sintaxe Python/JS, montagem dos quatro comandos CLI, rejeição de confirmação incorreta e auditoria com execução simulada. Windows, cloud, SSH e reinício real não testados. Os diagnósticos dependem dos utilitários Linux e permissões disponíveis.

Migração: após encerrar a versão anterior, preserve uma cópia de vms.json e history.sqlite3, caso existam, e copie-os para a pasta nova para manter seu inventário e histórico. Não substitua sua configuração SSH.

## V0.6 — The Reaper

Execute `Iniciar_SOTC.bat` no Windows local ou `py -3 app.py` no terminal local do VS Code. Abra http://127.0.0.1:8765. A versão inclui `gothic.css` com ornamentos, anéis metálicos, menu de módulos e névoa discreta (respeita redução de movimento). A seção The Reaper tem console de diagnósticos predefinidos e abertura de uma janela SSH interativa externa no Windows. Não é um terminal interativo embutido no navegador.

Energia bloqueada por padrão. Para permitir em uma VM, edite seu objeto em `vms.json` e acrescente `"allow_power": true` após revisar os identificadores, credenciais, permissões e impactos. Digite o alias e a ação conforme solicitado. GCP reboot usa reset forçado; Azure stop usa deallocate; OCI usa SOFTSTOP/SOFTRESET. Não há snapshot ou rollback automático. Em caso de timeout, consulte o estado real antes de repetir. CLI precisa estar instalada e autenticada. Auditoria registra o resultado da solicitação, não necessariamente o estado final da VM. Não exponha a porta local na internet. Não copie credenciais para o projeto.

Para atualizar, preserve uma cópia de `vms.json` e `history.sqlite3` da versão anterior. A integração DevCentral permanece separada; não foi implementada nesta versão. Nenhuma operação real de energia foi executada durante os testes.
