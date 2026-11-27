# Sing Of The Cross (SOTC) — Multi-Cloud Control Center (V0.1)

Painel web independente em estilo **Dark Gothic** para gerenciamento e monitoramento de conexões **Remote SSH** e **VS Code Server** em múltiplas clouds (**Google Cloud**, **AWS**, **Microsoft Azure** e **Oracle Cloud**).

## Identidade Visual Oficial (Dark Gothic)
- `#0A0B0D` — Preto absoluto
- `#1D1E23` — Grafite
- `#8B0000` — Vermelho sangue
- `#C0C0C0` — Prata metálica
- `#E8E4DB` — Branco ósseo
- `logo.png` — Emblema Gótico Sombrio com Cruz e Ceifador incorporado ao cabeçalho

## Arquivos do Projeto
| Arquivo | Função |
| :--- | :--- |
| `app.py` | Backend Python nativo na porta `8765` (zero bibliotecas externas) |
| `server.js` | Backend alternativo em Node.js nativo na porta `8765` |
| `index.html` | Interface web Dark Gothic com filtros das 4 clouds, métricas e modais |
| `vms.json` | Inventário das máquinas virtuais (Prévia + hosts detectados em `~/.ssh`) |
| `logo.png` | Logo oficial do Sing Of The Cross |
| `iniciar_sotc.bat` | Atalho de 1 clique para iniciar o painel e abrir o navegador |

## Como Executar

### Opção 1: Com 1 clique (Windows)
Dê duplo-clique em **`iniciar_sotc.bat`**. Ele detecta automaticamente o seu Python 3.13 (`C:\laragon\bin\python\python-3.13\python.exe`) ou Node.js e abre **`http://127.0.0.1:8765`**.

### Opção 2: Pelo terminal
```powershell
C:\laragon\bin\python\python-3.13\python.exe app.py
```
E acesse no navegador: **[http://127.0.0.1:8765](http://127.0.0.1:8765)**
