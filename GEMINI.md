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
- **Menu Lateral**: Ornamentos medievais metálicos.
- **Gráficos Circulares**: Anéis metálicos e iluminação.
- **Gráficos Históricos**: Linhas luminosas sobre fundo negro.
- **Botões & Barras de Rolagem**: Metálicos com bordas carmesim; scrollbars em preto metálico e vermelho.
- **Janelas de Confirmação (`Guardian Security Protocol`)**: Molduras góticas com confirmação digitada (`<alias> <servico>.service`).

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
- **Configuração SSH**: `C:\Users\vinad\.ssh\config` com alias `radar-producao` (`34.70.140.94`, usuário `vinad`, chave `~/.ssh/google_compute_engine`, projeto `gen-lang-client-0023634133`, zona `us-central1-a`).
- **Segurança em Produção**: Todas as sondas de telemetria e diagnóstico devem ser estritamente somente-leitura. Intervenções exigem confirmação explícita pelo **Guardian Security Protocol**.
- **GitHub**: Repositório `https://github.com/viniciuscasagrande-creator/Sing-of-the-Cross.git` (`main`).
