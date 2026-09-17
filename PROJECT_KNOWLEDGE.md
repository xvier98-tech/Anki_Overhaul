# 🧠 Obsidian Addon Suite - Guia Técnico Definitivo & Conhecimento Essencial (PROJECT_KNOWLEDGE.md)

Este documento centraliza todas as informações fundamentais, caminhos absolutos, comandos operacionais e regras de arquitetura do projeto **Obsidian Addon Suite** para o Anki Desktop.
**OBJETIVO**: Eliminar testes empíricos repetidos, tentativas e erros com comandos de terminal e buscas redundantes que desperdiçam tokens.

---

## 📌 1. CAMINHOS ABSOLUTOS DO SISTEMA & ARQUIVOS CRÍTICOS

| Item | Caminho no Windows | Descrição / Importância |
| :--- | :--- | :--- |
| **Executável do Anki** | `$env:USERPROFILE\Downloads\Anki\anki.exe` | ⛔ **NÃO USE `where anki` no PowerShell** (trava o terminal). Chame diretamente o executável. |
| **Workspace de Desenvolvimento** | `$env:USERPROFILE\Downloads\Obsidian Addon` | Diretório raiz do código-fonte onde os testes e edições ocorrem. |
| **Pasta de Produção do Add-on** | `$env:APPDATA\Anki2\addons21\Obsidian Addon` | Onde o Anki carrega o addon. Deve receber `robocopy` após aprovação dos testes. |
| **Banco de Preferências Globais** | `$env:APPDATA\Anki2\prefs21.db` | SQLite contendo a tabela `profiles`. Idioma nativo em `_global['defaultLang']` (`en_US`, `pt_BR`, etc.). |
| **Pasta do Perfil Ativo** | `$env:APPDATA\Anki2\<SeuPerfil>` | Perfil de usuário padrão do Anki nesta máquina. |
| **Banco da Coleção de Cartões** | `$env:APPDATA\Anki2\<SeuPerfil>\collection.anki2` | Banco SQLite principal do Anki com notas, cartões e estatísticas. |
| **Log de Diagnóstico em Runtime** | `runtime_debug.log` | Presente na raiz do addon. Registra inicialização da FAB, FocusGuard, cliques e eventos. |

---

## 🛠️ 2. SCRIPTS & COMANDOS OPERACIONAIS HOMOLOGADOS

### 🧪 Executar a Suíte de Testes Unitários
```powershell
python -m unittest discover -s tests
```
- **Local de Execução**: `$env:USERPROFILE\Downloads\Obsidian Addon`
- **Comportamento**: Roda de forma headless no Python do sistema. Todos os componentes com dependência de GUI Qt possuem fallbacks defensivos para executar sem erro mesmo se `PyQt6` não estiver instalado globalmente.

### 🔄 Sincronizar com a Pasta de Produção do Anki
```powershell
robocopy "$env:USERPROFILE\Downloads\Obsidian Addon" "$env:APPDATA\Anki2\addons21\Obsidian Addon" /E /XD __pycache__ .git .pytest_cache /XF *.pyc
```
- **Retorno Esperado**: Código `1` (arquivos copiados com sucesso) ou `0` (arquivos idênticos). Ambos representam sucesso. Códigos ≥ 8 indicam erro.

### 🚀 Gerenciamento do Processo do Anki no Windows
```powershell
# 1. Iniciar o Anki
Start-Process "$env:USERPROFILE\Downloads\Anki\anki.exe"

# 2. Verificar se o Anki está aberto
Get-Process anki -ErrorAction SilentlyContinue

# 3. Encerrar o Anki
Stop-Process -Name anki -Force -ErrorAction SilentlyContinue
```

---

## 🏛️ 3. MAPA DOS MÓDULOS & DIRETRIZES DE ARQUITETURA

O addon é estruturado em módulos independentes sob o diretório `modules/`:

### 1. `modules/pomodoro/` (Temporizador Pomodoro & Anti-Distração)
- `timer_engine.py`: Máquina de estados (`WORK`, `SOFT_BREAK`, `BREAK`, `LONG_BREAK`, `PAUSED`).
  - ⚠️ **REGRA MANDATÓRIA**: O mecanismo de pausa por inatividade só opera durante `WORK`. As pausas de descanso (`BREAK`, `LONG_BREAK`) correm livremente até `00:00`.
  - Dispara som `"inactivity"` ao atingir `inactivity_timeout_seconds`.
- `focus_guard.py`: Monitor de foco da janela via `QGuiApplication.applicationStateChanged`.
  - ⚠️ **REGRA MANDATÓRIA**: Só pausa e dispara alarme se `state == PomodoroState.WORK`. Durante o intervalo, a perda de foco é ignorada.
- `sounds.py`: Roteia os alertas sonoros (`work_end`, `break_end`, `focus_loss`, `inactivity`).
  - ⚠️ **REGRA MANDATÓRIA**: No Windows, arquivos `.wav` devem usar `winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)` para latência zero e suporte a execução com janela minimizada.
- `native_fab.py`: Widget flutuante nativo PyQt6 (`NativePomodoroFab`).
  - Margens externas amplas (`32, 28, 32, 40`) para evitar corte na sombra suave.
  - Eventos na margem transparente ignorados para repassar cliques à interface do Anki.

### 2. `modules/theme_manager/` (Gerenciador de Temas & Cores)
- `engine.py`: Motor CSS global e funções matemáticas de contraste WCAG 2.1:
  - `get_perceptual_luminance(hex_color)`: Luminância relativa CIE sRGB.
  - `get_contrast_ratio(c1, c2)`: Razão de contraste (1:1 a 21:1), aceita hex string ou float.
  - `get_accessible_text_color(bg_hex)`: Seleciona cor de texto com contraste ≥ 4.5:1.
  - `#study` e `#ansbut` recebem cor dinâmica via `get_accessible_text_color(accent)`.
- `presets.py`: Paletas prontas (Dracula, Nord, Solarized Dark, Warm Paper, Clean Light, Catppuccin Mocha, OLED Dark). Todos calibrados para WCAG AA.

### 3. `modules/dashboard/` (Modern Stats Dashboard)
- `renderer.py`: Renderização HTML responsivo com 5 cards dinâmicos:
  - Metas Diárias (`dash_daily_goals`), Progresso de Hoje (`dash_today_progress`), Fila de Hoje (`dash_queue_today`), Acervo Total (`dash_deck_library`), Concluídos Hoje (`dash_completed_today`).
- `stats.py`: Extração analítica do banco do Anki (novos, retenção, ritmo em cards/min, maturidade ≥ 21d).

### 4. `modules/gamepad/` (Suporte Nativo a Gamepad & Controles)
- Suporte a botões B0 até B17 (incluindo B16 e B17 para DualShock/DualSense).
- Mapeamento universal com atalhos de teclado, analógicos esquerdo/direito e botões de ação.
- Polling via DirectInput e XInput.

### 5. `modules/unified_config/` (Central de Configurações Unificada)
- `settings_dialog.py` (`ObsidianSuiteHubDialog`): Diálogo mestre com 6 abas (Geral, Temas, Dashboard, Pomodoro, Gamepad, Prioridades).
- Sliders e spinboxes usam `FocusWheelSlider` e `FocusWheelSpinBox` para não roubar o scroll da página durante rolagem do mouse.

### 6. `utils/i18n.py` (Internacionalização Integral)
- Dicionário multilíngue nos 4 idiomas: Inglês (`en`), Português (`pt`), Espanhol (`es`) e Francês (`fr`).
- Detecção em 5 níveis com fallback inteligente para inglês universal (`en`) caso o idioma nativo não tenha tradução.

---

## 🚫 4. ERROS COMUNS & ANTI-PATTERNS (NUNCA FAÇA ISSO!)

1. ❌ **Executar `where anki` no PowerShell**:
   - `where` no PowerShell é alias para `Where-Object`. Ele aguarda entrada do pipeline na stdin e trava o processo até timeout.
   - ✔️ **Faça**: Use o caminho conhecido `$env:USERPROFILE\Downloads\Anki\anki.exe` ou `Get-Command anki`.
2. ❌ **Interpolar cor de texto com branco para botões**:
   - Gera textos pastéis sem contraste em botões coloridos.
   - ✔️ **Faça**: Use `get_accessible_text_color(button_hex)`.
3. ❌ **Inserir strings literais de interface sem `tr()`**:
   - Quebra a internacionalização no Dashboard ou Configurações.
   - ✔️ **Faça**: Sempre use `tr("sua_chave", "Texto Padrão")`.
4. ❌ **Pausar o intervalo do Pomodoro por falta de cliques**:
   - O intervalo é para descansar, não para responder cartões.
   - ✔️ **Faça**: Verifique `if self.state == PomodoroState.WORK:` antes de pausar por inatividade.
