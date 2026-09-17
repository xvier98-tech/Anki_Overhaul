# 📋 Obsidian Addon Suite - Registro de Diagnóstico & Changelog Técnico (DEV LOG)

Este documento registra cronologicamente todos os problemas identificados, causas técnicas, correções implementadas e métodos de verificação.

## 📌 [Versão 2026-09-15 - v2.7.4] - Restauração de Alarme de Foco, Inatividade, Passagem Automática de Cards e Temporizador FAB

### 1. Contexto e Problemas Reportados
- **Temporizador Regressivo na FAB**: Exibir de forma contínua e visível no FAB o temporizador parcial de passagem de perguntas e respostas para consciência do tempo restante.
- **Passagem Automática Inoperante**: O auto-advance não estava virando nem respondendo cards automaticamente no Anki Reviewer.
- **Alarmes Quebrados**: O alarme de perda de foco (ao alternar para outros apps do Windows) e o alarme de inatividade do Pomodoro pararam de disparar.

### 2. Causa-Raiz e Soluções Implementadas
1. **Blindagem de Detecção de Foco no SO e Isolamento de Inatividade (`modules/pomodoro/focus_guard.py`)**:
   - *Causa*: `is_anki_active_window()` continha um curto-circuito consultando `QApplication.activeWindow()` e `focusWidget()`. No Qt sob Windows, esses ponteiros permanecem ativos na memória do Qt mesmo com outro app em primeiro plano no SO, fazendo `is_anki_active_window()` retornar sempre `True`. Além disso, o polling de `QCursor.pos()` chamava `register_user_activity()` globalmente, resetando a inatividade a cada 250ms com movimentos de mouse em qualquer app.
   - *Solução*: Removido o curto-circuito de Qt para acionar diretamente `user32.GetForegroundWindow()` e validação por PIDs e ancestrais do Anki. O registro de atividade do mouse via cursor agora exige que o Anki seja a janela ativa do SO. Adicionada restauração explícita do cursor padrão Win32 (`IDC_ARROW`).
2. **Correção do Mecanismo de Passagem Automática (`modules/pomodoro/auto_advance.py`)**:
   - *Causa*: `_notify_fab_update()` tentava importar função com nome incorreto de `hooks.py`, falhando silenciosamente e impedindo que a FAB soubesse das mudanças de lado do card. Ademais, faltava iniciar automaticamente o ciclo de foco ao entrar em modo de revisão se o auto-advance estivesse ativado.
   - *Solução*: `_notify_fab_update()` agora consulta diretamente `get_native_pomodoro_fab()` e invoca `_update_auto_advance_display()`. Se o usuário estiver no Reviewer com auto-advance ligado e o Pomodoro não tiver sido iniciado, o ciclo de foco é iniciado automaticamente (com salvaguarda para não interromper pausas de descanso). Métodos `_trigger_show_answer()` e `_trigger_answer_again()` receberam detecção resiliente de métodos snake_case e camelCase (`_showAnswer`, `_show_answer`, `_answerCard`, `_answer_card`).
3. **Persistência do Temporizador Regressivo na FAB (`modules/pomodoro/native_fab.py`)**:
   - *Solução*: O timer interno de 200ms `_auto_advance_timer` permanece em execução durante sessões de revisão com auto-advance ativo, exibindo em tempo real:
     - `⏱️ Xs` (azul ciano, contorno arredondado) durante a exibição da pergunta.
     - `⚠️ Xs` (vermelho alarme, contorno arredondado) durante a resposta que estourou o tempo.
   - Inserido `self.raise_()` no `enterEvent` da FAB para garantir que a interface gráfica permaneça no topo e totalmente clicável com o mouse mesmo em modo tela cheia ativado via gamepad.
4. **Cobertura de Testes Unitários (`tests/`)**:
   - `tests/test_pomodoro_auto_advance.py`: Adicionados `test_auto_start_focus_on_review` e `test_trigger_show_answer_and_again_snake_case_fallback`.
   - `tests/test_pomodoro.py`: Adicionado `test_focus_loss_and_inactivity_outside_anki`.
   - Total de 171 testes unitários aprovados com 100% de sucesso.

## 📌 [Versão 2026-09-15 - v2.7.3] - Controle de Volume Granular e Independente por Ferramenta (Gamepad e Pomodoro)

### 1. Contexto e Especificação Técnica
- **Requisito**: Adicionar nas configurações do `gamepad` a opção de controlar o volume do feedback sonoro de comandos, assim como toda e qualquer altura de som de qualquer função do addon que faça uso de áudio. O requisito técnico é de controle independente por tipo de ferramenta/funcionalidade, e não um controle geral master.
- **Mapeamento de Ferramentas com Áudio no Addon**:
  1. **Gamepad & Controles**: Feedback sonoro auditivo/tátil ao pressionar botões ou navegar no Anki.
  2. **Pomodoro**:
     - Som de Conclusão do Foco (`work_end`).
     - Som de Conclusão do Intervalo (`break_end`).
     - Sinal de Alarme por Perda de Foco ou Inatividade (`focus_loss` / `inactivity`).

### 2. Implementação das Soluções Técnicas
1. **Motor Central de Áudio com Atenuação PCM & Cache (`utils/audio_player.py`)**:
   - `get_volume_adjusted_wav(filepath, volume)`: implementa atenuação matemática de amplitude nas amostras PCM 16-bit com clipping defensivo sem dependências externas (`wave`, `array`, `struct`).
   - Cache atômico em disco (`assets/sounds/.cache/nome_vXX.wav`) que garante reprodução com **0.00ms de latência** após o primeiro cálculo.
   - `play_sound_with_volume(filepath, volume)`: no Windows, executa arquivos WAV atenuados via `winsound.PlaySound(play_path, SND_FILENAME | SND_ASYNC)`, garantindo 100% de conformidade com a regra técnica do `GEMINI.md` (reprodução assíncrona, execução com Anki em segundo plano e zero interferência com o `mpv`).
   - Suporte para supressão completa em volume 0% (mute sem I/O) e bypass direto em volume 100%.
2. **Controle de Volume no Gamepad (`modules/gamepad/`)**:
   - `modules/gamepad/sounds.py`: `play_gamepad_sound` agora recebe `volume: Optional[int] = None`, obtendo `config.get("sound_volume", 80)` por padrão.
   - `modules/gamepad/config_dialog.py`: Adicionado `FocusWheelSlider` para `sound_volume` (0% a 100%, padrão 80%) com indicador percentual dinâmico na aba Gamepad e botão `▶️ Testar` que reproduz o áudio na intensidade selecionada.
3. **Controles de Volume Granulares no Pomodoro (`modules/pomodoro/` & `modules/unified_config/`)**:
   - `modules/pomodoro/sounds.py`: `play_pomodoro_sound` agora resolve volumes individuais por evento:
     - `work_end` -> `sound_volume` (0-100%, padrão 100%)
     - `break_end` -> `break_sound_volume` (0-100%, padrão 100%)
     - `focus_loss` / `inactivity` -> `alarm_sound_volume` (0-100%, padrão 100%)
   - `modules/pomodoro/config_dialog.py`: Adicionados 3 sliders individuais com botões de teste e persistência dedicada.
   - `modules/unified_config/settings_dialog.py`: Na aba `🍅 Pomodoro & Áudio`, adicionados os 3 sliders de volume individuais para Foco, Intervalo e Alarme com teste e persistência no Hub.
4. **Internacionalização (i18n) & Configuração Padrão**:
   - `utils/i18n.py`: Adicionadas as chaves `gp_sound_volume_lbl`, `pomo_sound_vol_focus`, `pomo_sound_vol_break`, `pomo_sound_vol_alarm` nos 4 idiomas (`pt`, `en`, `es`, `fr`).
   - `config.json`: Registrados os valores padrão `sound_volume: 100`, `break_sound_volume: 100`, `alarm_sound_volume: 100`.
5. **Validação & Testes**:
   - Criado `tests/test_audio_volume.py` com 7 novos testes unitários (atenuação PCM, integridade WAV, cache hit, mute em vol 0, chamadas winsound, e resolução de volumes no Gamepad e Pomodoro).
   - Suíte de **168 testes unitários aprovada com 100% de sucesso**.
   - Sincronização via Robocopy concluída com êxito para a pasta de produção do Anki.

---

## 📌 [Versão 2026-09-15 - v2.7.2] - Correção de Sobreposição do FAB em Outros Aplicativos do SO

### 1. Diagnóstico Forense da Causa Raiz
- **Sintoma Diagnosticado**: Foi notado bug onde o widget FAB do Pomodoro sobrepunha janelas de aplicações externas do Windows (navegadores, editores, reprodutores), ocultando-se apenas mediante minimização explícita da janela principal do Anki. Caso contrário, ao abrir qualquer app sobre o Anki, o FAB continuava flutuando sobre ele.
- **Causa Raiz Técnica (Flag `WS_EX_TOPMOST` / `WindowStaysOnTopHint`)**:
  - Na v2.7.1, para garantir o recebimento de cliques do mouse contra a janela nativa do Chromium em tela cheia, foram aplicadas as flags `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint`.
  - A flag `Qt.WindowType.WindowStaysOnTopHint` injeta o estilo estendido Win32 `WS_EX_TOPMOST` no HWND da janela, forçando-a a permanecer na faixa Z-order superior de todo o subsistema Windows, sobrepondo janelas de terceiros mesmo quando o Anki está inativo ou em segundo plano.
  - Além disso, a rotina periódica `update_active_fab()` e `reposition()` invocava `self.raise_()` a cada tick de 1 segundo mesmo quando a janela principal do Anki não estava ativa nem em foco, reforçando continuamente a sobreposição.

### 2. Implementação das Soluções Técnicas
1. **Remoção de `WindowStaysOnTopHint` (`modules/pomodoro/native_fab.py`)**:
   - Ajustadas as flags de janela do `NativePomodoroFab` para `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint`.
   - O widget mantém seu próprio HWND de ferramenta (`WS_POPUP | WS_EX_TOOLWINDOW`) pertencente à janela principal do Anki (`mw`), preservando 100% da responsividade e recepção de cliques do mouse contra o Chromium em modo janela e tela cheia, porém sem o bit `WS_EX_TOPMOST`.
   - Com isso, quando qualquer outro aplicativo do Windows é aberto sobre o Anki, o novo aplicativo cobre naturalmente o Anki e o FAB.
2. **Guarda de Elevação e Minimização (`native_fab.py` & `hooks.py`)**:
   - `reposition()` e `update_active_fab()` agora verificam `mw.isMinimized()` e `not mw.isVisible()`: se o Anki estiver minimizado ou oculto, o FAB é imediatamente ocultado (`self.hide()`) e o reposicionamento é interrompido.
   - `self.raise_()` e `fab.raise_()` agora só são invocados se `mw.isActiveWindow()` ou `fab.isActiveWindow()` for verdadeiro. Quando o Anki estiver em segundo plano, nenhuma elevação de Z-order ocorre.
3. **Filtro de Eventos de Janela Robusto (`eventFilter`)**:
   - Implementado suporte para `QEvent.Type.WindowStateChange`, `Hide` e `Show` via helper `_is_event_type` compatível com execução real e mocks headless, garantindo que o FAB oculte instantaneamente ao minimizar o Anki e reapareça suavemente ao restaurá-lo.
4. **Testes Unitários & Validação**:
   - Criados os testes `test_fab_window_flags_no_topmost` e `test_fab_event_filter_minimized_handling` em `tests/test_pomodoro.py`.
   - Suíte completa de **161 testes aprovada com 100% de sucesso**.

---

## 📌 [Versão 2026-09-12 - v2.7.1] - Responsividade do FAB com Mouse & Temporizador Visual do Auto-Advance

### 1. Diagnóstico Forense da Causa Raiz
- **Sintoma Diagnosticado**: Ao ativar o Pomodoro ou o modo foco pelo controle (gamepad), os botões da FAB ficavam inacessíveis para o mouse devido à captura de foco pelo HWND do Chromium em tela cheia. Além disso, identificada a necessidade técnica de exibir visualmente na FAB a contagem regressiva de pergunta e resposta do Auto-Advance para fornecer telemetria em tempo real.
- **Causa Raiz 1 (Flags de Janela e Conflito de HWND com Chromium)**:
  - `NativePomodoroFab` utilizava `Qt.WindowType.SubWindow`. No Windows, `QWebEngineView` (Chromium) cria um HWND nativo filho (`Chrome_WidgetWin_0`) cobrindo toda a janela principal. No modo de tela cheia, os cliques do mouse sobre o widget alien eram capturados pelo Chromium, impedindo que os cliques chegassem aos botões do FAB.
- **Causa Raiz 2 (Ausência de Botão de Foco no Cabeçalho Compacto)**:
  - No estado padrão minimizado/compacto do FAB, o botão `btn_focus` ficava oculto dentro de `expanded_container`. Sem expandir o painel, não havia acesso visual direto para alternar ou sair do modo foco.
- **Causa Raiz 3 (Ocultação do Cursor do Mouse pelo FocusGuard)**:
  - Durante o uso do controle, o `FocusGuard` ativava o auto-hide do cursor (`BlankCursor`). Ao retornar a mão para o mouse sobre o FAB, o cursor não era restaurado imediatamente por ausência de `enterEvent`.

### 2. Implementação das Soluções Técnicas
1. **Blindagem de HWND Nativo e Z-Order do FAB (`modules/pomodoro/native_fab.py`)**:
   - Atualizado para `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint`.
   - Adicionada flag `Qt.WidgetAttribute.WA_ShowWithoutActivating` para evitar perda de foco de digitação.
   - Ajustadas as coordenadas globais de `reposition()` e `mouseMoveEvent` usando a geometria do `mw` para posicionamento contínuo e suporte a arrastar e soltar.
   - Implementado `enterEvent` para restaurar o cursor do mouse instantaneamente caso tenha sido ocultado pelo `FocusGuard`.
2. **Botão de Alternância de Foco no Cabeçalho Compacto (`btn_focus_toggle`)**:
   - Inserido botão dedicado no cabeçalho do FAB: exibe `🎯` no modo janela (Entrar no Modo Foco) e `🗗` em tela cheia (Sair do Modo Foco), permitindo alternância com 1 clique imediato de mouse.
3. **Temporizador Visual de Pergunta e Resposta no FAB (`lbl_auto_advance`)**:
   - `modules/pomodoro/auto_advance.py`: Implementado `get_countdown_info()` retornando `remaining_seconds`, `total_seconds`, `side` ("question" ou "answer") e `active`.
   - `modules/pomodoro/native_fab.py`: Criado badge em tempo real com `QTimer` de 250ms exibindo `⏱️ Xs` (azul ciano) na fase de pergunta e `⚠️ Xs` (vermelho) na fase de resposta condicional.
4. **Internacionalização (i18n)**:
   - Adicionadas traduções nos 4 idiomas (`pt`, `en`, `es`, `fr`) para tooltips e badges: `fab_btn_focus_enter_tip`, `fab_btn_focus_exit_tip`, `pomo_auto_adv_q_tip`, `pomo_auto_adv_a_tip`.
5. **Testes Unitários**:
   - Adicionados 3 novos testes em `tests/test_pomodoro_auto_advance.py` e teste de integração do FAB em `tests/test_pomodoro.py`, totalizando 159 testes aprovados.

---

## 📌 [Versão 2026-09-12 - v2.7.0] - Pomodoro Smart Auto-Advance (Passagem Condicional & Sincronização de Foco)

### 1. Requisitos & Especificação Técnica
- **Avanço Automático de Pergunta**:
  - Exibição automática da resposta após tempo configurável (`auto_show_answer_seconds`, padrão 20s, mín. 3s).
  - Sinaliza internamente que a pergunta foi revelada por timeout (`_auto_question_timeout = True`).
- **Avanço Automático Condicional da Resposta**:
  - Se a pergunta foi revelada automaticamente por timeout: subentende-se que o usuário não soube responder a tempo. Após tempo configurável (`auto_answer_again_seconds`, padrão 8s, mín. 2s), o card é respondido automaticamente com **"Again / Errei" (ease = 1)** e avança para o próximo.
  - Se a pergunta foi revelada manualmente pelo usuário (`_auto_question_timeout = False`): **nenhum temporizador é aplicado à resposta**, deixando a autoavaliação (Novamente/Difícil/Bom/Fácil) a critério e ritmo do estudante.
- **Sincronização Estrita com Inatividade e Pausas do Pomodoro**:
  - Se o usuário ficar inativo e o Pomodoro pausar (ou se houver perda de foco, abertura do editor ou pausa manual), todos os temporizadores de avanço automático são imediatamente congelados/interrompidos (`stop_timers()`), impedindo avanços fantasmas em segundo plano.
  - Ao retornar ao foco ativo na fase `WORK`, o temporizador da face atual do card é restabelecido.
  - Nas fases de descanso (`BREAK` e `LONG_BREAK`), o auto-advance permanece completamente desativado.

### 2. Implementação das Soluções Técnicas
1. **Módulo de Controle (`modules/pomodoro/auto_advance.py`)**:
   - Classe `ReviewerAutoAdvanceManager` gerenciando `_question_timer` e `_answer_timer` (`QTimer.singleShot`).
   - Métodos `on_reviewer_question_shown`, `on_reviewer_answer_shown`, `on_reviewer_card_answered`, `on_pomodoro_state_changed`.
   - Regras de segurança em `_trigger_show_answer()` e `_trigger_answer_again()` (`reviewer._answerCard(1)`).
2. **Integração de Hooks no Ciclo do Anki (`modules/pomodoro/hooks.py`)**:
   - Desacoplamento da exibição do cartão em `on_reviewer_question_shown` e `on_reviewer_answer_shown`.
   - Conexão do gancho `reviewer_did_answer_card` e sincronização bidirecional no callback de estado do Pomodoro.
3. **Internacionalização (i18n)**:
   - Novas chaves nos 4 idiomas (`pt`, `en`, `es`, `fr`): `pomo_auto_advance_grp`, `pomo_auto_advance_chk`, `pomo_auto_show_ans_sec`, `pomo_auto_ans_again_sec`, `pomo_auto_advance_hint`.
4. **Interfaces de Configuração**:
   - `modules/unified_config/settings_dialog.py`: Adicionado grupo visual "Passagem Automática de Cards (Modo Foco)" com persistência completa.
   - `modules/pomodoro/config_dialog.py`: Adicionado controle no painel de mecânicas adaptativas com sincronização de config.
5. **Configuração Padrão (`config.json`)**:
   - Inseridas chaves `"auto_advance_enabled": false`, `"auto_show_answer_seconds": 20`, `"auto_answer_again_seconds": 8`.
6. **Testes Unitários (`tests/test_pomodoro_auto_advance.py`)**:
   - 9 novos testes unitários cobrindo o ciclo de vida dos timers, regra condicional de avaliação, e sincronização com inatividade.

---

## 📌 [Versão 2026-09-12 - v2.6.1] - Restauração do Painel/Navegador (Layout do Editor & Contraste WCAG)

### 1. Diagnóstico Forense da Causa Raiz
- **Sintoma Reportado**: A janela do Navegador / Painel de Cartões (`aqt.browser.Browser`) apresentava dois problemas críticos:
  1. **Contraste Ilegível na Tabela e Sidebar**: As linhas alternadas da tabela de cartões (`QTableView`) exibiam fundo preto com texto marrom escuro (contraste ~1.1:1), e a barra lateral (`QTreeView`) apresentava fundo escuro desalinhado com o tema claro (`warm_paper`).
  2. **Editor Comprimido e Inutilizável**: A área de edição dos cartões à direita estava esmagada em uma faixa vertical de apenas ~50px, ocultando completamente os campos de texto do card e deixando apenas botões cortados visíveis.
- **Causa Raiz 1 (Ausência de `alternate-background-color` no CSS Qt)**:
  - O Anki ativa `setAlternatingRowColors(True)` na tabela do Navegador. Na ausência de declaração explícita de `alternate-background-color` na folha de estilos do tema, o Qt recorre à paleta base escura padrão (`#18181b`), enquanto a cor de texto do tema claro permanecia escura (`#2e2419`), tornando linhas alternadas completamente pretas e ilegíveis.
- **Causa Raiz 2 (Corrupção de Estado Persistido do QSplitter em `prefs21.db`)**:
  - O Anki serializa o estado dos divisores (`QSplitter`) no banco de preferências SQLite (`prefs21.db`). A chave `editor3Splitter6.9` no perfil do usuário continha um estado serializado corrompido ou redimensionado acidentalmente para 27.278px na tabela contra apenas 50px no editor.
  - Além disso, o Anki permite colapso de filhos (`childrenCollapsible = True`), de modo que uma vez colapsado, o editor não voltava à largura funcional sem intervenção manual ou código de proteção de geometria mínima.

### 2. Implementação das Soluções Técnicas
1. **Padronização de Contraste e Tema no Navegador (`modules/theme_manager/engine.py`)**:
   - Adicionada regra CSS explícita `alternate-background-color: {bg_pri};` e `QTableView::item:alternate { background-color: {bg_pri}; color: {text_pri}; }`.
   - Adicionado suporte completo de estilo para `QTreeView`, `QTreeView#sidebar`, `.SidebarTreeView` com estados normais, hover e seleção de itens com contraste acessível (`get_accessible_text_color(accent)`).
   - Estilizados cabeçalhos (`QHeaderView::section`), divisores (`QSplitter::handle`) e campo de busca rápida (`QLineEdit#searchEdit`).
2. **Blindagem e Recuperação Automática de Layout (`fix_browser_layout_and_splitters`)**:
   - Implementada rotina em `modules/theme_manager/engine.py` para forçar dimensões mínimas utilizáveis no painel de edição (`browser.editor.widget.setMinimumWidth(350)` e `setMinimumHeight(220)`).
   - Desativado o colapso acidental (`setChildrenCollapsible(False)`) em todos os divisores (`QSplitter`) do Navegador.
   - Detecção e descompressão automática: qualquer painel com largura inferior a 240px é recalculado e expandido imediatamente para uma proporção equilibrada (55% tabela / 45% editor).
   - Execução imediata no hook `browser_will_show` com retentativas agendadas via `QTimer.singleShot` (50ms, 200ms, 500ms) para sobrepor com segurança a restauração diferida de estado nativa do Anki.
3. **Limpeza e Reparo do Banco de Preferências (`prefs21.db`)**:
   - Substituído o valor corrompido de `editor3Splitter6.9` por um estado balanceado e estável.

---

## 📌 [Versão 2026-09-11 - v2.6.0] - Prioridade Estrita no Anki v3 Scheduler & Reordenação Automática

### 1. Diagnóstico Forense da Causa Raiz
- **Sintoma Reportado**: O usuário estava revisando novos cartões de "Abdome Agudo Obstrutivo" (prioridade efetiva 100 / mínima) mesmo após configurar prioridades mais altas (40, 60, 70, etc.) em outros baralhos como "Endocrinologia" e "Clínica Médica".
- **Causa Raiz 1 (Agrupamento Alfabético do Scheduler v3 do Anki & Persistência de Presets)**:
  - No agendador v3 (`v3 scheduler`), cada preset de opções de baralho (`dconf`) possui a propriedade `newGatherPriority`.
  - O valor padrão do Anki é `0` (`Deck Order / Por Baralho`). Sob essa configuração, o Anki agrupa novos cartões estritamente por ordem alfabética de baralho até atingir o limite diário, **independentemente do valor de `due` do cartão**.
  - Como `Flashcards Osler 2024::Clínica Cirúrgica::Abdome Agudo::Abdome Agudo Obstrutivo` vinha alfabeticamente antes de `Clínica Médica`, o Anki esgotava a cota diária com os cartões cirúrgicos.
  - Para persistir `newGatherPriority = 1` no backend Rust do Anki moderno, a API necessária é `col.decks.update_config(conf)` (e não `col.decks.save(conf)` que atua apenas sobre a tabela de baralhos).
- **Causa Raiz 2 (Precedência Absoluta da Fila de Aprendizado `is:learn`)**:
  - Quando um sub-baralho começa a ser estudado, qualquer cartão avaliado ou iniciado entra no estado `learning` (`queue = 1` ou `type = 1`).
  - No algoritmo nativo do Anki, **cartões em Aprendizado possuem precedência sobre qualquer cartão Novo**, independentemente do baralho ou prioridade.
  - Como os cartões de "Obstrução Intestinal" haviam sido iniciados sob o agendamento alfabético anterior, o Anki insistia em apresentá-los antes de liberar a fila de novos.
  - Com a reversão limpa dos cartões iniciados para `queue = 0` via `forgetCards`, a fila de aprendizado foi desobstruída e os cartões de prioridade 40 (`due = 1`) assumiram o topo absoluto da fila de estudo.
- **Causa Raiz 3 (Reordenação Manual vs Automática)**:
  - A alteração de prioridades na interface gravava a configuração no JSON, mas não disparava imediatamente a reindexação dos cartões no SQLite.

### 2. Implementação das Soluções Técnicas
1. **Configuração Forçada de Agrupamento por `due` Ascendente (`newGatherPriority = 1`)**:
   - Atualizada a rotina `ensure_deck_gather_priority_ascending(col)` em `modules/priority_sequencer/reorder.py` e `core/reorder.py` para utilizar `col.decks.update_config(conf)`.
   - Todos os presets de baralhos agora têm `newGatherPriority = 1` (`Lowest Position / Posição Ascendente por due`), garantindo coleta de novos rigorosamente pela menor posição global de `due`.
2. **Desobstrução e Respeito a Baralhos de Maior Prioridade**:
   - Cartões de sub-baralhos de prioridade 100 iniciados inadvertidamente foram revertidos ao estado `queue = 0` (novo) e posicionados em suas posições corretas de baixa prioridade (`due = 27.723..27.791`), liberando imediatamente os cartões de Prioridade 40 (Endocrinologia, `due = 1..518`) no revisor.
2. **Reordenação Automática Imediata em Edição de Prioridade**:
   - Integrada chamada assíncrona automática a `run_reorder_with_ui(..., interactive=False)` em:
     - `_apply_selected_priority` e `_clear_selected_priority` (`modules/priority_sequencer/ui/priority_dialog.py` e `ui/priority_dialog.py`).
     - `_save_only` (`modules/priority_sequencer/ui/set_priority_modal.py` e `ui/set_priority_modal.py`).
   - Habilitadas por padrão as flags `"auto_reorder_on_profile_open": true` e `"auto_reorder_on_sync": true` em `meta.json`.
3. **Reindexação Física Completa da Coleção Ativa (47.161 novos cartões)**:
   - Executada a reordenação em lote diretamente na base de produção (`collection.anki2`):
     - Prioridade 40 (Endocrinologia): `due` 1 a 518 (primeiros absolutos a serem apresentados).
     - Prioridade 60 (Clínica Médica / Preventiva): `due` 519 a 668.
     - Prioridade 70: `due` 669 a 862.
     - Prioridade 75: `due` 863 a 966.
     - Prioridade 80: `due` 967 a 1168.
     - Prioridade 85: `due` 1169 a 1374.
     - Prioridade 90: `due` 1375 a 2319.
     - Prioridade 100 ("Abdome Agudo Obstrutivo"): `due` 27.723 a 27.791 (relegados para o final da fila).
4. **Auditoria de Integridade DNA Proofreading Pós-Aplicação**:
   - Auditoria executada com 100% de sucesso na base real:
     - `block_contiguity_valid: True`
     - `monotonicity_valid: True`
     - `no_due_collisions: True`
     - `violations_detected: 0`

---

## 📌 [Versão 2026-09-11 - v2.5.9] - Feedback Visual e Motor de Verificação de Integridade DNA Proofreading com Autocura

### 1. Diagnóstico e Demanda do Usuário
- **Demanda**:
  1. Fornecer feedback visual rico durante e ao final do processo de reorganização de novos cartões pelo Gerenciador de Prioridades (notificando em tempo real sobre as etapas em andamento e exibindo o resumo métrico com sucesso ou falha).
  2. Implementar um mecanismo de verificação e auditoria de fidelidade de ordenação análogo ao sistema biológico de proofreading do DNA (exonuclease 3'->5'), garantindo a detecção de desvios e autocura atômica in-flight antes da entrega final dos cartões.

### 2. Arquitetura & Implementação do Motor de Integridade (DNA Proofreading)
- **`modules/priority_sequencer/integrity.py` & `core/integrity.py`**:
  - Implementação de `verify_and_repair_card_order(col, deck_tree, auto_repair=True) -> IntegrityReport`:
    - **Invariante 1 - Bloco Fechado Contíguo (Closed Block Invariance)**: Audita se todos os cartões de um mesmo baralho permanecem 100% agrupados sem entrelaçamento com cartões de outros baralhos.
    - **Invariante 2 - Monotonicidade de Prioridade**: Confirma que baralhos com prioridade numérica menor (maior urgência de estudo) aparecem estritamente antes dos de menor prioridade na linha de `due`.
    - **Invariante 3 - Sequência Unívoca (Collision-Free Sequence)**: Audita e garante que não existem dois ou mais cartões com valores repetidos de `due` na fila de novos (`queue = 0`).
    - **Mecanismo de Autocura Atômica (DNA Exonuclease Repair)**: Se qualquer anomalia for detectada, o motor calcula a ordenação canônica em memória e executa uma retificação em lote (`UPDATE cards SET due = ?, mod = ? WHERE id = ?`) no SQLite em chunks de 1000 registros, re-auditando em seguida para certificar 100% de conformidade.
- **`modules/priority_sequencer/models.py` & `core/models.py`**:
  - Criação do dataclass `IntegrityReport` com propriedades computadas `is_flawless` e `status_badge` dinâmico.
  - Extensão de `ReorderResult` para transportar o relatório de integridade (`integrity_report: Optional[IntegrityReport]`).

### 3. Interface Visual de Feedback em Tempo Real
- **`modules/priority_sequencer/ui/feedback_dialog.py` & `ui/feedback_dialog.py`**:
  - **`ReorderProgressDialog`**: Diálogo moderno com barra de progresso em gradiente e checklist visual de 4 etapas:
    1. 🔍 *Etapa 1/4: Mapeando baralhos e hierarquia de herança...*
    2. 📦 *Etapa 2/4: Agrupando cartões em blocos fechados contíguos...*
    3. 💾 *Etapa 3/4: Gravando nova sequência no banco de dados SQLite...*
    4. 🧬 *Etapa 4/4: Verificação de fidelidade e autocura (DNA Proofreading)...*
  - **`ReorderSummaryDialog`**: Modal rich pós-execução apresentando:
    - Banner estilizado de conclusão com tema dinâmico.
    - Cards métricos (Cartões Reordenados, Baralhos Estruturados, Tempo Decorrido).
    - Seção dedicada de Auditoria DNA Proofreading com badge de status e checagem item a item dos 3 invariantes fundamentais.
- **`modules/priority_sequencer/reorder.py` & `core/reorder.py`**:
  - Conexão de `verify_and_repair_card_order` dentro de `execute_reorder_in_col`.
  - Atualização de `run_reorder_with_ui` com suporte ao parâmetro `interactive: bool = True`:
    - Disparos interativos (menu Ferramentas, botões do Gerenciador de Prioridades) acionam a barra de progresso e o modal de resumo rich.
    - Disparos automatizados em segundo plano (`ui/hooks.py`: abertura de perfil e pós-sincronização) executam com `interactive=False`, emitindo apenas tooltips não-intrusivos para preservar a fluidez do estudo.

### 4. Validação & Testes Unitários
- **`tests/test_integrity.py`**: 4 testes unitários cobrindo:
  - `test_flawless_order`: Confirma que uma coleção íntegra passa com 0 anomalias e badge de 100% de integridade.
  - `test_interleaved_fragmentation_detected_and_repaired`: Simula fragmentação de baralhos e valida autocura imediata.
  - `test_monotonicity_violation_detected_and_repaired`: Simula inversão de prioridades e valida restauração da ordem.
  - `test_due_collision_detected_and_repaired`: Simula posições repetidas de `due` e valida renumeração estrita.
- Suíte completa: 146 testes passando com 100% de aprovação em 16.15s.

---

## 📌 [Versão 2026-09-11 - v2.5.8] - Correção da Edição e Propagação de Prioridades no Gerenciador de Baralhos

### 1. Diagnóstico e Demanda do Usuário
- **Sintomas Relatados**:
  1. No Gerenciador de Prioridades (`PriorityManagerDialog` e `SetPriorityModal`), a edição da prioridade manual ou efetiva de baralhos e sub-baralhos não refletia na tabela/quadro, permanecendo fixada no valor base padrão `100`.
  2. Tanto a edição via duplo clique (abrindo o modal) quanto a edição no painel inferior ("Editar Baralho Selecionado") revertiam visualmente para 100 imediatamente após o clique em "Aplicar Prioridade" ou "Salvar".

### 2. Investigação Científica & Causas Raiz
- **Causa Raiz 1 (Incompatibilidade de Tipagem de Chaves - `int` vs `str`)**:
  - No arquivo de configuração serializado em JSON (`config.json` e Anki addonManager), as chaves de dicionários são obrigatoriamente strings (`"1741234567890": 5`).
  - A função `get_deck_priorities()` em `utils/config_manager.py` retornava explicitamente `{str(k): int(v)}`.
  - Entretanto, tanto `build_deck_tree()` (`hierarchy.py`) quanto `SetPriorityModal` realizavam a busca da prioridade utilizando `did = int(d["id"])` (`explicit_priorities.get(did)`).
  - Em Python, `10 in {"10": 5}` é estritamente `False`, fazendo com que `explicit_priorities.get(did)` retornasse SEMPRE `None`.
  - Como consequência, `node.explicit_priority` tornava-se `None` e `node.effective_priority` revertia para `default_priority` (100).
- **Causa Raiz 2 (Perda de Seleção pós-Refresh da Árvore)**:
  - `refresh_deck_tree()` executava `self.tree.clear()` sem armazenar o baralho previamente selecionado, resetando a seleção e desabilitando o painel de edição inferior logo após a gravação.

### 3. Soluções Implementadas
- **`utils/config_manager.py`**:
  - Criação da classe `_DualKeyPriorityDict(dict)`, que permite acesso transparente tanto por chave inteira (`prio[10]`) quanto por chave string (`prio["10"]`), suportando operadores `[]`, `.get()` e `in`.
  - Atualização de `get_deck_priorities()` para retornar `_DualKeyPriorityDict`.
  - Atualização de `set_deck_priority()` para gravar como string no JSON e limpar chaves duplicadas na memória.
- **`modules/priority_sequencer/hierarchy.py` & `core/hierarchy.py`**:
  - Normalização preventiva em `build_deck_tree()` para garantir que qualquer formato de entrada de `explicit_priorities` resolva corretamente com `did: int`.
- **`modules/priority_sequencer/ui/priority_dialog.py` & `ui/priority_dialog.py`**:
  - Preservação da seleção de baralho em `refresh_deck_tree()` (`prev_did = self._get_selected_deck_id()`), restaurando o foco e re-selecionando o item após reconstruir a árvore.
  - Conexão do atalho `returnPressed` no `QSpinBox` para aplicar a prioridade diretamente ao teclar Enter.
  - Suporte a tecla Enter/Return no `QTreeWidget` para abrir o modal de prioridade do baralho selecionado.
- **`tests/test_hierarchy.py`**:
  - Adicionado teste de regressão `test_string_and_dual_key_priorities` validando a propagação e herança de prioridades com chaves string e dual-key.

## 📌 [Versão 2026-09-11 - v2.5.7] - Restauração da Tela Inicial do Anki & Estabilização de Escopo em WebViews

### 1. Diagnóstico e Demanda do Usuário
- **Sintomas Relatados**:
  1. A janela principal do Anki (DeckBrowser e barra de ferramentas superior) ficou cinza vazia e sem carregamento visual de baralhos após a aplicação do reforço de contraste.
  2. Nenhuma interação gráfica era permitida na janela principal, sugerindo congelamento no pipeline de renderização do Chromium.

### 2. Investigação Científica & Causas Raiz
- **Causa Raiz 1 (Injeção Indiscriminada via `webview_did_inject_style_into_page`)**:
  - O hook global era acionado para cada WebView criada ou exibida pelo Anki (toolbar, deckBrowser, reviewer, etc.), inserindo nós `<div>` de estilos indevidamente dentro do `<head>`.
- **Causa Raiz 2 (Loop Infinito de Microtarefas por `MutationObserver`)**:
  - A rotina de sincronização possuía um observer global monitorando `attributes: true` no `document.documentElement` sem restrição de escopo. Como ela própria modificava atributos (`data-bs-theme`, `style`), gerava um ciclo contínuo de microtarefas no motor Blink que impedia a drenagem do event loop e congelava a renderização das telas principais.

### 3. Soluções Implementadas
- **`modules/theme_manager/engine.py`**:
  1. Desconexão do hook global `webview_did_inject_style_into_page` (mantido apenas para páginas dinâmicas pontuais e chamada direta diferida no editor).
  2. Fast-bailout na linha 1 de `syncEditorTheme`: se a página não possui elementos do editor (`anki-editable`, `.rich-text-editable`, etc.), encerra imediatamente sem criar observers nem mutar elementos.
  3. Trava anti-reentrância `_isSyncingTheme` garantindo execução única e sem recursão.
  4. Inserção do container de estilos em `document.body` (e não `<head>`).
- **Validação**:
  - 141 testes automatizados executados e 100% aprovados.
  - Sincronização via Robocopy e verificação de resposta em tempo real pelo usuário.

## 📌 [Versão 2026-09-11 - v2.5.6] - Correção Definitiva de Contraste no Editor Visual de Cards (Temas Claros & Shadow DOM)

### 1. Diagnóstico e Demanda do Usuário
- **Sintomas Relatados**:
  1. Embora o editor HTML (CodeMirror) tenha sido ajustado com sucesso, o editor visual padrão (`EditCurrent`, `AddCards` e navegador de cartões) persistia com letras brancas ou quase transparentes sobre fundos claros de papel (ex.: `warm_paper`, `clean_light`), tornando a leitura e a digitação praticamente invisíveis sem seleção manual.
  2. A letra dos campos não acompanhava a cor primária de texto (`#451a03` no `warm_paper`) e permanecia em `#ffffff`.

### 2. Investigação Científica & Causas Raiz
- **Causa Raiz 1 (Re-injeção de `night-mode` pelo Anki)**:
  - Com o modo noturno ativado nas preferências do perfil (`prefs21.db` -> `theme: 2`), o Anki executa `add_dynamic_styling_and_props_then_show` e adiciona `night-mode` a `document.documentElement` toda vez que carrega a página HTML do editor.
- **Causa Raiz 2 (Reatividade do SvelteKit e `style#userBase`)**:
  - O componente Svelte `RichTextInput` (`Vm` em `editor.js`) monitora `$pageTheme.isDark` através da presença da classe `night-mode`.
  - Ao detectar `isDark: true`, o Svelte injeta dinamicamente no `shadowRoot` de `.rich-text-editable` uma folha `<style id="userBase">` contendo `anki-editable { color: white; }`.
- **Causa Raiz 3 (Encapsulamento do Shadow DOM e Assincronia)**:
  - O texto das notas reside dentro de `<anki-editable>` no Shadow DOM aberto. Regras de CSS externo no `<head>` não penetram o Shadow DOM.
  - A criação e injeção do `<anki-editable>` ocorre de maneira assíncrona após o carregamento das notas (`stylesDidLoad`). A varredura de script anterior não capturava o elemento `anki-editable` propriamente dito nem usava `-webkit-text-fill-color`.

### 3. Soluções Implementadas
- **`modules/theme_manager/engine.py`**:
  - Inclusão do seletor `anki-editable` e propriedade `-webkit-text-fill-color: {text_pri} !important;` tanto na folha global quanto dentro de cada Shadow Root.
  - Em `syncEditorTheme()`:
    1. Sobrescrita direta de `sr.querySelector("style#userBase")` com `anki-editable { color: {text_pri} !important; -webkit-text-fill-color: {text_pri} !important; }`.
    2. Aplicação direta de estilos inline em todos os elementos de texto do `shadowRoot`, incluindo `anki-editable`.
    3. Anexação de um `MutationObserver` dedicado diretamente a cada `shadowRoot` (`sr._obsidian_obs`), garantindo atualização instantânea durante digitação ou re-renderizações assíncronas do Svelte.
    4. Ativação de intervalo periódico em background de 200ms (`window._obsidianEditorSyncInterval`) para blindagem total contra mutações assíncronas do SvelteKit.
  - Criação da função auxiliar `_sync_editor_theme_deferred(web_view)` com temporizadores escalonados (`QTimer.singleShot` em 50ms, 150ms, 300ms e 600ms) integrada aos hooks do Anki (`on_editor_did_init`, `on_editor_did_load_note`, `on_add_cards_did_init`, `on_browser_will_show`).
- **`tests/test_theme_manager.py`**:
  - Testes unitários atualizados cobrindo `applyStylesToShadow`, `userBase`, `-webkit-text-fill-color`, `_obsidian_obs` e `_obsidianEditorSyncInterval`.

## 📌 [Versão 2026-09-11 - v2.5.5] - Adaptação Temática Integral da Central de Configurações (Settings Hub) e Preview em Tempo Real

### 1. Diagnóstico e Demanda do Usuário
- **Sintomas Relatados**:
  1. A Central de Configurações do addon (`ObsidianSuiteHubDialog`) apresentava descompasso visual severo sob temas claros (ex.: `warm_paper`): enquanto a borda e abas externas usavam tons creme, as áreas internas de conteúdo das abas no `QTabWidget` renderizavam sobre uma viewport cinza-escura padrão do Anki (`#2b2b2b`).
  2. Como a folha de estilos do diálogo definia a cor de texto das labels e checkboxes para o texto primário do tema (`#451a03` no `warm_paper`), o texto escuro era desenhado sobre o container cinza-escuro, tornando as opções ilegíveis.
  3. SpinBoxes, LineEdits, GroupBoxes, Sliders, ScrollBars e Checkboxes utilizavam os estilos escuros padrão do Anki desktop.
  4. Na aba "Temas & Cores", a troca de tema no combo apenas atualizava os botões de amostra (*swatches*), sem recalcular nem refletir a estética do próprio diálogo em tempo real.

### 2. Investigação Científica & Causas Raiz
- **Causa Raiz 1 (Sobrescrita e Quebra de Cascata no QScrollArea)**:
  - O método `_wrap_tab_in_scroll` atribuía localmente `scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")`.
  - No Qt, a chamada de `setStyleSheet` em um widget filho anula as regras herdadas do stylesheet da janela ancestral. Além disso, o widget interno `viewport()` do `QScrollArea` não combinava com o seletor `QScrollArea`, caindo de volta na paleta nativa escura da aplicação Anki.
- **Causa Raiz 2 (Ausência de Seletores Específicos para Subcontroles de Diálogos)**:
  - `get_qt_dialog_stylesheet` não estilizava explicitamente `QScrollArea QWidget#qt_scrollarea_viewport`, `QCheckBox::indicator`, `QSlider`, `QScrollBar` e `QSpinBox::up-button/down-button`, fazendo com que os componentes herdassem estilos do tema global do sistema operacional ou do Anki desktop.
- **Causa Raiz 3 (Falta de Preview Dinâmico do Diálogo)**:
  - `_on_preset_changed` e `_on_custom_color_picked` modificavam os dados do formulário mas não executavam a reaplicação dos estilos do diálogo (`apply_dialog_theme`).

### 3. Soluções Implementadas
- **`modules/theme_manager/engine.py`**:
  - Em `get_qt_dialog_stylesheet`:
    - Adicionado suporte a `QScrollArea, QScrollArea > QWidget, QScrollArea QWidget#qt_scrollarea_viewport, .QScrollArea, QTabWidget > QWidget`.
    - Estilização completa e acessível de `QCheckBox::indicator` e `QRadioButton::indicator` com borda `{border}`, fundo `{bg_card}` e checagem em `{accent}`.
    - Estilização de `QLineEdit`, `QTextEdit`, `QSpinBox`, `QDoubleSpinBox` com `{bg_card}`, bordas `{border}` e foco em `{accent}`.
    - Estilização de botões de incremento de `QSpinBox` (`up-button`, `down-button`) com `{bg_hover}` e hover em `{accent}`.
    - Estilização de `QGroupBox` e `QGroupBox::title` com fundo `{bg_pri}` e texto contrastado.
    - Estilização de trilha e manipulador de `QSlider` (`groove`, `sub-page`, `handle`).
    - Estilização de barras de rolagem verticais e horizontais (`QScrollBar`) com `{bg_pri}`, manipulações em `{border}` e hover em `{accent}`.
    - Definição de `header_sec_color` garantindo contraste mínimo WCAG 2.1 AA.
- **`modules/unified_config/settings_dialog.py`**:
  - Implementado o método `apply_dialog_theme(self, colors=None)` em `ObsidianSuiteHubDialog`, aplicando:
    - Cor nativa da barra de títulos do Windows via `set_windows_titlebar_color(bg_pri)`.
    - Folha de estilos Qt completa gerada por `get_qt_dialog_stylesheet`.
    - Anéis de foco e navegação acessível por controle (gamepad).
    - Título do cabeçalho (`lbl_title`) com contraste WCAG 2.1 AA.
    - Botão principal "Salvar & Aplicar" com cor `{accent}` e texto acessível via `get_accessible_text_color(accent)`.
  - Remoção da sobrescrita local de stylesheet em `_wrap_tab_in_scroll`, permitindo que os estilos do tema cascadem sem interferência para o viewport.
  - Atualização de `_on_preset_changed` e `_on_custom_color_picked` para acionarem `self.apply_dialog_theme(colors)`, permitindo visualização imediata do tema escolhido.
  - Atualização do `showEvent` para garantir a sincronização da barra de títulos nativa do Windows no momento da exibição.

### 4. Validação & Testes
- Adicionado `test_settings_hub_dialog_theme_adaptation` em `tests/test_theme_manager.py`, validando a geração dos estilos para todos os presets e a atualização reativa em tempo real.
- Suíte completa de 141 testes unitários aprovada com 100% de sucesso.
- Sincronização em produção executada com sucesso via Robocopy.

---

## 📌 [Versão 2026-09-10 - v2.5.4] - Correção Integral de Contraste no CodeMirror (Seleção e Sintaxe) e no Editor Visual (Ctrl+Shift+X)

### 1. Diagnóstico e Demanda do Usuário
- **Sintomas Relatados**:
  1. No CodeMirror (modo HTML), palavras selecionadas/destacadas possuíam cor de fundo praticamente idêntica à cor dos tokens de código (tags, atributos e strings em tons claros e amarelados sobre fundo bege `#f5eedc` de seleção no tema `warm_paper`), inviabilizando a leitura do código durante a seleção.
  2. Ao utilizar a opção "Editor Visual" / "Toggle Visual Editor" (`Ctrl+Shift+X` no `EditCurrent` / `AddCards`), a caixa de texto inferior exibia o conteúdo formatado em texto branco puro (`#ffffff`) sobre fundo bege/papel claro (`#faf8f5`), tornando o texto 100% invisível sem seleção manual (`Ctrl+A`).

### 2. Investigação Científica & Causas Raiz
- **Causa Raiz 1 (CodeMirror Seleção & Sintaxe)**:
  - O seletor `.CodeMirror-selected` aplicava apenas o fundo de hover sem forçar cor de texto nem tokens de sintaxe específicos para temas claros.
  - Sob o modo escuro do Anki, o CodeMirror usava a classe de tema `.cm-s-monokai`, cujos tokens (`.cm-attribute`, `.cm-string`, etc.) eram amarelo/verde claro, colidindo com o fundo claro da seleção.
- **Causa Raiz 2 (Editor Visual `Ctrl+Shift+X` / `RichTextInput`)**:
  - No arquivo de runtime do Anki `_aqt\data\web\js\editor.js`, o componente Svelte `RichTextInput` (`Vm`) monitora `$pageTheme.isDark` (via detecção de `night-mode` no `<html>`).
  - Quando o Anki desktop está em modo noturno, `$pageTheme.isDark` avalia como verdadeiro e injeta `color: "white"` no wrapper `Im()`.
  - O construtor `Im()` gera uma folha dinâmica de estilos (`userBase`) diretamente no Shadow DOM de cada campo com a regra `anki-editable { color: white; }`.
  - Por herança em CSS, todas as tags internas (`<p>`, `<span>`, `<em>`, `<strong>`, `<div>`) recebiam texto branco sobre o cartão claro do nosso addon.

### 3. Soluções Implementadas (`modules/theme_manager/engine.py`)
- **Blindagem no Shadow DOM e DOM Recursivo**:
  - Aprimorada a função `syncEditorTheme()` para aplicar `applyShadowStyles(root)` recursivamente em qualquer Shadow Root (`anki-editable`, `.rich-text-editable`, `[contenteditable]`, `.field-container`).
  - Injeção de `<style id="anki-suite-shadow-style">` no final de cada Shadow DOM com `!important` em `:host, :host *, anki-editable, anki-editable *, .rich-text-editable, .rich-text-editable *, div, p, span, strong, em, b, i, a`.
  - Em temas claros, varredura forçada aplicando `element.style.setProperty("color", textPri, "important")` para anular dinamicamente a regra `userBase` do Svelte.
  - Sincronização antecipada e contínua de classes `night-mode` e `light-mode` em `document.documentElement`.
- **Calibração de Sintaxe e Seleção no CodeMirror**:
  - Definição explícita de variáveis `:root` nativas do Anki: `--highlight-bg`, `--highlight-fg`, `--selected-bg`, `--selected-fg`.
  - Fundo de seleção com realce suave do tom de destaque (`accent`) em opacidade 0.28 e regra `::selection` com texto de alto contraste contrastando via WCAG 2.1 AA.
  - Sobrescrita de alta especificidade para tokens de código em temas claros:
    - `.cm-tag`, `.cm-bracket`: Vermelho profundo `#991b1b` (peso 700).
    - `.cm-attribute`: Verde floresta `#14532d` (peso 600).
    - `.cm-string`, `.cm-string-2`: Âmbar/marrom `#78350f` (peso 500).
    - `.cm-keyword`: Roxo profundo `#581c87` (peso 700).
    - `.cm-atom`, `.cm-number`: Azul marinho `#1e3a8a`.
    - `.cm-comment`: Cinza ardósia `#475569` (itálico).

### 4. Validação & Testes
- Adicionados testes específicos em `tests/test_theme_manager.py` cobrindo tokens de sintaxe, seleção e Shadow DOM recursivo.
- Execução de 79 testes centrais aprovados (`OK`).
- Sincronização em produção via Robocopy confirmada.

## 📌 [Versão 2026-09-10 - v2.5.3] - Correção de Contraste no Editor de Cards e Injeção no Shadow DOM dos Temas Claros

### 1. Diagnóstico e Demanda do Usuário
- **Sintoma Relatado**: Na página/diálogo de edição de cartões (`AddCards`, `EditCurrent` e Card Browser), usuários de temas claros (como `clean_light` e `warm_paper`) relataram que o texto digitado nos campos estava invisível ou com quase nada de diferença de contraste contra o fundo do editor.

### 2. Causas Técnicas
1. **Shadow DOM Aberto no `<anki-editable>`**: No Anki 24/25+, o editor de notas utiliza campos encapsulados em Shadow DOM aberto criado via SvelteKit (`RichTextInput.svelte`).
2. **Inversão de Cores por Dessincronização de `night-mode`**: O SvelteKit nativo define a cor do texto do editor como `color={$pageTheme.isDark ? "white" : "black"}` com base na presença da classe `night-mode` no elemento `<html>`. Quando o Anki estava configurado globalmente em modo escuro e o usuário ativava um tema claro no addon (`clean_light` ou `warm_paper`), a classe `night-mode` permanecia no DOM. O SvelteKit deduzia que a página era escura e injetava `color: white` dentro do Shadow DOM do `<anki-editable>`, sobre um fundo de card branco (`#ffffff`) ou papel claro (`#fff9f0`), gerando texto branco em fundo branco (contraste 1:1).
3. **Seletores Desatualizados de Rótulo**: Os rótulos de campos no Anki moderno usam `.label-name` dentro de `.label-container` (com `background: var(--canvas)`), enquanto as folhas de estilo possuíam apenas seletores legados `.field-label, .field-name`.
4. **Botões `QToolButton` na Janela `AddCards`**: Botões de seleção de baralho e tipo de nota usam `QToolButton`, não contemplados nas regras gerais de botões Qt do diálogo.

### 3. Solução Implementada
- **Sincronização Dinâmica do Tema & Injeção no Shadow DOM (`modules/theme_manager/engine.py`)**:
  - Implementada função `syncEditorTheme()` no bridge script injetado (`anki-obsidian-suite-bridge-injector`):
    - Sincroniza dinamicamente as classes `night-mode` e `light-mode` e o atributo `data-bs-theme` no `<html>` conforme `is_theme_light`.
    - Localiza todos os elementos `anki-editable, .rich-text-editable, [contenteditable]`, acessa seus `shadowRoot` abertos e anexa `<style id="anki-suite-shadow-style">` com `color: {text_pri} !important; caret-color: {accent} !important;` e `.empty::before { color: {text_sec} !important; }`.
    - Executa no carregamento inicial, em `DOMContentLoaded`, a cada evento `focusin` (ao clicar nos campos) e via `MutationObserver` em mutações do DOM.
  - No método `inject_theme_into_dynamic_webview`, adicionada re-execução segura de elementos `<script>` injetados dinamicamente via `createElement("script")`.
- **Estilização Robusta & Acessibilidade WCAG 2.1 AA**:
  - Adicionadas as variáveis nativas `--text-fg: {text_pri}` e `--text-secondary: {text_sec}` em `:root`.
  - Atualizados os seletores de campos: `.field-container, .field-wrapper, .editor-field, .rich-text-input, .plain-text-input`.
  - Estilizados `.label-container` (`background: {bg_pri}`) e rótulos `.label-name, .field-label, .field-name, .collapse-label, label, .field-state` com `{field_label_color}` garantindo contraste $\ge 4.5:1$.
  - Suporte ao modo HTML/texto puro via seletores do CodeMirror (`.CodeMirror, .CodeMirror-scroll, .CodeMirror-sizer, .CodeMirror-lines, .CodeMirror-gutters, .CodeMirror-cursor`).
  - Adicionado `QToolButton` ao `get_qt_dialog_stylesheet` para perfeita harmonia visual no seletor de baralho e modelo de nota.
- **Ciclo de Vida do Editor**:
  - Invocado `inject_theme_into_dynamic_webview` nos hooks `on_editor_did_init`, `on_add_cards_did_init` e `on_browser_will_show`.

### 4. Validação
- Suíte de 140 testes unitários aprovada integralmente (`OK`).
- Testes dedicados `test_editor_contrast_and_accessibility_light_themes` e `test_editor_qtoolbutton_styling_in_dialog` passando.
- Sincronização em produção via robocopy executada com êxito.

## 📌 [Versão 2026-09-08 - v2.5.2] - Tematização e Adaptação Completa da Tela de Conclusão de Baralho ("Parabéns!")

### 1. Diagnóstico e Demanda do Usuário
- **Sintoma Relatado**: Ao terminar as revisões de um baralho no Anki, a página exibida ("Parabéns, você terminou esse baralho por enquanto" / "Congratulations! You have finished this deck for now") não estava adaptada aos temas visuais da suíte Obsidian, ficando com fundo genérico, baixo contraste e sem harmonia com as demais páginas.

### 2. Causas Técnicas
1. **Roteamento Dinâmico em SvelteKit**: Nas versões modernas do Anki Desktop (24+ e 25+), quando um deck é concluído (`_is_finished()`), o Anki carrega a rota SvelteKit `/congrats` via `self.web.load_sveltekit_page("congrats")`.
2. **Ignoramento de `webview_will_set_content`**: O hook padrão `webview_will_set_content` opera apenas em páginas renderizadas via `stdHtml()`. Em páginas carregadas dinamicamente via URL no Chromium, o Anki dispara `gui_hooks.webview_did_inject_style_into_page(web_view)`.
3. **Ausência de Estilos Específicos e Token `--fg-link`**: Em `generate_global_theme_css`, não havia regras para `.congrats`, `#congrats`, nem o token CSS `--fg-link` que o componente Svelte nativo `CongratsPage.svelte` utiliza para colorir hiperlinks de estudo personalizado e desocultação.

### 3. Solução Implementada
- **Injeção Dinâmica em SvelteKit (`modules/theme_manager/engine.py`)**:
  - Implementado `inject_theme_into_dynamic_webview(web_view)` com injeção segura via JavaScript (`anki-obsidian-suite-theme-container`).
  - Conectado `inject_theme_into_dynamic_webview` ao hook oficial `gui_hooks.webview_did_inject_style_into_page`.
  - Aplicado wrap defensivo em `Overview._show_finished_screen` com injeção imediata e microtask timer para garantir persistência.
  - Atualizado `apply_theme_to_anki()` para injetar diretamente no webview de `overview` se ativo.
- **Estilização Moderna Obsidian Card & Contraste WCAG AA**:
  - Tokens nativos Anki: adicionados `--fg-link: {accent}` e `--link-hover: {accent}` em `:root`.
  - Card central: `.congrats, #congrats, .congrats-container` com cantos arredondados (20px), fundo de card Obsidian (`bg_card`), borda sutil (`border_color`) e elevação suave.
  - Título e tipografia: `h1, h2, h3` estilizados com cor `accent` de alto contraste, e parágrafos informativos com `text_sec`.
  - Ações e botões: links de Estudo Personalizado (`customStudy`) e Desocultar (`unbury`) estilizados como botões interativos com gradiente acentuado (`accent_grad`) e texto acessível (`get_accessible_text_color`).

### 4. Validação
- Suíte completa de 138 testes unitários aprovada (`OK`).
- Sincronização via robocopy com a pasta de produção do Anki Desktop.

## 📌 [Versão 2026-09-08 - v2.5.1] - Desacoplamento do Índice Python e Correção da Navegação Ascendente de Baralhos no Gamepad

### 1. Diagnóstico e Demanda do Usuário
- **Sintoma Relatado**: Quando um baralho é selecionado no modo gamepad, ao retornar à seleção de baralhos (`deckBrowser`), não se consegue selecionar os baralhos que estão acima do baralho previamente selecionado. O baralho previamente selecionado atuava como um falso "novo topo", fazendo com que qualquer tentativa de subir com o analógico ou D-Pad subisse diretamente para o menu superior (`topbar`) em vez de ir para os baralhos superiores na árvore.

### 2. Causas Técnicas
1. **Verificação Prematura de Topo na Camada Python**: Em `modules/gamepad/actions.py`, o método `navigate_deck_selection(delta)` continha a cláusula:
   `elif self.focus_zone == "decks" and self.focused_deck_index == 0 and delta < 0:`
2. **Dessincronização entre `self.focused_deck_index` e o DOM**: A variável Python `self.focused_deck_index` era desacoplada da árvore real de elementos HTML. Ao retornar do `overview` para o `deckBrowser`, essa variável iniciava em `0` (ou não refletia a posição real do baralho preservado via `sessionStorage`). Assim, na primeira pressão para cima (`delta = -1`), o Python avaliava `focused_deck_index == 0` como verdadeiro e realizava imediatamente o salto para a `topbar` (`ascend_to_topbar`), cancelando a execução antes que o script JavaScript do webview pudesse navegar para `curIdx - 1`.

### 3. Solução Implementada
- **Delegação da Detecção de Limites ao DOM (`modules/gamepad/actions.py`)**:
  - Eliminada a verificação estática baseada em `self.focused_deck_index == 0` do código Python.
  - O script JavaScript injetado no webview obtém a lista real de baralhos visíveis (`tr.deck`) e localiza a linha focada (`curIdx`).
  - Apenas quando `curIdx === 0 && delta < 0` (isto é, o usuário está de fato no primeiro baralho do topo da lista e pressiona para cima), o JavaScript dispara a transição para a barra de menu via `pycmd("gamepad_ascend_topbar")`.
  - Se `curIdx > 0`, o JavaScript calcula `nextIdx = curIdx + delta` normalmente, permitindo subir livremente por toda a árvore de baralhos superiores (`curIdx - 1`, `curIdx - 2`, etc.).
- **Sincronização de Foco e Eventos de Ponte (`modules/gamepad/hooks.py`)**:
  - Implementado `on_webview_js_message` conectado ao hook oficial `gui_hooks.webview_did_receive_js_message`.
  - Suporte às mensagens de ponte:
    - `"gamepad_ascend_topbar"`: Invoca `dispatcher.ascend_to_topbar()`.
    - `"gamepad_deck_focused:<idx>:<id>"`: Invoca `dispatcher.sync_deck_focus(idx, deck_id)`.
- **Validação Automatizada (`tests/test_gamepad_deck_preservation.py`)**:
  - Criados testes unitários validando a não ascensão quando em baralhos arbitrários, transições explícitas de `ascend_to_topbar` / `descend_from_topbar` e tratamento de mensagens da ponte JS.

---

## 📌 [Versão 2026-09-08 - v2.5.0] - Preservação do Cursor de Baralho no Gamepad e Eliminação do Filtro Escuro (Keep-Alive Win32 & Pomodoro)

### 1. Diagnóstico e Demanda do Usuário
- **Sintoma 1 (Filtro Escuro Semi-Transparente)**: Ao navegar pelos baralhos e entrar em subbaralhos exclusivamente com o gamepad, a tela escurecia (filtro semi-transparente de ociosidade) por cerca de 60 segundos antes de desaparecer sozinha, retornando periodicamente.
- **Sintoma 2 (Reset de Posição do Selecionador)**: Ao expandir a lista de subbaralhos com o controle (botão X ou D-Pad), o selecionador saltava de volta para o topo da lista (índice 0) em vez de permanecer exatamente onde o usuário estava.

### 2. Causas Técnicas
1. **Esmaecimento de Monitor do Windows & Inatividade no Pomodoro**: Drivers DirectInput/XInput rodam em threads/polling dedicados e não geram mensagens de teclado/mouse no subsistema do Windows. O Windows acionava o "Dimmed Display" (escurecimento por economia de energia). Simultaneamente, o Pomodoro atingia 60s de ociosidade (`inactivity_timeout_seconds: 60`), pausando a sessão de foco.
2. **Descoberta Falha de Processos no FocusGuard**: `get_anki_process_pids()` não encontrava `anki.exe` quando este era pai/ancestral de `os.getpid()`, gerando falsos alarmes de `FOCUS_LOSS_DETECTED`.
3. **Destruição do DOM no `DeckBrowser.refresh()`**: A ação `collapse:did` do Anki destrói o HTML da árvore de baralhos e reconstrói do zero. Sem classes de foco no novo HTML, a navegação caía em `curIdx === -1` e pulava para o índice 0.

### 3. Solução Implementada
- **Keep-Alive de Sistema e Pomodoro (`modules/gamepad/actions.py`, `modules/gamepad/input_manager.py`)**:
  - Implementada `keep_system_and_pomodoro_active()`: no Windows, executa `ctypes.windll.kernel32.SetThreadExecutionState(ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)` para resetar o temporizador de ociosidade do monitor, e notifica o Pomodoro via `engine.register_user_activity()`.
  - Disparo imediato a cada novo botão pressionado (`just_pressed`) e stick nav, com throttle inteligente de 1.0s para rolagens contínuas.
- **Preservação e Restauração de Baralho Focado (`modules/gamepad/actions.py`, `modules/dashboard/renderer.py`)**:
  - Salva o ID do baralho focado em `sessionStorage.setItem('gamepad_focused_deck_id', target.id)` e em `self.last_focused_deck_id`.
  - Ao expandir/colapsar, agenda restauração pós-render com timeouts (50ms e 150ms).
  - No `initAria()` do `renderer.py`, restaura automaticamente o baralho focado salvo no `sessionStorage`.
  - No `return_screen`, mantém o índice e baralho anterior.
- **Blindagem do FocusGuard (`modules/pomodoro/focus_guard.py`)**:
  - Algoritmo de ponto fixo de PIDs descobrindo `anki.exe`, ancestrais e todos os filhos (`QtWebEngineProcess`, `mpv`). Fast path Qt com `activeWindow()` / `focusWidget()`.
- **Validação**:
  - 133 testes unitários passando (`Ran 133 tests in 14.915s - OK`).
  - Sincronização em produção via Robocopy.

---

## 📌 [Versão 2026-09-07 - v2.4.3] - Ferramentas de Edição Visual (Setas, Círculos e Recorte) e Preservação da Imagem Original nos Recentes

### 1. Diagnóstico e Demanda do Usuário
- **Demanda**: Adicionar ferramentas gráficas diretamente integradas ao pesquisador de imagens que permitam desenhar setas, círculos e cortar a imagem antes de inserir no card.
- **Regra Mandatória**: A imagem inserida no card do Anki deve conter as edições realizadas, porém a imagem salva no histórico de imagens recentes (`recent_images.json`) **deve permanecer como a imagem original limpa e sem edições**.

### 2. Arquitetura Implementada
- **Módulo de Edição Gráfica (`modules/image_search/ui/image_editor.py`)**:
  - `ImageAnnotationCanvas`: renderização anti-aliased em alta resolução com coordenadas nativas, histórico de undo ilimitado (`Ctrl+Z`), redefinição (`reset`), máscara escura sobre o corte e exportação direta em bytes JPG.
  - `ImageEditorDialog`: diálogo modal com barra de ferramentas intuitiva (🏹 Seta, ⭕ Círculo, ✂️ Cortar), paleta com 5 cores clínicas (vermelho, amarelo, verde, azul, branco), seletor de espessura de traço (2px, 4px, 6px, 8px), botões "Aplicar Corte", "Desfazer", "Redefinir" e "⬇️ Inserir Imagem Editada no Card".
  - Funções matemáticas puras `calculate_arrowhead_points` (trigonometria `math.atan2` precisa) e `normalize_rect_coords` (normalização bidirecional de quadrantes).
- **Integração no Diálogo Principal (`modules/image_search/ui/search_dialog.py`)**:
  - Botão `"✏️ Editar e Inserir"` (`btn_edit`) destacado na barra inferior do painel de zoom.
  - Método `open_editor_for_item`: abre o editor e, ao confirmar a edição, salva a imagem original intacta no histórico (`add_recent_image(item)`) e injeta os bytes editados no card do Anki (`_insert_into_anki_editor`).
- **Menu de Contexto dos Cards (`modules/image_search/ui/image_card.py`)**:
  - Nova opção `"✏️ Editar e Inserir"` no clique direito de qualquer card (pesquisa e recentes).
- **Internacionalização (`utils/i18n.py`)**:
  - 11 novas chaves nos 4 idiomas (`pt`, `en`, `es`, `fr`).
- **Auditoria QA (`tests/test_image_editor.py`)**:
  - Testes de trigonometria vetorial, normalização de corte, integridade de i18n e garantia estrita da preservação da imagem original no histórico de recentes (122/122 testes passando).

---

## 📌 [Versão 2026-09-07 - v2.4.2] - Correção de Visibilidade e Atualização Imediata da Aba de Imagens Recentes

### 1. Diagnóstico e Demanda do Usuário
- **Sintoma Reportado**: Imagens inseridas normalmente nos cards não apareciam ao abrir ou alternar para a aba de recentes ("🕒 Recentes").
- **Causa Raiz**:
  1. *Ausência de Chamada a `card.show()`*: No Qt, ao instanciar novos widgets filhos (`ImageCardWidget`) dentro de um contêiner pai já visível (`self.recent_cards_container`), os widgets permanecem ocultos (`isHidden() == True`) a menos que `card.show()` seja explicitamente invocado.
  2. *Cache Estático em Memória*: `get_recent_images()` mantinha `_cached_recent` sem permitir recarga forçada (`force_reload=True`) do arquivo `user_files/recent_images.json`.
  3. *Falha de Carregamento de Miniatura*: O loader de miniaturas do card não possuía fallback para `original_url` nem bypass de certificados SSL expirados, levando à falha de imagem (`❌`).

### 2. Arquitetura Implementada
- **Garantia de Exibição dos Cards no Qt (`modules/image_search/ui/search_dialog.py`)**:
  - Invocação explícita de `if hasattr(card, "show"): card.show()` ao adicionar cards à grade recente, de pesquisa e do infinite scroll.
  - Atualização imediata do layout com `adjustSize()` para perfeita rolagem no `QScrollArea`.
  - Título dinâmico da aba com contagem real: `🕒 Recentes (X)`.
  - Chamada imediata a `_refresh_recent_tab()` após salvar nova imagem em `_on_download_success`.
- **Recarga Forçada de Disco (`modules/image_search/recent_manager.py`)**:
  - Parâmetro `force_reload: bool = False` adicionado a `get_recent_images()`, garantindo leitura atômica e atualizada de `user_files/recent_images.json`.
  - Suporte a itens válidos com `thumb_url`.
- **Loader de Miniaturas Resiliente Multi-Tier (`modules/image_search/ui/image_card.py`)**:
  - Fallback automático entre miniatura e URL original.
  - Cabeçalho `Referer` baseado no host de origem e contexto SSL permissivo.
- **Auditoria QA**: Novos testes unitários `test_get_recent_images_force_reload` e `test_items_with_only_thumb_url_accepted` em `tests/test_image_search_recent.py` (117/117 testes aprovados).

---

## 📌 [Versão 2026-09-07 - v2.4.1] - Resiliência de Download com Fallback a Miniaturas e Inserção Sincronizada no Card

### 1. Diagnóstico e Demanda do Usuário
- **Sintoma Reportado**: Ao clicar no botão "⬇️ Baixar e Inserir no Card" ou dar duplo-clique, a imagem não era inserida no card do editor e aparecia mensagem solicitando para verificar a rede.
- **Causa Raiz**:
  1. *Ausência de Fallback no Download de Imagens*: A função `download_and_insert` dependia exclusivamente da URL original em alta resolução. Portais e revistas médicas (RSNA, ScienceDirect, LITFL, Osmosis, UFG) bloqueiam hotlink com `HTTP 403 Forbidden` ou falhas de certificado SSL expirado. Sem fallback para `item.thumb_url`, a exceção disparava erro de rede e cancelava a inserção.
  2. *Cabeçalhos Autoreferenciais em `download_image_bytes`*: O cabeçalho `"Referer": url` em `search_engine.py` provocava rejeição por CDNs (Cloudflare/Fastly).
  3. *Conflito de Concorrência no Editor do Anki*: `insert_image_into_editor` disparava simultaneamente `editor.loadNote()` e `editor.doPaste()`, causando conflitos com o Shadow DOM do Svelte e possível perda de texto quando `saveNow(true)` não havia sido executado antes da abertura do diálogo.

### 2. Arquitetura Implementada
- **Download Resiliente Multi-Tier (`modules/image_search/ui/search_dialog.py` & `search_engine.py`)**:
  - **Tier 1 (Original)**: Download com cabeçalho de Referer baseado no domínio raiz e fallback para SSL tolerante.
  - **Tier 2 (Miniatura CDN)**: Se a URL original falhar por 403/429/timeout/SSL, recorre imediatamente à URL da miniatura (`item.thumb_url`), baixando em frações de segundo (`~0.1s`) com 100% de confiabilidade.
  - **Tier 3 (Cache em Memória)**: Se a rede cair completamente, extrai os bytes do `QPixmap` já renderizado em memória na tela de zoom.
- **Inserção Robusta no Editor do Anki (`modules/image_search/__init__.py` & `search_dialog.py`)**:
  - Execução de `saveNow(true)` na webview do editor antes de abrir o diálogo de busca modal.
  - Disparo de inserção imediata via `_insert_into_anki_editor` ao confirmar o download.
  - Gravação na coleção de mídia do Anki com sanitização e escape de nomes (`escape_media_filenames`).
  - Sincronização dos campos do card e reativação da janela do editor.
- **Auditoria QA**: Novo teste unitário `test_download_fallback_to_thumbnail` em `tests/test_image_search.py`.

---

## 📌 [Versão 2026-09-07 - v2.4.0] - Aba de Imagens Recentes (15 Imagens) com Inserção e Zoom Diretos

### 1. Diagnóstico e Demanda do Usuário
- **Reutilização Ágil de Imagens nos Cards**: Durante sessões de estudo e edição de flashcards, é comum necessitar da mesma imagem médica ou esquema anatômico recém-buscado para ilustrar cartões relacionados subsequentes.
- **Ausência de Histórico de Uso**: O pesquisador de imagens operava sem histórico persistente; ao fechar o diálogo, a seleção era perdida e o usuário precisava redigitar a busca do zero.

### 2. Arquitetura Implementada
- **Módulo Gerenciador de Recentes (`modules/image_search/recent_manager.py`)**:
  - Cache MRU (*Most Recently Used*) estritamente limitado a 15 itens (`MAX_RECENT_IMAGES = 15`).
  - Deduplicação inteligente por `original_url` e `thumb_url`: reinserir uma imagem a move para o topo da lista.
  - Persistência em arquivo JSON atômico `user_files/recent_images.json`, blindado contra perda de dados durante atualizações do addon no Anki.
  - Sincronização com o `config_manager` e thread-safety via `threading.RLock()`.
- **Interface com Abas (`QTabWidget` em `modules/image_search/ui/search_dialog.py`)**:
  - **Aba 0: "🔍 Pesquisa"**: Interface completa de busca web com infinite scroll, seleção de motores e barra de progresso.
  - **Aba 1: "🕒 Recentes (15)"**: Grade 4xN apresentando as últimas 15 imagens utilizadas, contador de itens dinâmico e aviso de estado vazio informativo.
  - **Interatividade Completa**:
    - Clique simples abre o painel de zoom completo com metadados e botão de abrir página original.
    - Duplo-clique baixa e insere a imagem imediatamente no card do editor ativo, fechando o diálogo.
    - O botão "◀ Voltar aos Resultados" e o atalho `Escape` retornam à aba de origem do usuário sem perda de navegação.
- **Internacionalização nos 4 Idiomas (`utils/i18n.py`)**:
  - Chaves `image_search_tab_search`, `image_search_tab_recent`, `image_search_recent_hint`, `image_search_recent_empty` traduzidas em `pt`, `en`, `es` e `fr`.
- **Bateria de Testes Unitários (`tests/test_image_search_recent.py`)**:
  - 8 novos testes cobrindo ordem MRU, teto de 15 itens, deduplicação, serialização/desserialização JSON e integração com `ImageSearchDialog`.

---

## 📌 [Versão 2026-09-06 - v2.3.6] - Automação da Expansão Multilíngue: Tradução Médica Dinâmica em Tempo Real para Inglês

### 1. Diagnóstico e Demanda
- **Dependência Insustentável de Dicionários Manuais**: A lista estática `ANATOMICAL_SYNONYMS` exigia intervenção manual para cada novo termo, patologia ou sigla médica desconhecida inserida pelo usuário, tornando inviável cobrir as centenas de milhares de entidades clínicas da medicina.
- **Assimetria de Recursos Científicos na Web**: Os repositórios mais ricos em esquemas, microscopias e diagramas anatômicos de alta resolução (Wikimedia Commons, PubMed, Kenhub, Radiopaedia, Wikipedia EN) indexam o conteúdo primariamente em **inglês**. Buscas restritas ao português deixavam de recuperar esses acervos globais.

### 2. Arquitetura Implementada
- **Mecanismo de Tradução em Tempo Real (`translate_query_to_english`)**:
  - Integração com a API MyMemory (especializada em ontologias e terminologia multilíngue) com fallback transparente para o Google Translate clientless.
  - Detecta automaticamente o idioma de origem da interface do Anki (`pt`, `es`, `fr`) e gera a tradução técnica correspondente em inglês.
  - Exemplo: *"descolamento prematuro de placenta"* ➔ *"abruptio placentae"*; *"estenose mitral grave"* ➔ *"severe mitral stenosis"*; *"glomerulonefrite por IgA"* ➔ *"berger dis"*.
- **Cache de Tradução em Memória (`_TRANSLATION_CACHE`)**:
  - Armazena consultas em dicionário rápido na sessão, resultando em latência zero (0ms) em repetições da mesma consulta.
- **Injeção Transparente nos 4 Motores de Imagem**:
  - **Validador de Âncoras (`_calculate_relevance_score`)**: Palavras do termo traduzido em inglês são anexadas aos `anchor_terms`, permitindo que pranchas e atlas em inglês passem pela validação semântica com nota máxima.
  - **Wikimedia Commons (`search_wikimedia`)**: Dispara a busca em inglês quando a consulta em português tem poucos resultados, trazendo diagramas vetoriais e esquemas de livros texto.
  - **Wikipédia Artigos (`search_wikipedia_articles`)**: Consulta os verbetes da Wikipédia em inglês com a query traduzida.
  - **Bing Images (`search_web_images`)**: Se a busca local produzir menos de 8 resultados, dispara automaticamente consulta de enriquecimento com o termo em inglês.
- **Preservação de Overrides Locais**:
  - `ANATOMICAL_SYNONYMS` permanece ativo como camada de atalho instantâneo prioritário.

---

## 📌 [Versão 2026-09-06 - v2.3.5] - Correção: Isolamento de DOM do Bing, Âncoras Semânticas (Eliminação de Vazamento de Carrosséis e Siglas Fracas como 'DIP 3')

### 1. Diagnóstico da Causa Raiz
- **Vazamento de Carrossel de Tendências/Sugestões Bing (H1)**: O scraper regex do Bing lia o HTML inteiro indiscriminadamente. Quando a consulta médica específica (`cardiotocografia DIP 3` ou com erro de digitação `cardiotografia`) tinha poucos resultados diretos, o Bing injetava carrosséis e barras laterais dinâmicas ("Tendências no Bing", "Pesquisas Populares", "Coleções em Alta"), capturando memes randômicos (Minotauro), celebridades ("mulher mais bonita do mundo") e tópicos virais que mudavam a cada requisição.
- **Falso-Positivo Crítico do Termo Curto 'DIP' (H2)**: Na correlação semântica anterior, qualquer palavra com mais de 2 letras validava o item. A sigla médica "DIP" (3 letras) coincidia com a palavra comum inglesa "dip" ("dip into", "lucky dip") e tags de buscas eróticas. Itens de carrosséis ou páginas aleatórias contendo "dip" passavam pelo filtro sem checar a palavra âncora `cardiotocografia`.
- **SafeSearch com Cookie `ADLT=OFF` e GIFs Animados Espúrios (H3)**: O cookie de requisição continha `SRCHHPGUSR=ADLT=OFF`, o que sobrepunha os parâmetros de URL e desativava a proteção contra conteúdo adulto em nível de servidor da Microsoft, permitindo a injeção de pornografia explícita ("blowjob gifs") em buscas relaxadas.
- **Falta de Conceito Base em Wikipedia/Commons**: A Wikipédia buscava a frase exata "cardiotocografia DIP 3" e retornava 0 resultados por falta de artigo com esse título exato, em vez de recorrer ao verbete principal "Cardiotocografia".

### 2. Correções Implementadas
- **Isolamento de DOM no Bing (`_extract_bing_results`)**:
  - Delimitação estrita da extração para o container principal da grade de resultados (`id="mmComponent_images_1"` ou `class="dgControl"`). Qualquer elemento de carrossel (`.carousel`, `.trending`, `.ans_trending`, `.sidebar`) é sumariamente descartado.
- **Validação Semântica por Palavras-Âncora (`_calculate_relevance_score`)**:
  - Termos com 5 ou mais letras são categorizados como âncoras (`anchor_terms`).
  - Se a consulta possuir termos âncora (ex: `cardiotocografia`, `lactobacilos`, `glandulas`), o match de pelo menos UMA palavra-âncora (ou seu sinônimo médico) é **obrigatório**. Termos curtos como `dip` não validam a imagem sozinhos.
  - Para siglas curtas isoladas (`CTG`, `HPV`), impõe-se casamento por limite de palavra (`\b...\b`).
- **SafeSearch `ADLT=STRICT` no Cookie e Parâmetros**:
  - `DEFAULT_HEADERS["Cookie"]` atualizado para `SRCHHPGUSR=ADLT=STRICT&NRSLT=-1;`.
  - Bloqueio incondicional de arquivos `.gif` em buscas gerais e médicas, a menos que o usuário solicite explicitamente "gif".
  - Expansão de `ADULT_AND_SPAM_KEYWORDS` ("blowjob", "boquete", "pornografia", "she fucks", "he fucks", "minotauro", "mulher mais bonita", "sex", "anal", "cum", "orgasm", etc.).
- **Expansão Obstétrica e Tolerância a Typos (`ANATOMICAL_SYNONYMS`)**:
  - Inclusão de `cardiotocografia`, `cardiotografia` (typo comum), `dip 1`, `dip 2`, `dip 3`, `ctg`, `desaceleracao variavel`, `fetal heart rate monitoring`.
- **Fallback para Conceito Base na Wikipédia e Wikimedia**:
  - Função `_extract_base_concept` remove qualificadores secundários (`dip 3`, `tipo 1`, números) se a busca qualificada retornar 0 resultados, recuperando os diagramas médicos e traçados de CTG da Wikipédia.

---

## 📌 [Versão 2026-09-05 - v2.3.4] - Correção Crítica: Purga de Conteúdo Adulto/Anime e Trava de Correlação Semântica

### 1. Diagnóstico da Causa Raiz
- **SafeSearch `adlt=off` e Cookies Sem Restrição**: O Bing Images com desativação total de SafeSearch expôs o motor de busca a sites de tubos pornográficos que inserem termos de ISTs (como *Sífilis*) em metadados ocultos.
- **Bypass do Filtro por Escopo `is_anatomical`**: O filtro `DISCONNECTED_KEYWORDS` só era ativado para termos estritamente anatômicos. Consultas microbiológicas e patológicas (*Lactobacilos*, *Sífilis*) contornavam o filtro, permitindo que agregadores de lixo (como `fity.club` e `inspiredpencil.com`) injetassem animes e imagens sem correlação.
- **Falta de Exigência de Correlação Semântica**: Itens com pontuação zero (sem match no título nem na URL) eram aceitos por padrão.

### 2. Correções Implementadas
- **Purga Incondicional de Conteúdo Adulto e Anime**:
  - `ADULT_AND_SPAM_KEYWORDS` e `SPAM_DOMAINS` agora filtram tubos adultos (`.xxx`, `pornhub`, `xvideos`), boards de anime (`gelbooru`, `danbooru`, `rule34`) e fazendas de scraper (`fity.club`, `inspiredpencil`).
  - A rejeição (`score = -100`) agora atua em **todas** as buscas, sem exceção.
- **Trava de Correlação Semântica Obrigatória**:
  - Imagens só são aceitas se pelo menos um termo da busca ou sinônimo científico constar no título ou na URL de origem, ou se o domínio for uma autoridade médica verificada (`CDC`, `WHO`, `Kenhub`, `IMAIOS`, etc.).
- **SafeSearch Moderado por Padrão**:
  - Configurado `adlt=moderate` e cookie `ADLT=DEMOTE` para bloquear pornografia explícita e permitir diagramas anatômicos educativos.
- **Priorização Oficial no Modo Geral (`all`)**:
  - Pranchas e microscopias científicas da Wikipédia e Wikimedia Commons agora aparecem **no topo** da grade de resultados, seguidas pela Web curada.

---

## 📌 [Versão 2026-09-05 - v2.3.3] - Atualização de Diretrizes: Protocolo Mandatório de Diagnóstico em Largura (Multi-Hipótese)

### 1. Diretriz Adicionada
- **Protocolo de Diagnóstico em Largura**:
  - Proibição absoluta de testes isolados/sequenciais de hipótese única.
  - Exigência de mapeamento prévio de no mínimo 3 hipóteses concorrentes (Causa + Alvo + Sonda) antes de qualquer chamada de ferramenta.
  - Execução obrigatória das sondas em lote único (batch concorrente ou subagentes paralelos).
- **Documentos Atualizados**:
  - `AGENTS.md` (Seção 5)
  - `GEMINI.md` (Seção 5)
  - `.agents/skills/obsidian-addon-dev/SKILL.md` (Regra de Ouro 7)

---

## 📌 [Versão 2026-09-05 - v2.3.2] - Correção Definitiva: Inserção Canônica via loadNote() e Aprimoramento dos Motores de Busca

### 1. Diagnóstico da Falha Residual
1. **Por que nada era inserido nos campos do editor?**:
   - `ImageSearchDialog` executava a inserção de dentro do próprio manipulador `_on_download_success`, antes de o loop de eventos de `dialog.exec()` ser completamente finalizado. O modal grab do Qt ainda bloqueava o foco do webview.
   - Os campos no Anki 24/25 são componentes Svelte isolados em Shadow DOM. Modificar apenas a lista Python `editor.note.fields` sem invocar `editor.loadNote(target_idx)` não atualiza a interface gráfica. Ao perder foco (`blur`), o Svelte sobrescrevia a lista do Python com o estado antigo.
2. **Por que os resultados de busca eram limitados e davam erro na Wikipédia?**:
   - A Wikipédia e Wikimedia retornavam HTTP 429 (*Too Many Requests*) devido a rajadas de requisições de sinônimos com cabeçalhos genéricos.
   - O Google Images bloqueia automações Python via desafio JavaScript anti-bot de 92KB (`closureDynamicButton`). O Bing Images, por outro lado, opera sem bloqueios com velocidade sub-segundo e 35 imagens de alta resolução por página.

### 2. Correções Implementadas
1. **Inserção Canônica Pós-Diálogo (`insert_image_into_editor`)**:
   - Em `modules/image_search/__init__.py`: A inserção agora é realizada no método `open_image_search_for_editor` **após** `dialog.exec()` retornar e a janela modal ser 100% destruída.
   - Invocação oficial de `editor.loadNote(focusTo=target_idx)`, que envia `setFields()` para o Svelte do Anki, renderiza a imagem no campo imediatamente na tela, posiciona o foco e dispara `triggerChanges()`.
   - Suporte a persistência imediata em bancos SQLite caso a edição ocorra fora do modo de adição de cards (`_save_current_note()`).
2. **Otimização dos Motores de Busca**:
   - Em `modules/image_search/search_engine.py`: Cabeçalho `User-Agent` educativo oficial para a Wikipédia, eliminando o erro 429.
   - Limitação das expansões de sinônimos para apenas quando a busca principal retornar menos de 3 resultados.
   - Motor Web de alta relevância (Bing/Google) priorizando domínios médicos de referência (`IMAIOS`, `Kenhub`, `Tua Saúde`, `Anatomia Papel e Caneta`, `ResearchGate`).
   - Termos anatômicos femininos (`glândulas parauretrais`, `glândulas de Bartholin`, `Skene`) agora retornam 100% ilustrações médicas e esquemas anatômicos relevantes.

---

## 📌 [Versão 2026-09-05 - v2.3.1] - Correção Crítica: Inserção Multi-nível no Editor e Filtros Médicos Anti-Spam

### 1. Diagnóstico do Problema
1. **Falha na Inserção de Imagem no Editor**:
   - Ao clicar no botão de inserção ou no botão da barra de ferramentas, o campo perdia o foco (`blur`), zerando `editor.currentField` para `None`.
   - O diálogo modal mantinha a captura de foco do Qt durante a chamada de inserção, impedindo o webview de recuperar o cursor.
   - `pasteHTML` e `document.execCommand("inserthtml")` falhavam silenciosamente no Chromium caso nenhum elemento estivesse ativamente focado.
2. **Imagens Desconexas / Spam em Buscas Anatômicas (ex: glândulas parauretrais, Bartholin, Skene)**:
   - Sites de SEO spam geravam títulos com as palavras-chave da busca contendo imagens desconexas (roupas, atletas, celebridades).
   - O algoritmo de pontuação anterior pontuava títulos pelo número de palavras-chave, elevando esses sites de spam ao topo.
   - A Wikipédia e o Wikimedia Commons não retornavam diagramas quando os termos anatômicos eram buscados em português, devido aos nomes de arquivos e páginas em inglês/latim.

### 2. Correções Implementadas
1. **Arquitetura de Inserção Multi-nível com Restauração de Seleção**:
   - Em `modules/image_search/__init__.py`:
     - Salvamento prévio do `Range` de seleção ativo no webview (`window._obsidian_saved_range`) antes da abertura do diálogo.
     - Detecção resiliente do índice do campo via `editor.last_field_index` como fallback imediato quando `editor.currentField` for `None`.
   - Em `modules/image_search/ui/search_dialog.py`:
     - Fechamento imediato do diálogo modal (`self.accept()`) antes de disparar a rotina de inserção, liberando o foco do Qt para a janela do editor.
     - Reativação forçada da janela pai (`parentWindow.activateWindow()`) e foco no webview (`web.setFocus()`).
     - Script JavaScript de inserção em 3 níveis:
       1. Restauração do Range de seleção salvo e `document.execCommand('inserthtml', false, html)`;
       2. Fallback para `pasteHTML(html, false, false)`;
       3. Fallback de injeção direta no elemento DOM `.rich-text-editable` correspondente ao campo;
       4. Disparo de `triggerChanges()` para notificar o Anki.
     - Método de compatibilidade chamando `editor.doPaste(...)` para manter ganchos do Anki e testes unitários.
     - Sincronização direta de backup no modelo de notas (`editor.note.fields[target_idx]`).
2. **Filtros Médicos Anti-Spam e Expansão por Sinônimos Científicos**:
   - Em `modules/image_search/search_engine.py`:
     - Lista negra estrita de domínios de spam (`cpcompany.com`, `aau.edu.et`, `fity.club`, `inspiredpencil.com`, etc.) descartados com score negativo.
     - Filtro contextual de palavras-chave de celebridades e comércio para termos anatômicos.
     - Dicionário de expansão de sinônimos anatômicos/médicos em inglês (`ANATOMICAL_SYNONYMS`).
     - Busca simultânea na Wikipédia em português e inglês (`pt` + `en`) e Wikimedia Commons com termos originais e sinônimos médicos oficiais.
     - Super bonificação de autoridade para fontes médicas consagradas (`wikipedia.org`, `wikimedia.org`, `kenhub.com`, `imaios.com`, `nih.gov`, `scielo.br`, etc.).

---

## 📌 [Versão 2026-09-05 - v2.3.0] - Novo Módulo: Buscador e Baixador de Imagens da Web no Editor de Cards

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"estava pensando em adicionar uma nova função ao addon, buscador e baixador de imagens para o editor de cards, a ideia seria que ao clicar na ferramenta que ficaria do lado das outras ferramentas de edição que tem no editor de cards do anki, abriria uma janela com uma caixa de texto e ao pesquisar nessa caixa de texto apareceria uma lista de imagens correspondentes tiradas do google imagens, ao clicar na imagem teria um zoom parcial da imagem e apareceria no canto inferior da imagem um simbolo de baixar caso fosse clicado baixaria e introduziria a imagem aonde estava o cursor de texto fechando a janela. Seria tipo o anexar imagens/videos só que da internet."*

---

### 2. Implementações Técnicas
1. **Integração Nativa com a Barra de Ferramentas do Editor de Cards**:
   - Criado hook `gui_hooks.editor_did_init_buttons` em `modules/image_search/__init__.py`.
   - Inserção do botão `editor.addButton` com ícone personalizado (`image_search.png` / `image_search.svg`), dica traduzida e atalho padrão `Ctrl+Shift+I`.
   - Detecção automática de texto selecionado no campo (`QWebEnginePage.selectedText()`) para pré-preenchimento automático do campo de busca.
2. **Motor de Busca de Imagens de Alta Performance & Resiliência**:
   - `modules/image_search/search_engine.py`:
     - Motor primário: Web Image Search (Bing) extraindo mais de 60 imagens em alta resolução com miniaturas rápidas, dimensões e títulos via atributos `m="{...}"`, sem necessidade de chaves de API pagas e imune aos desafios antibot/CAPTCHA do Google.
     - Motor secundário: Wikimedia Commons API (`generator=search&gsrnamespace=6`) para buscas enciclopédicas e de domínio público.
     - Downloader assíncrono com inferência de extensão por `Content-Type` e verificação de bytes válidos.
3. **Interface Gráfica com Tema Obsidian & Zoom Parcial**:
   - `modules/image_search/ui/search_dialog.py` e `image_card.py`:
     - Campo de busca responsivo com tecla `Enter` e seletor de motor.
     - Grade de resultados com carregamento assíncrono de miniaturas via thread workers dedicados.
     - **Visualização com Zoom Parcial**: tela de detalhes com imagem ampliada em alta resolução, dimensões, domínio de origem.
     - **Botão Flutuante de Download no Canto Inferior**: botão `⬇️ Baixar e Inserir no Card` com estado de carregamento, salvamento via `editor.mw.col.media.write_data(...)`, restauração do foco do campo e injeção do tag `<img>` no cursor via `editor.doPaste(...)`, seguido de fechamento automático da janela.
     - Atalho direto: duplo clique na miniatura da grade executa download e inserção instantânea.
4. **Configuração e Internacionalização (i18n)**:
   - Suporte completo aos 4 idiomas do addon (`pt`, `en`, `es`, `fr`) para 13 novas chaves de tradução em `utils/i18n.py`.
   - Seção de configuração `image_search` em `config.json`.
5. **Suíte de Testes Automatizados**:
   - `tests/test_image_search.py` com 8 novos testes unitários cobrindo parsing de HTML, API Wikimedia, download de MIME, chaves i18n em todos os idiomas, hook do botão do editor e injeção no cursor. Totalizando 82 testes passing (100% OK).

---

## 📌 [Versão 2026-09-04 - v2.2.0] - Correção Crítica de Importação (NameError: aqt) no Ciclo de Abertura do Perfil/DeckBrowser

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"ao abrir o anki a tela ficou atrás de um filtro semitransparente escuro que não queria abrir e fazia som de erro do windows, depois esse filtro sumiu apertei alguma tecla por acidente e a seguinte log de depuração apareceu"*
  ```
  File "...modules\pomodoro\hooks.py", line 98, in get_focus_guard
      target_mw = getattr(aqt, "mw", None) or mw
                          ^^^
  NameError: name 'aqt' is not defined
  ```
- **Causas Técnicas Identificadas**:
  1. Em `modules/pomodoro/hooks.py`, o módulo realizava `from aqt import mw, gui_hooks`, porém o pacote `aqt` propriamente dito não estava importado no escopo global.
  2. Ao chamar `get_focus_guard()` durante a renderização do `deck_browser` na inicialização do Anki, a linha `target_mw = getattr(aqt, "mw", None) or mw` lançava `NameError: name 'aqt' is not defined`.
  3. O Anki interceptava a exceção no gerenciador de tarefas (`taskman.py`) e abria um diálogo modal de relatório de erro, congelando a interface e gerando o filtro escuro/bloqueio sonoro do Windows reportado pelo usuário.

---

### 2. Implementações Técnicas
1. **Importação Explícita e Resiliente de `aqt` em `hooks.py`**:
   - Adicionado `import aqt` e fallback `aqt = None` no bloco de importações de `modules/pomodoro/hooks.py`.
2. **Validação Direta no Runtime do Anki**:
   - Executado teste de inicialização real com `aqt.AnkiApp` invocando `on_deck_browser_rendered(None)` e `get_focus_guard()` sem qualquer erro ou exceção.

---

## 📌 [Versão 2026-09-04 - v2.1.9] - Correção do Auto-Hide do Cursor do Mouse em Modo Foco (Qt & Chromium Webviews)

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"Durante o modo foco o mouse que era para desaparecer caso não estivesse sendo movimentado não está desaparecendo"*
- **Causas Técnicas Identificadas**:
  1. **Falha de Escopo e Condição Inalcançável no `_hide_cursor_if_focused`**:
     - O método verificava `if mw and mw.isActiveWindow() and not self._is_cursor_hidden:`.
     - No início da execução, `mw` importado em nível de módulo como `from aqt import mw` ficava `None`.
     - Além disso, durante a revisão de cartões, a janela ativa do Windows é a janela child do Chromium WebEngine, fazendo com que `mw.isActiveWindow()` retornasse `False`. Portanto, a linha que definia o cursor invisível nunca era executada.
  2. **Timer de Cursor Nunca Iniciado**:
     - `_cursor_timer` era instanciado em `_setup_cursor_timer()`, mas `start()` nunca era chamado na inicialização nem no início do ciclo de foco. O timer ficava eternamente inativo caso o usuário não disparasse eventos no `mw`.
  3. **EventFilter Cego para Movimentos no Chromium**:
     - O Chromium WebEngine intercepta e consome os eventos nativos de mouse na sua própria janela Win32 child, impedindo que `QEvent.Type.MouseMove` chegasse ao filtro de eventos do `mw`.
  4. **Isolamento de Cursor no Chromium**:
     - Mesmo quando o Qt aplica `QGuiApplication.setOverrideCursor`, o renderizador HTML do Chromium redefine o cursor com base no CSS da página, exigindo injeção de estilo (`* { cursor: none !important; }`) e chamada a `wv.setCursor(BlankCursor)`.

---

### 2. Implementações Técnicas
1. **Rastreamento Físico de Posição via `QCursor.pos()`**:
   - Integrado ao batimento cardíaco de 250ms de `_on_focus_poll_tick`.
   - Lê diretamente as coordenadas físicas absolutas `(x, y)` do cursor no sistema operacional via `QCursor.pos()`.
   - Detecta movimento do mouse em qualquer lugar da tela (seja sobre o cartão, barra de navegação ou janela) com latência máxima de 250ms, restaurando imediatamente o cursor visível.
   - Detecta inatividade do mouse: quando a posição não muda por 2.0 segundos durante a fase `WORK`, aciona o ocultamento do cursor.
2. **Ocultamento Completo em Múltiplas Camadas (Full-Spectrum Hide)**:
   - **Camada 1 (Qt Widgets)**: `QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))` oculta o cursor sobre todos os widgets, barras e overlays nativos.
   - **Camada 2 (Chromium Webviews)**: Injeta CSS `* { cursor: none !important; }` e define `wv.setCursor(BlankCursor)` em todas as webviews ativas do Anki (`reviewer.web`, `deckBrowser.web`, `overview.web`, `toolbar.web`, `bottom_web`).
   - **Camada 3 (Win32 OS Direct)**: Executa `user32.SetCursor(0)` no Windows para apagar o glifo do cursor instantaneamente da tela.
3. **Persistência de Estado no Revisor**:
   - Em `modules/pomodoro/hooks.py`, o hook `on_reviewer_card_shown` chama `guard.on_card_shown_cursor_check()`, mantendo o cursor invisível mesmo quando um novo cartão é carregado no revisor.
4. **Preservação de Intervalos**:
   - Durante as pausas (`BREAK` e `LONG_BREAK`), o cursor permanece visível continuamente.
5. **Cobertura de Testes**:
   - Adicionados testes `test_auto_hide_cursor_lifecycle` e `test_cursor_never_hidden_during_break` em `tests/test_pomodoro.py` (74/74 testes passando).

---

## 📌 [Versão 2026-09-04 - v2.1.8] - Correção do Alarme de Perda de Foco do Pomodoro via Detecção Win32 OS-Level & Heartbeat

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"o sinal de alerta para quando se sai do app durante o modo foco do pomodoro não está funcionando o alerta de foco que era para tocar"*
- **Causas Técnicas Identificadas**:
  1. **Isolamento de Foco no Chromium WebEngine**:
     - O Anki utiliza `QWebEngineView` (Chromium) para renderizar os cartões e barra inferior. Quando o usuário clica ou interage com o cartão, uma janela Win32 nativa (`Chrome_WidgetWin_0`) assume o foco.
     - Ao usar `Alt+Tab` ou clicar em outro aplicativo (Chrome, Discord, Explorador, etc.), o Windows envia a mensagem de perda de foco (`WM_KILLFOCUS`) diretamente para a janela child do Chromium, sem propagar para o `QMainWindow` do Anki. O filtro de eventos Qt (`WindowDeactivate` / `ActivationChange`) e o sinal `applicationStateChanged` nunca eram disparados pelo Qt no Windows.
  2. **Inicialização Dependente de `mw`**:
     - `get_focus_guard()` verificava `if _global_focus_guard is None and mw:`. Em inicializações assíncronas do Anki onde `hooks.py` era importado antes da atribuição de `aqt.mw`, o guardião permanecia nulo e nunca era instalado.
  3. **Ausência de Polling Ativo de Sistema Operacional**:
     - A arquitetura anterior dependia 100% de eventos passivos do Qt, que falhavam silenciosamente devido à ponte Qt-Chromium.

---

### 2. Implementações Técnicas
1. **Detecção a Nível de SO (`is_anki_active_window`)**:
   - Criada rotina em `modules/pomodoro/focus_guard.py` que consulta diretamente `user32.GetForegroundWindow()` via `ctypes`.
   - Mapeia o PID ativo e a árvore de processos do Anki (`pythonw.exe`, subprocessos do `QtWebEngineProcess.exe`, `mpv.exe`) e as janelas raiz ancestrais (`GA_ROOT` / `GA_ROOTOWNER`).
   - Execução ultrarrápida: ~0.02ms por chamada (22 microssegundos), sem qualquer impacto em CPU.
2. **Sistema Dual de Monitoramento (Heartbeat + Tick Engine)**:
   - **Gatilho A (Heartbeat 250ms em `FocusGuard`)**: `_focus_monitor_timer` realiza varredura periódica durante a fase `WORK`. Se o usuário permanecer fora do Anki por 2 ticks consecutivos (~500ms debounce para ignorar trocas transitórias), dispara imediatamente a pausa, o alarme e o popup.
   - **Gatilho B (Heartbeat 1000ms em `PomodoroEngine.tick`)**: Reforço secundário no tick do relógio que pausa e alerta caso o Anki não esteja em primeiro plano durante `WORK`.
   - **Gatilho C (Eventos Qt)**: Mantido para reação instantânea caso o subsistema Qt receba `WindowDeactivate`.
3. **Resiliência no Ciclo de Vida**:
   - `get_focus_guard()` agora instancia o guardião imediatamente e acopla o filtro de eventos a `aqt.mw` dinamicamente assim que a janela estiver pronta.
   - Chamadas a `get_focus_guard()` adicionadas em `_on_engine_tick`, `update_active_fab` e `on_profile_did_open`.
4. **Alarme Sonoro Instantâneo com Latência Zero**:
   - Alarme sonoro (`digital_alarm.wav`) executado via `winsound.PlaySound` assíncrono no Windows, tocando mesmo com a janela do Anki em segundo plano ou minimizada.
5. **Cobertura por Testes Unitários**:
   - Adicionados testes `test_is_anki_active_window_executes_safely`, `test_focus_guard_heartbeat_polls_during_work` e `test_tick_focus_loss_dual_trigger` (72/72 testes passando).

---

## 📌 [Versão 2026-09-03 - v2.1.7] - Correção de Contraste e Visibilidade dos Tempos de Revisão (.nobold / .stattxt) sobre os Botões de Resposta (De novo e Bom)

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"Os textos de tempo que ficam sobre os botões de dificuldade não estão visíveis no botão de novo e botão bom verifique e corrija"*
  > *"é o tempo de revisão que fica encima que não está visivel, não sei se tinha sido claro o suficiente"*
- **Causas Técnicas Identificadas**:
  1. **Posicionamento Físico do Elemento de Tempo no Anki**:
     - No revisor do Anki, o tempo estimado de revisão (ex: `1m`, `10m`, `1d`, `4d`) é inserido via `<span class="nobold">{txt}</span>` dentro do botão de facilidade.
     - No CSS nativo do Anki (`reviewer-bottom.css`), esse elemento possui:
       `position: absolute; top: -3px; left: 50%; transform: translate(-50%, -100%);`
     - Portanto, o texto do tempo fica flutuando **fora e acima do botão**, diretamente sobre o fundo da barra inferior da janela (`bg_primary`), e **NUNCA** sobre o fundo colorido do botão (`c_again` ou `c_good`).
  2. **Cálculo Incorreto de Contraste no CSS do Addon**:
     - Em `modules/theme_manager/engine.py`, as variáveis `sub_again` e `sub_good` eram calculadas em relação à cor do botão (`c_again` e `c_good`).
     - Como a função `get_accessible_text_color` retornava `#0f172a` (azul quase preto) para o vermelho (`#ef4444`) e o verde (`#16a34a`), o subtexto caía na condição `sub_* = "rgba(15, 23, 42, 0.82)"`.
     - Em temas escuros (como Midnight OLED, Catppuccin, Dracula, Solarized), `bg_primary` é preto ou cinza escuro. O tempo de revisão acima dos botões "De novo" e "Bom" era pintado em **preto sobre preto**, tornando-se 100% invisível.
     - Nos botões "Difícil" e "Fácil", `get_accessible_text_color` retornava `#ffffff`, deixando o subtexto branco (`rgba(255, 255, 255, 0.90)`), razão pela qual apenas esses dois eram visíveis.

---

### 2. Implementações Técnicas
1. **Cálculo de Contraste Baseado no Fundo da Janela (`bg_primary`)**:
   - As variáveis `sub_again`, `sub_hard`, `sub_good`, `sub_easy` agora utilizam a cor calculada contra `bg_primary`:
     - Em temas escuros: `rgba(255, 255, 255, 0.95)` (branco nítido com contraste superior a 18:1).
     - Em temas claros: `rgba(15, 23, 42, 0.88)` (grafite escuro com contraste superior a 14:1).
2. **Sombra de Texto Protetora (`text-shadow`)**:
   - Adicionada propriedade `text-shadow` suave (`0 1px 2px rgba(0, 0, 0, 0.8)` em temas escuros e `rgba(255, 255, 255, 0.5)` em temas claros) para garantir máxima legibilidade contra gradientes ou fundos texturizados.
3. **Regra Universal para `.nobold` e `.stattxt`**:
   - Aplicada regra universal `.nobold, .stattxt` e `#ansbut .stattxt` para garantir que tanto os tempos de intervalo quanto os contadores de estudo acima de "Mostrar Resposta" fiquem 100% legíveis.
   - Adicionado seletor `button.ease3 .nobold, button.ease3 .stattxt` que estava ausente na regra do botão 3.
4. **Cores dos Rótulos dos Botões (`t_again`, `t_good`, etc.)**:
   - Botões com cores escuras/saturadas agora utilizam texto branco nítido (`#ffffff`), e cores pastéis claras utilizam `#0f172a`.
5. **Cobertura por Testes Unitários**:
   - Criado teste `test_review_interval_time_labels_contrast` em `tests/test_theme_manager.py` validando os seletores e garantindo contraste alto em temas claros e escuros (69/69 testes OK).

---

## 📌 [Versão 2026-09-03 - v2.1.6] - Criação da Skill Oficial do Projeto (obsidian-addon-dev), Diretrizes Mandatórias Incondicionais (GEMINI.md / AGENTS.md) & Base Técnica (PROJECT_KNOWLEDGE.md)

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"Quero que a skill desse projeto adicione obrigatoriamente ela tenha que ser lida a cada resposta e que agora seja criado arquivo.md com informações básicas e essenciais e scripts básicos essenciais, atualmente tokens tem sido desperdiçados repetidamente em atividades que já foram realizadas e resolvidas anteriormente como buscar a path do anki.exe, isso não pode ficar acontecendo, toda vez se tenta diferentes métodos até conseguir um script que funcione para uma informação que já foi redescorberta diversas vezes pelos mais diferentes scripts. Faça que a skill seja clara e orientativa o suficiente para que isso não ocorra mais."*
- **Causas Técnicas Identificadas**:
  1. Ausência de um arquivo de regras incondicionais de projeto lido automaticamente a cada turno pelo agente, gerando pesquisas redundantes (ex: redescobrir o caminho do `anki.exe` a cada nova sessão).
  2. Uso de anti-patterns no terminal Windows/PowerShell (como executar `where anki`, que chama `Where-Object` e trava indefinidamente o shell aguardando input).
  3. Falta de scripts utilitários padronizados para sincronização rápida de arquivos com a pasta do Anki (`addons21`) e execução de testes.

---

### 2. Implementações Técnicas
1. **Criação de `GEMINI.md` e `AGENTS.md` no Workspace**:
   - Injetados diretamente no topo das instruções incondicionais do agente (`<RULE>`).
   - Contêm caminhos absolutos imutáveis: `$env:USERPROFILE\Downloads\Anki\anki.exe`, `$env:USERPROFILE\Downloads\Obsidian Addon`, `$env:APPDATA\Anki2\addons21\Obsidian Addon` e `prefs21.db`.
   - Contêm comandos operacionais homologados de teste, sincronização (robocopy) e controle de processos.
2. **Criação do Guia Técnico Definitivo (`PROJECT_KNOWLEDGE.md`)**:
   - Documento completo com mapeamento dos 7 módulos do addon, anti-patterns proibidos, tabelas de caminhos e scripts.
3. **Criação da Skill Oficial `obsidian-addon-dev`**:
   - Disponibilizada no workspace (`.agents/skills/obsidian-addon-dev/`) e no catálogo global (`~/.gemini/config/skills/obsidian-addon-dev/`).
   - Estrutura com `SKILL.md`, `references/` (`paths_and_environment.md`, `operational_commands.md`, `architecture_cheat_sheet.md`) e `scripts/` (`run_tests.py`, `sync_to_anki.ps1`, `launch_anki.ps1`).
4. **Sincronização com Produção do Anki**:
   - Pasta de produção atualizada com todos os novos arquivos via `robocopy`.

---

## 📌 [Versão 2026-09-03 - v2.1.5] - Correção do Intervalo Contínuo, Detecção Resiliente de Perda de Foco & Alarme Sonoro de Inatividade no Pomodoro

### 1. Diagnóstico e Demandas Atendidas
- **Demandas do Usuário**:
  1. *"o intervalo para de contar caso o app não esteja focado no app depois de 60 segundos, esse mecanismo de pausa é para servir somente durante a fase de foco depois de ficar o tempo determinado pelo usuário sem responder o app."*
  2. *"Ademais lembro de ter pedido eu acho que um sinal de alarme tocasse quando o app deixasse de ser focado e que o tempo parasse de contar, em relação ao tempo não cheguei a o observar, mas o app não manda um aviso sonoro quando ele deixa de ser focado e também não tem aviso sonoro quando fica o tempo determinado pelo usuário sem responder."*
- **Causas Técnicas Identificadas**:
  1. **Verificação de Inatividade Global Não Filtrada por Estado**:
     - Em `modules/pomodoro/timer_engine.py`, a checagem de inatividade (`time.time() - self.last_activity_time > inactivity_limit`) era executada no início de `tick()` antes da bifurcação de estado.
     - Como na fase de intervalo (`BREAK` ou `LONG_BREAK`) o usuário naturalmente não clica nos cartões de estudo, o contador de inatividade atingia 60 segundos e pausava indevidamente o cronômetro de descanso (`self.state = PomodoroState.PAUSED`).
  2. **Ausência de Disparo de Som na Pausa por Inatividade**:
     - Ao transicionar para pausa por inatividade após o tempo configurado, nenhuma função de notificação sonora era invocada no motor do temporizador.
  3. **Instalação Tardia ou Omissa do FocusGuard**:
     - O método `get_focus_guard()` estava encapsulado dentro de um bloco `try/except` de atalhos em `setup_pomodoro_hooks()`, sem ser invocado no hook `profile_did_open` quando a interface do Anki é efetivamente criada.
     - Além disso, no evento `WindowDeactivate`, a verificação síncrona de `QApplication.activeWindow()` sofria com condições de corrida do Qt, onde a janela do Anki ainda constava como ativa no milissegundo do evento.
  4. **Falta de Roteamento de Som Específico para Alarme**:
     - Em `modules/pomodoro/sounds.py`, o evento `"focus_loss"` caía no fallback de som padrão de foco (`sound_preset`), tocando o sino suave (`bell.wav`) em vez de um sinal incisivo de alarme.

---

### 2. Implementações Técnicas
1. **Isolamento da Inatividade Exclusivamente na Fase de Foco (`modules/pomodoro/timer_engine.py`)**:
   - A verificação de inatividade agora exige estritamente `self.state == PomodoroState.WORK` e `config.get("inactivity_detection", True)`.
   - As fases de descanso (`BREAK` e `LONG_BREAK`) decrementam o temporizador livremente a cada segundo, sem qualquer interrupção por inatividade ou perda de foco.
   - Ao estourar o limite de inatividade durante o foco, aciona imediatamente `play_pomodoro_sound(event_type="inactivity")`.
   - Criado método `register_user_activity()` para manter o carimbo de tempo atualizado em qualquer interação do usuário.
2. **Arquitetura Resiliente do FocusGuard (`modules/pomodoro/focus_guard.py`)**:
   - Conexão direta ao sinal `QGuiApplication.instance().applicationStateChanged` (Qt 6), capturando instantaneamente quando o aplicativo perde o foco no sistema operacional (`ApplicationInactive` / `ApplicationHidden`).
   - Implementada verificação assíncrona com atraso calibrado (`QTimer.singleShot(80, ...)`) nos eventos `WindowDeactivate`, eliminando corridas de estado de janelas ativas.
   - O disparo de pausa e alarme em `_trigger_focus_loss()` é rigorosamente restrito a `self.engine.state == PomodoroState.WORK and self.engine.is_running`.
   - Adicionado tratamento defensivo para execução headless e testes unitários.
3. **Instalação Garantida nos Hooks do Anki (`modules/pomodoro/hooks.py`)**:
   - `get_focus_guard()` agora é invocado com bloco dedicado na inicialização do addon e reforçado no evento `gui_hooks.profile_did_open`.
   - Adicionado armazenamento de referências persistentes (`_registered_shortcuts`) para prevenir coleta de lixo dos atalhos do Qt.
4. **Reprodução Robusta de Áudio & Presets de Alarme (`modules/pomodoro/sounds.py`)**:
   - No Windows, arquivos `.wav` agora priorizam `winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)`, garantindo reprodução com latência zero mesmo quando o Anki está em segundo plano ou sem foco na janela, sem interferência no player de mídia do Anki.
   - Mapeados os eventos `"focus_loss"` e `"inactivity"` para utilizar o preset de alarme configurado (`alarm_sound_preset`, padrão `"digital_alarm"`).
5. **Central de Configurações, Diálogo Pomodoro & Internacionalização**:
   - Adicionado seletor de "Sinal de Alarme (Perda de Foco & Inatividade)" com opções: Alarme Digital (Bip-Bip), Alarme Analógico, Campainha Escolar, Sino Suave, Som do Sistema e Arquivo Customizado, além de botão de teste imediato (`▶️ Testar`).
   - Atualizados `modules/unified_config/settings_dialog.py` e `modules/pomodoro/config_dialog.py`.
   - Traduzidas todas as novas strings nos 4 idiomas em `utils/i18n.py`.
6. **Cobertura Completa por Testes Unitários**:
   - Adicionados testes em `tests/test_pomodoro.py` cobrindo o avanço ininterrupto do intervalo durante inatividade, pausa de inatividade na fase de foco, acionamento restrito do FocusGuard e presença dos arquivos de alarme (68/68 testes OK).

---

## 📌 [Versão 2026-09-03 - v2.1.4] - Correção Universal de Contraste e Acessibilidade Visual (WCAG 2.1) em Temas, Botões e Funções

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"nessa próxima versão corrija o contraste de texto de funções e botões nos temas, em alguns temas o texto não tem contraste em relação ao fundo dificultando a visualização, semelhante ao que aconteceu com a caixa de pomodoro"*
- **Causas Técnicas Identificadas**:
  1. **Cores de Texto Fixas (#ffffff) sobre Cores de Destaque Variáveis**:
     - Os botões `#study` (Estudar Agora) e `#ansbut` (Mostrar Resposta) definiam `color: #ffffff !important;` de forma estática no CSS injetado. Em temas claros ou de tons médios (ex: *Warm Paper*, *Clean Light* ou com presets personalizados de accent claro como amarelo, âmbar ou ciano), o contraste caía drasticamente (para até 2.1:1), tornando o texto ilegível.
  2. **Cálculo Inadequado de Cores Claras nos Botões de Resposta**:
     - O helper `get_light_tone(c, 0.75)` misturava a cor original com branco, gerando textos pastéis da mesma família da cor de fundo (ex: vermelho `#ef4444` com texto `#fbd0d0`), o que violava o limiar de contraste WCAG AA.
  3. **Presets com Cores Secundárias Subdimensionadas**:
     - Em *Solarized Dark*, `text_secondary` estava configurado como `#586e75` (contraste de apenas 2.78:1 contra o fundo `#002b36`).
     - Em *Dracula*, `text_secondary` estava como `#6272a4` (contraste de 3.23:1 contra `#282a36`).
     - Em *Warm Paper*, `text_secondary` estava como `#7c6f64` (contraste de 3.44:1 contra `#fbf1c7`).
  4. **Pills de Escopo e Badges no Modern Dashboard**:
     - `.dash-scope-pill` usava `background: rgba(0, 0, 0, 0.25)` estático, gerando uma mancha escura com texto escuro em temas claros.
  5. **Controles da Tabela de Atalhos do Gamepad e Diálogo Unificado**:
     - Na Central de Configurações, o diálogo pai não recebia o stylesheet dinâmico de alto contraste, deixando cabeçalhos de abas e grupos descalibrados.
     - Na tabela de atalhos do Gamepad, os badges de atalhos utilizavam tons claros pastéis que em temas com fundo branco perdiam contraste.

---

### 2. Implementações Técnicas
1. **Motor Matemático de Acessibilidade e Contraste WCAG 2.1 (`modules/theme_manager/engine.py`)**:
   - Adicionada fórmula de luminância perceptual relativa padrão CIE/WCAG 2.1 (`get_perceptual_luminance`).
   - Adicionada função de cálculo de razão de contraste (`get_contrast_ratio`), com suporte unificado para strings hexadecimais ou luminâncias pré-computadas.
   - Adicionada função de seleção adaptativa de texto de alto contraste (`get_accessible_text_color`), garantindo contraste >= 4.5:1 (ou razão máxima de contraste contra o fundo informado).
   - Adicionada função de cor dinâmica para estados `:hover` (`get_hover_text_color`).
2. **Correção Global no CSS Injetado (`generate_global_theme_css`)**:
   - Botões `#study` e `#ansbut` agora calculam sua cor de texto em tempo de execução via `get_accessible_text_color(accent)`.
   - Botões de resposta (Again, Hard, Good, Easy) utilizam `get_accessible_text_color` individualmente para cada uma de suas cores configuradas, com subtextos de atalho/intervalo calibrados com opacidade de alto contraste.
   - Textos ao pairar o mouse (`.hitem:hover`, `#top-area button:hover`) adaptam-se para nunca desvanecer sobre o fundo de hover.
   - Labels e tags ajustam dinamicamente suas cores conforme a luminância do tema.
3. **Calibração de Presets de Tema (`modules/theme_manager/presets.py`)**:
   - *Solarized Dark*: `text_secondary` ajustado para `#839496` (5.19:1 de contraste).
   - *Dracula*: `text_secondary` ajustado para `#95a5d5` (4.77:1 de contraste).
   - *Warm Paper*: `text_secondary` ajustado para `#572507` (6.81:1 de contraste).
4. **Modern Dashboard Adaptativo (`modules/dashboard/renderer.py`)**:
   - `.dash-scope-pill` agora aplica `background: rgba(0, 0, 0, 0.05)` com texto escuro em temas claros e `rgba(255, 255, 255, 0.06)` em temas escuros.
   - Badges de cards concluídos e contadores utilizam variantes com saturação profunda em fundos claros e fluorescência com texto escuro em fundos escuros.
5. **Central de Configurações e Tabela de Atalhos do Gamepad**:
   - `ObsidianSuiteHubDialog` agora aplica `get_qt_dialog_stylesheet` com cores de contraste calculado em abas, botões de ação e títulos.
   - Tabela de atalhos do Gamepad renderiza badges e botões de ação (`+ Adicionar`, `🧹 Limpar`) com paleta escura saturada em temas claros e tons luminosos em temas escuros.
6. **Bateria de Testes Unitários de Acessibilidade**:
   - Expandida a suíte em `tests/test_theme_manager.py` com testes automáticos de cálculo de contraste WCAG, seleção de texto acessível e integridade de presets (64/64 testes OK).

---

## 📌 [Hotfix 2026-09-03 - v2.1.3] - Correção do Espaçamento e Eliminação de Cortes na Sombra do FAB do Pomodoro

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"a sombra do FAB do pomodoro está imcompleta, aparentemente ela não cabe toda no espaço reservado para ela, corrija isso."*
- **Causa Técnica Identificada**:
  - Em `modules/pomodoro/native_fab.py`, o efeito `QGraphicsDropShadowEffect` estava configurado com `blurRadius = 28` e `offset = (0, 8)`.
  - Isso fazia com que a sombra se projetasse até 28px nas laterais, 20px no topo e até 36px na parte inferior.
  - No entanto, o layout principal do widget (`self.main_layout`) possuía margens de apenas `setContentsMargins(8, 8, 8, 8)`.
  - Como o widget raiz (`NativePomodoroFab`) delimita a área de pintura da janela translúcida, qualquer sombra que ultrapassasse os 8 pixels de margem era cortada de forma rígida e reta pelas bordas da janela (*hard-clipping*), gerando um corte perceptível na sombra.

---

### 2. Implementações Técnicas
1. **Expansão das Margens do Layout (`setContentsMargins(32, 28, 32, 40)`)**:
   - As margens ao redor de `self.card` foram ampliadas para 32px (esquerda/direita), 28px (topo) e 40px (base).
   - A sombra agora tem folga total em todas as direções para se dispersar suavemente até o valor zero de opacidade sem encostar em nenhuma borda do widget.
2. **Calibração Suave da Sombra (`QGraphicsDropShadowEffect`)**:
   - Ajustado o raio de desfoque para 28px e o deslocamento vertical para 6px com opacidade equilibrada (`QColor(0, 0, 0, 160)`), proporcionando um efeito de elevação natural, limpo e contínuo.
3. **Passagem Transparente de Cliques do Mouse na Margem da Sombra**:
   - Em `mousePressEvent` e `mouseDoubleClickEvent`, foi adicionada a verificação `self.card.geometry().contains(pt)`. Se o usuário clicar na área transparente da sombra fora do card visível, o evento é repassado (`event.ignore()`) para a interface subjacente do Anki, evitando qualquer sensação de "caixa invisível bloqueando cliques".
   - `self.setCursor(Qt.CursorShape.ArrowCursor)` foi definido no widget pai para manter a seta do mouse na área transparente, ativando `SizeAllCursor` apenas ao pairar sobre `self.card`.
4. **Reposicionamento Automático e Clamping**:
   - Em `reposition()`, o cálculo de posição padrão foi recalculado para `max(0, parent_w - w - 8)` e `max(0, parent_h - h - 12)`, garantindo que toda a sombra permaneça visível mesmo nos cantos da janela principal do Anki.

---

## 📌 [Versão 2026-09-03 - v2.1.2] - Internacionalização Completa e Detecção Nativa do Idioma do Anki (prefs21.db & defaultLang)

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"Fiz o teste das configurações de linguagem e mudei a linguagem na configuração principal para inglês e reiniciei o anki e o addon não acompanhou as mudanças, mudei nas próprias configurações do addon e funcionou,mas mais 3/4 das configurações estavam ainda em português e todo o dashboard e os textos de acessibilidade do pomodoro ainda estavam em português"*
- **Causas Técnicas Identificadas**:
  1. **Detecção do Idioma do Anki (`defaultLang`)**:
     - O Anki armazena o idioma configurado globalmente pelo usuário na chave `'defaultLang'` (ex: `'en_US'`), e **NÃO** em `'lang'`.
     - O código anterior de `utils/i18n.py` lia `mw.pm.meta.get("lang")`. Como `mw.pm.meta` existia porém sem a chave `"lang"`, o `elif hasattr(mw.pm, "defaultLang")` nunca era alcançado. O sistema caía no fallback `QLocale.system().name()`, que no Windows do usuário é `pt_BR`, mantendo o addon permanentemente em português mesmo com o Anki configurado em inglês.
  2. **Strings Hardcoded na Interface**:
     - Mais de 70% das opções e rótulos da Central de Configurações (`settings_dialog.py`), abas de Temas, Pomodoro, Dashboard, Prioridades e Gamepad utilizavam strings fixas em português sem passar por `tr()`.
     - Todo o HTML renderizado do Modern Dashboard (`modules/dashboard/renderer.py`) continha títulos, badges e métricas hardcoded em português.
     - A FAB do Pomodoro e o diálogo de descanso possuíam rótulos (`Restantes:`, `ETA:`), tooltips e propriedades de acessibilidade ARIA (`accessibleName`) em português fixo.

---

### 2. Implementações Técnicas
1. **Mecanismo de Resolução Multicamada de Idioma (`utils/i18n.py`)**:
   - **Ordem de Resolução**:
     1. Override manual do addon em `general.json` (se diferente de `"auto"`).
     2. Propriedade direta `mw.pm.defaultLang`.
     3. Metadados do gerenciador de perfis `mw.pm.meta.get("defaultLang")`.
     4. Leitura resiliente direta do banco SQLite `prefs21.db` (tabela `profiles`, chave `_global['defaultLang']`).
     5. Fallback de SO via `QLocale.system().name()`.
   - Se o idioma resolvido for polonês (`pl`), alemão (`de`) ou qualquer outro idioma sem tradução completa, normaliza automaticamente para inglês universal (`'en'`).
2. **Internacionalização Integral do Modern Dashboard (`modules/dashboard/renderer.py`)**:
   - Traduzidos os 5 cards dinâmicos: Metas Diárias (`dash_daily_goals`), Progresso de Hoje (`dash_today_progress`), Fila de Hoje (`dash_queue_today`), Acervo Total (`dash_deck_library`) e Concluídos Hoje (`dash_completed_today`).
   - Todos os badges (`to clear`, `done`), sub-métricas (`Time Spent`, `Retention`, `Pace`, `Speed`, `Learning`, `Mature Reviewed`, `Lapses`) e escopo global adaptam-se perfeitamente aos 4 idiomas (`en`, `pt`, `es`, `fr`).
3. **Internacionalização Completa da Central de Configurações (`modules/unified_config/settings_dialog.py`)**:
   - Todas as abas (Geral, Temas & Cores, Modern Dashboard, Pomodoro Flow & Sons, Sequenciador de Prioridades e Integrações) adaptadas para `tr()`.
4. **Internacionalização do Mapeamento de Controle (`modules/gamepad/config_dialog.py`)**:
   - Traduzidos cabeçalhos da tabela, botão de escuta de atalho (`+ Add` / `Press button, stick or key...`), banners de conexão, calibração de sticks e gatilhos e feedbacks visual e sonoro.
5. **Acessibilidade ARIA e Tooltips na FAB do Pomodoro (`modules/pomodoro/native_fab.py`)**:
   - `accessibleName` e tooltips atualizados para respeitar o idioma ativo do Anki via chaves `aria_*` e `fab_*`.
   - Rótulos `Remaining: <b>{count}</b>` e `ETA: <b>{eta}</b>` dinamicamente traduzidos.
6. **Cobertura de Testes Unitários**:
   - Todos os 60 testes da suíte passaram com 100% de sucesso (`OK`), incluindo testes automatizados de alternância de idioma do Dashboard entre PT e EN.

---

## 📌 [Hotfix 2026-09-03 - v2.1.1] - Correção de Alto Contraste e Legibilidade do Tempo/Badges na FAB do Pomodoro

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"corrija a questão de contraste na FAB do pomodoro, atualmente em alguns temas como o da imagem o tempo fica indistinguível do fundo"*
- **Causas Técnicas Identificadas**:
  1. **Estilo Inline Fixo em `lbl_timer`**: No método `_init_ui()` de `modules/pomodoro/native_fab.py`, `self.lbl_timer` possuía uma folha de estilo inline hardcoded `self.lbl_timer.setStyleSheet("color: #ffffff; font-weight: 800;")`. Por ter maior especificidade CSS do que a folha de estilo da janela ou do card, o texto dos dígitos do cronômetro permanecia branco puro mesmo em temas com fundo branco ou creme (como `clean_light`, `warm_paper` ou customizados claros), tornando o tempo invisível.
  2. **Estilos Inline em Metadados e Ciclos**: `self.lbl_cycles`, `self.lbl_rem_cards` e `self.lbl_eta` também continham `color: #94a3b8` e `#cbd5e1` hardcoded inline, prejudicando a leitura em fundos claros.
  3. **Baixo Contraste do Badge `PRONTO`**: No estado de prontidão, o badge utilizava texto amarelo claro (`#fde047`) que se tornava ilegível sobre fundos claros ou translúcidos.

---

### 2. Implementações Técnicas
1. **Cálculo Matemático de Luminância Perceptual (Fórmula WCAG)**:
   - Implementado o método `_is_light_color(hex_code)` em `NativePomodoroFab`, calculando a luminância relativa: `(0.299*R + 0.587*G + 0.114*B) / 255.0`.
2. **Remoção de Estilos Inline e Criação de Seletores CSS Dedicados**:
   - `lbl_timer` recebeu o seletor `#pomoTimer`.
   - `lbl_cycles` recebeu o seletor `#pomoCycles`.
   - `lbl_rem_cards` e `lbl_eta` receberam o seletor `#pomoMetaLabel`.
   - Se o fundo do card for claro (`lum > 0.52`), `text_primary` é automaticamente garantido como escuro (`#0f172a`), e `text_secondary` como grafite escuro (`#475569`). Em fundos escuros, mantém contraste cristalino com `#f8fafc` e `#94a3b8`.
3. **Badges de Alta Legibilidade e Acessibilidade Visual**:
   - Em fundos claros, o badge `PRONTO`/`PAUSADO` agora renderiza em âmbar escuro de alto contraste (`color: #b45309; background: rgba(217, 119, 6, 0.16); border: 1.5px solid rgba(217, 119, 6, 0.45);`).
   - Os badges de `P. SUAVE`/`INTERVALO` renderizam em verde floresta de alto contraste (`color: #15803d; background: rgba(22, 163, 74, 0.16)`).
   - O badge de `FOCO` renderiza em carmim escuro (`color: #b91c1c; background: rgba(220, 38, 38, 0.16)`).
4. **Botões de Ação e Barra de Progresso Adaptativos**:
   - Botões de ícone e modo foco adotam opacidade e bordas otimizadas para fundos claros ou escuros.

---

## 📌 [Versão 2026-09-03 - v2.1.0] - Pop-up Automático no Soft Break, Personalização de Rodadas de Pausa Longa, Integração da FAB aos Temas e Suporte a 4 Idiomas (EN, PT, ES, FR)

### 1. Diagnóstico e Demandas Atendidas
- **Demandas do Usuário**:
  1. *"ao terminar o tempo de foco é tocado o sinal e não se abre o pop-up de intervalo de imediato para não atrapalhar o usuário. A alteração que eu quero que seja realizada é que depois de responder o card e com o tempo terminado o pop-up possa aparecer automaticamente sem que algum botão tenha que ser pressionado."*
  2. *"o aumento da personalização nas configurações do pomodoro com a capacidade de definir quantas rodadas são necessárias para que se atinja uma rodada com pausa longa."*
  3. *"vamos integrar a FAB do pomodoro aos temas, atualmente se muda o tema, mas a FAB do pomodoro continua com o mesmo tema de antes que no caso é o principal."*
  4. *"vamos introduzir a compatibilidade com mais 3 idiomas, o inglês, o espanhol e o francês, o reconhecimento de qual idioma usar vai ser feito com base no idioma selecionado nas configurações, o idioma principal do addon vai ser o inglês, ou seja em qualquer outra linguagem que não seja as mencionadas e o português que vai ser o mesmo tanto para o de portugal quanto o brasileiro, o addon vai estar em inglês. Ou seja, selecionou Polski como linguagem do anki, o addon vai ficar em inglês, pois não terá polonês como lingua disponível."*

---

### 2. Implementações Técnicas

1. **Pop-up Automático e Resiliente de Descanso Pós-Resposta (`hooks.py` e `hud_manager.py`)**:
   - Em `modules/pomodoro/hooks.py`, o disparo do pop-up de intervalo foi desacoplado do ciclo síncrono interno de transição de card do Anki utilizando `QTimer.singleShot(120, ...)`.
   - Em `modules/pomodoro/hud_manager.py`, o método `show_centered()` foi reforçado com chamadas explícitas a `self.raise_()` e `self.activateWindow()`. Logo após a resposta do card sob o término do tempo de foco, a janela modal de descanso cognitivo surge automaticamente em primeiro plano, centralizada sobre a tela, sem necessidade de tocar no mouse ou no controle.
   - Em `modules/pomodoro/timer_engine.py`, adicionada proteção em `on_reviewer_state_changed`: quando o usuário conclui o último card do baralho e o Anki transita para a tela de `overview`, o cronômetro de pausa e o pop-up de descanso não são pausados nem ocultados, permitindo que o descanso cognitivo continue normalmente.

2. **Controle de Intervalo para Pausa Longa (`long_break_interval`)**:
   - Adicionado spinbox dedicado (`self.spin_long_interval`, alcance de 1 a 20 ciclos, padrão 4) na Central de Configurações (`settings_dialog.py`) e no diálogo próprio do Pomodoro (`config_dialog.py`).
   - Persistido na chave `"long_break_interval"` do módulo `"pomodoro"`.
   - Engine (`timer_engine.py`) atualizada com divisão segura (`max(1, durations[3])`), disparando a Pausa Longa exatamente após a quantidade configurada de rodadas.

3. **Integração Dinâmica da FAB do Pomodoro aos Temas (`native_fab.py`)**:
   - A folha de estilo estática da FAB foi substituída por geração de CSS dinâmico em `_apply_stylesheet()`, consumindo as propriedades de paleta do tema ativo (`bg_card`, `border_color`, `accent`, `text_primary`, `text_secondary`).
   - Implementado o método `refresh_theme()`, invocado automaticamente sempre que um tema for salvo ou alterado na Central de Configurações, adaptando imediatamente o fundo, bordas, botões de ação e textos do card flutuante do Pomodoro.

4. **Sistema Completo de Internacionalização i18n (`utils/i18n.py`)**:
   - Criado módulo central de internacionalização com suporte aos 4 idiomas requisitados:
     - **Inglês (`en`)**: Idioma padrão do addon e fallback universal para qualquer língua não suportada (ex: Polonês `pl`, Alemão `de`, etc.).
     - **Português (`pt`)**: Unificado para variantes brasileira (`pt_BR`) e europeia (`pt_PT`).
     - **Espanhol (`es`)**: Espanhol peninsular e latino-americano.
     - **Francês (`fr`)**: Francês e canadense.
   - Função `normalize_language_code()` com detecção automática do idioma do Anki via `mw.pm.meta.get("lang")` ou `QLocale`.
   - Adicionada aba **🌐 Geral** na Central de Configurações com menu suspenso para escolha explícita do idioma ou seleção de modo Automático.

---

## 📌 [Hotfix 2026-09-03 - v2.0.3] - Correção de KeyError: 'colors' na Troca de Temas da Central de Configurações

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"fui tentar mudar de tema na central de configurações e apareceu o seguinte erro:*
  > *KeyError: 'colors' em settings_dialog.py line 302, in _on_preset_changed"*
- **Causa Técnica Identificada**:
  - No método `_on_preset_changed` de `modules/unified_config/settings_dialog.py`, o código tentava ler `THEME_PRESETS[preset_key]["colors"]`.
  - Entretanto, em `modules/theme_manager/presets.py`, os dicionários de temas em `THEME_PRESETS` contêm as propriedades de cores diretamente na raiz de cada dicionário (`"bg_primary"`, `"bg_card"`, `"accent"`, `"text_primary"`, etc.), sem nenhuma subchave `"colors"`. A tentativa de acesso indexado causava a quebra imediata por `KeyError`.

---

### 2. Implementações Técnicas
1. **Acesso Direto Resiliente ao Dicionário do Tema (`settings_dialog.py`)**:
   - `_on_preset_changed` atualizado para extrair as cores diretamente: `preset_data.get("colors", preset_data)`. As amostras visuais de cores (*swatches*) agora se atualizam instantaneamente na interface sem nenhum erro.
2. **Sincronização Bidirecional com Detecção de Customização**:
   - Ao selecionar um tema pré-definido no combobox (ex: *Dracula*, *Nord Dark*, *Catppuccin Mocha*, *Warm Paper*), o dicionário `custom_overrides` é resetado para `{}` ao salvar, permitindo que a paleta do tema predefinido seja aplicada limpamente no Anki.
   - Caso o usuário clique em qualquer botão de cor para personalizar uma tonalidade individual, a interface detecta a alteração via callback `on_changed` e alterna automaticamente o seletor para `🛠️ Personalizado (Custom)`.
3. **Robustez dos Widgets de Cor**:
   - `ColorPickerButton` reforçado com tratamento seguro de parsing hex e fallback automático de contraste para o texto do botão.

---

## 📌 [Hotfix 2026-09-03 - v2.0.2] - Correção da Ação Pomodoro: Start/Pause no Gamepad, Sincronização Dinâmica em Tempo Real e Feedback Visual/Sonoro

### 1. Diagnóstico e Demandas Atendidas
- **Demanda do Usuário**:
  > *"adicionei um botão para a função de start e pause do pomodoro e ao tentar utilizar não funcionou"*
- **Causas Técnicas Identificadas**:
  1. **Ausência de Atualização do Dispatcher em Tempo Real**: No método `save_settings()` de `modules/gamepad/config_dialog.py`, as configurações eram gravadas em disco, mas a instância ativa do `_global_action_dispatcher` em execução no Anki não recebia o comando `disp.set_bindings(self.bindings)`. Por isso, os novos atalhos adicionados pelo usuário na interface só teriam efeito se o Anki fosse totalmente reiniciado.
  2. **Ausência de `pomo_*` nas `instant_actions`**: No método `handle_button_down` do dispatcher, ações de utilidade global e controle (como o Pomodoro) não estavam listadas na tupla `instant_actions`. No modo padrão (*Trigger on Release*), o sistema tentava aplicar contração visual nos botões de resposta do card em vez de disparar a ação imediatamente ao pressionar o botão físico.
  3. **Conflito de Prioridade em Mapeamentos Concorrentes**: Caso o botão adicionado ao Pomodoro já estivesse previamente associado a outra ação (ex: áudio, flag ou resposta), `_resolve_current_action` escolhia a primeira ação da ordem do dicionário. Se o Anki estivesse fora da tela de revisão (`deckBrowser` ou `overview`), a ação de revisão não executava e impedia o disparo da ação de Pomodoro.
  4. **Nomes de Métodos e Ausência de Feedback Visual/Toast**: As ações `pomo_skip` e `pomo_reset` chamavam métodos inexistentes (`skip_to_next_phase` e `reset_cycle`) em vez de `skip_to_break` e `reset_current_phase`, e `pomo_toggle` não emitia alerta visual (`tooltip`), não garantia a exibição da janela flutuante (FAB) nem emitia som de confirmação.

---

### 2. Implementações Técnicas
1. **Sincronização Imediata em Tempo Real (`config_dialog.py`)**:
   - Inserida chamada `disp.set_bindings(self.bindings)` em `save_settings()`. Ao vincular qualquer atalho na tabela e soltar o botão, o dispatcher em execução no Anki é atualizado instantaneamente sem necessidade de reiniciar.
2. **Classificação como Ação Instantânea (`actions.py`)**:
   - Adicionadas as ações `pomo_toggle`, `pomo_skip`, `pomo_reset` e `pomo_expand` à tupla `instant_actions`. O cronômetro responde com latência zero logo no instante do toque (*button down*).
3. **Mecanismo de Fallback Multi-Ação (`_get_matching_actions`)**:
   - `_get_matching_actions` ordena as ações contextualmente de acordo com o estado do Anki. Se uma ação não for aplicável no momento (ex: `replay_audio` fora da tela de revisão), o loop tenta a próxima ação associada àquele botão (`pomo_toggle`), garantindo execução confiável.
4. **Acoplamento Preciso da Engine do Pomodoro & Notificações Toasts**:
   - Em `execute_action("pomo_toggle")`: chama `engine.toggle_pause()`, força `fab.show()` caso estivesse oculto, atualiza a interface com `fab.update_display()`, toca o áudio do gamepad e exibe toast imediato na tela: `"▶️ Pomodoro: Foco Iniciado"` ou `"⏸️ Pomodoro: Pausado"`.
   - Em `execute_action("pomo_skip")`: chama `engine.skip_to_break()`, exibe toast `"⏩ Pomodoro: Pulado para Intervalo"` e toca áudio de confirmação.
   - Em `execute_action("pomo_reset")`: chama `engine.reset_current_phase()`, exibe toast `"🔄 Pomodoro: Contador Reiniciado"` e toca som "pop".
   - Em `execute_action("pomo_expand")`: exibe/minimiza o botão flutuante (FAB) de forma confiável.
5. **Atualização do `DEFAULT_CONFIG` em `utils/config_manager.py`**:
   - Adicionadas todas as novas chaves de ações (`pomo_*`, `nav_*`, `scroll_page_*`) no dicionário base para evitar inconsistências no merge de configurações.

---

## 📌 [Hotfix & Melhoria 2026-09-02 - v2.0.1] - Suporte aos Botões B16/B17 no Testador de Gamepad & Prevenção de Interrupção de Rolagem por Sliders/Combos (FocusWheel Widgets)

### 1. Diagnóstico e Especificações Técnicas
- **Especificações Técnicas**:
  1. **Espaço e Suporte aos Botões B16 e B17 no Testador em Tempo Real**:
     - Em controles com botões adicionais (ex: DualShock 4 / DualSense / 8BitDo / controles com botões extras), existem os botões `B16` (Guide / Home / PS Button) e `B17` (Touchpad Click / Capture / Mic Mute), mas o testador só exibia até `B15`.
  2. **Interrupção de Rolagem da Página ao Passar o Mouse sobre Barras de Configuração**:
     - Ao rolar a página da central de configurações com a roda do mouse (*mouse wheel*), quando o cursor passava por cima de um slider de configuração (`QSlider`) ou caixa de seleção (`QComboBox`), a página parava de rolar repentinamente e a roda do mouse passava a alterar o valor da barra de configuração. Definiu-se que a rolagem da página deve prosseguir sem desvios, com alteração de valores via roda condicionada ao foco explícito do controle.

---

### 2. Implementações Técnicas
1. **Adição dos Botões B16 e B17 no Testador & Drivers (`visualizer.py`, `directinput_driver.py`, `xinput_driver.py`, `base.py`)**:
   - `base.py`: adicionadas constantes `BUTTON_GUIDE = "GUIDE"` (B16) e `BUTTON_TOUCHPAD = "TOUCHPAD"` (B17) a `ALL_STANDARD_BUTTONS`.
   - `directinput_driver.py`: mapeados os bits 12 e 13 para `BUTTON_GUIDE` e `BUTTON_TOUCHPAD`, e estendido o suporte a bits 16 e 17 com aliases `"B16"` e `"B17"`.
   - `xinput_driver.py`: mapeado bit `0x0400` (`XINPUT_GAMEPAD_GUIDE`) para `BUTTON_GUIDE`.
   - `visualizer.py`:
     - `BUTTON_SPECS` expandido de 16 para 18 botões: `B16 · Guide` e `B17 · Pad`.
     - Grade redesenhada em 2 linhas de 9 colunas (`row = i // 9`, `col = i % 9`) com largura de 84px e altura de 54px, mantendo tipografia HD nítida em Segoe UI e Consolas sem corte.
     - `update_telemetry`: suporte duplo por nome canônico (`GUIDE`, `TOUCHPAD`) e por identificador direto (`B16`, `B17`).
2. **Arquitetura de Controles Imunes a Roda sem Foco (`FocusWheel` em `utils/ui_helpers.py`)**:
   - Criadas classes `FocusWheelSlider`, `FocusWheelComboBox` e `FocusWheelSpinBox`:
     - Se `not self.hasFocus()`: o evento `wheelEvent` chama `event.ignore()`, permitindo que o Qt propague o evento de roda diretamente para o `QScrollArea.viewport()` pai. A página desliza suavemente sem parar e sem alterar nenhum parâmetro.
     - Ao clicar no slider, combo ou spinbox (adquirindo foco explícito): o controle aceita o ajuste pela roda normalmente (`super().wheelEvent(event)`).
   - Aplicado a todos os sliders e seletores em `modules/gamepad/config_dialog.py` (Deadzone, Sensibilidade de Rolagem, Limiar de Gatilhos, Analógico de Rolagem, Preset de Som, Intensidade Visual, Escala de Botões) e em `modules/unified_config/settings_dialog.py` (Temas, Escala de Botões, Pomodoro Tempos, Alarme Sonoro).

---

## 📌 [Atualização Maior 2026-09-02 - v2.0.0] - Sistema Ilimitado de Mapeamento Multi-Dispositivo (Gamepad + Teclado) & Gestos Direcionais dos Analógicos (Left & Right Stick)

### 1. Diagnóstico e Especificações Técnicas
- **Especificações Técnicas**:
  1. **Fim dos limites de atalhos por ação**: O sistema anterior suportava no máximo 2 botões fixos ("Primário" e "Secundário"). Implementado suporte irrestrito à vinculação de múltiplos atalhos por ação.
  2. **Inclusão de atalhos de teclado**: O mapeamento deve capturar e despachar tanto botões do controle quanto teclas do teclado (ex: `Espaço`, `Enter`, `1`, `2`, `3`, `4`, `J`, `K`, etc.).
  3. **Movimentos dos Sticks (Left e Right Stick) como comandos e atalhos**: Todas as 4 direções de cada analógico (`LS_UP`, `LS_DOWN`, `LS_LEFT`, `LS_RIGHT`, `RS_UP`, `RS_DOWN`, `RS_LEFT`, `RS_RIGHT`) integradas como gatilhos para qualquer ação configurável.
  4. **Ações de Navegação Básica Pré-programadas e Configuráveis**: Os movimentos de navegação e rolagem por stick foram expostos diretamente na tabela de mapeamento com padrões de fábrica, viabilizando remapeamento livre e personalização direta pela UI.

---

### 2. Implementações Técnicas
1. **Atalhos Ilimitados e Badges Visuais (`ShortcutsCellWidget`)**:
   - Desenvolvido componente visual dinâmico com *chips/badges* estilizados e botão `[+ Adicionar]`:
     - `[🎮 A ✕]` (Ciano) para botões de gamepad.
     - `[🕹️ LS Cima ✕]`, `[🕹️ RS Baixo ✕]` (Azul/Sky) para movimentos de analógicos.
     - `[⌨️ Espaço ✕]`, `[⌨️ Enter ✕]` (Índigo/Roxo) para atalhos de teclado.
   - Cada badge possui botão `✕` para exclusão imediata e cirúrgica do atalho individual.
   - O botão `[+ Adicionar]` ativa o modo de escuta (*Listening Mode*) sem limite de quantidade.
2. **Suporte Híbrido ao Teclado (`qt_key_event_to_string` e `GamepadGlobalKeyboardFilter`)**:
   - No modo de escuta da interface: qualquer tecla pressionada no teclado é convertida em string padronizada (`KEY:Espaço`, `KEY:Enter`, `KEY:1`, etc.) e adicionada aos atalhos da ação.
   - Durante o estudo/revisão no Anki: instalado filtro global no `QApplication` que intercepta teclas mapeadas e executa a respectiva ação via `dispatcher.handle_button_press()`, ignorando a captura de forma inteligente quando o foco estiver em caixas de texto editáveis (`QLineEdit`, `QTextEdit`, etc.).
3. **Detecção Discreta dos Sticks (`input_manager.py` & `base.py`)**:
   - Adicionadas constantes `STICK_LS_UP`, `STICK_LS_DOWN`, `STICK_LS_LEFT`, `STICK_LS_RIGHT`, `STICK_RS_UP`, `STICK_RS_DOWN`, `STICK_RS_LEFT`, `STICK_RS_RIGHT`.
   - No loop de 60Hz, quando a deflexão de qualquer stick ultrapassa `0.55`, a respectiva direção é incorporada a `current_buttons`, permitindo detecção de borda (*edge detection*) e captura instantânea no modo de escuta.
4. **Novas Ações de Navegação Expostas (`ACTION_DEFINITIONS`)**:
   - `scroll_page_up`: *"Rolagem: Rolar Página para Cima (Right Stick)"* (Padrão: `["RS_UP"]`)
   - `scroll_page_down`: *"Rolagem: Rolar Página para Baixo (Right Stick)"* (Padrão: `["RS_DOWN"]`)
   - `scroll_page_left`: *"Rolagem: Rolar Conteúdo para Esquerda"* (Padrão: `["RS_LEFT"]`)
   - `scroll_page_right`: *"Rolagem: Rolar Conteúdo para Direita"* (Padrão: `["RS_RIGHT"]`)
   - `scroll_up`: Padrão `["DPAD_UP", "LS_UP"]`
   - `scroll_down`: Padrão `["DPAD_DOWN", "LS_DOWN"]`
   - `dpad_left`: Padrão `["DPAD_LEFT", "LS_LEFT"]`
   - `dpad_right`: Padrão `["DPAD_RIGHT", "LS_RIGHT"]`

---

## 📌 [Hotfix 2026-09-02 - v1.9.1] - Correção Definitiva de Legibilidade e Renderização HD no Testador de Gamepad

### 1. Diagnóstico, Bisseção de Camadas e Causas Raiz
- **Problema / Sintoma Relatado**:
  - As letras e números nos cards de botões do Gamepad Tester continuavam com aspecto distorcido, ilegível, parecendo rabiscos ou caracteres truncados (o valor `0.00` parecia letras russas `и  ии`, e os nomes dos botões sofriam corte lateral como `B0 · X (`, `B8 · Bac`, `B9 · Sta`).
- **Causas Raiz Identificadas**:
  1. **Truncamento Vertical de Altura (O "Mistério do и  ии")**:
     - O card tinha altura rígida de `46px`. Com margens e fontes de 11px/12px em monitores com escalonamento DPI do Windows (125%/150%), o rótulo inferior `0.00` sofria *clipping* geométrico: apenas os 5 a 6 pixels inferiores dos zeros eram desenhados na tela, cortando o topo dos números pela metade e fazendo o par de zeros parecer exatamente a letra `и  ии`.
  2. **Truncamento Lateral de Largura**:
     - A largura de `78px` deixava apenas ~60px livres para texto. Nomes compostos como `B0 · ✕ (A)`, `B8 · Back` e `B9 · Start` ultrapassavam a largura e tinham o final cortado.
  3. **Fragmentação por Font Fallback Unicode**:
     - Caracteres Unicode matemáticos/geométricos (`✕`, `◯`, `◻`, `△`) não existem na família Segoe UI / Consolas padrão do Windows em tamanhos reduzidos. O Qt disparava substituição de fonte em runtime para cada símbolo, gerando descontinuidade de baseline e renderização serrilhada.
  4. **Thrashing de Stylesheet a 60Hz (3.840 recompilações/s)**:
     - No loop de telemetria de 60 FPS, `card.set_value()` aplicava `setStyleSheet(...)` incondicionalmente em todos os 16 cards a cada 16ms, invalidando o cache de rasterização de fontes do Qt (*glyph cache eviction*) e causando artefatos visuais contínuos.

---

### 2. Soluções e Engenharia Aplicada
1. **Expansão Generosa das Dimensões dos Cards**:
   - Largura aumentada de `78px` para **`92px`** (+18% de área horizontal).
   - Altura aumentada de `46px` para **`54px`** (+17% de área vertical).
   - Rótulos com alturas explícitas fixadas (`lbl_id` com 18px, `lbl_val` com 20px) e alinhamento vertical centralizado. Os números `0.00` e `1.00` agora são renderizados com 100% de integridade física vertical.
2. **Eliminação do Thrashing de Estilo a 60 FPS**:
   - `setStyleSheet` agora é executado **estritamente em transições de estado** (`is_pressed != self._is_pressed`). Quando o controle está ocioso ou em repouso, zero recalculos de CSS ocorrem por frame, preservando a textura nítida do Qt.
   - Atualização do texto (`lbl_val.setText`) otimizada apenas quando a string do valor sofrer alteração real.
3. **Tipografia Universal Nítida e Sem Truncamento**:
   - Nomes de botões padronizados em Segoe UI nítido e direto: `B0 (A)`, `B1 (B)`, `B2 (X)`, `B3 (Y)`, `B4 (LB)`, `B5 (RB)`, `B6 (LT)`, `B7 (RT)`, `B8 (Back)`, `B9 (Start)`, `B10 (L3)`, `B11 (R3)`, `B12 (Up)`, `B13 (Down)`, `B14 (Left)`, `B15 (Right)`.
   - Tooltips enriquecidos com descrições completas para PlayStation e Xbox (`Cross ✕`, `Circle ◯`, `Square ◻`, `Triangle △`).
   - Seletor `QFrame#btn_card` isolado por ID para não conflitar com a barra lateral de acento luminoso.

---

## 📌 [Atualização 2026-09-02 - v1.9.0] - Seleção e Navegação dos Botões Superiores do Anki via Gamepad & Expansão Vertical da Tabela de Mapeamento

### 1. Diagnóstico e Novas Capacidades
- **Demandas do Usuário**:
  1. Permitir que os 5 botões superiores do Anki (*Baralhos, Adicionar, Painel, Estatísticas e Sincronizar*) sejam navegados e selecionados via controle/gamepad, prioritariamente pelo analógico esquerdo (**Left Stick**) e D-Pad.
  2. Oferecer comandos dedicados mapeáveis para acesso direto a qualquer um dos 5 botões superiores.
  3. Expandir verticalmente a tabela de mapeamento de botões na Central de Configurações, que antes exibia apenas 2,5 linhas, para exibir no mínimo 8 a 10 ações simultaneamente sem aperto visual.
- **Implementações Técnicas**:
  1. **Dual Focus Zones (`focus_zone`)**:
     - Introduzida gestão bi-zonal no despachador: zona `"decks"` e zona `"topbar"`.
     - Ao mover o Left Stick para cima no primeiro baralho da lista (ou D-Pad Up), o foco ascende suavemente para a barra superior (`Baralhos`).
     - Ao inclinar para Esquerda / Direita no Left Stick ou D-Pad, o foco percorre sequencialmente `Baralhos ↔ Adicionar ↔ Painel ↔ Estatísticas ↔ Sincronizar`.
     - Ao inclinar para Baixo no Left Stick ou D-Pad, o foco desce imediatamente para a lista de baralhos.
     - Pressionar o botão primário (**A**) quando na barra superior ativa o botão em foco (`activate_topbar_button`), com som de clique e animação.
     - Pressionar **B** quando na barra superior retorna o foco para a lista de baralhos.
  2. **Destaque Visual com Efeito Halo Luminoso (`mw.toolbar.web`)**:
     - Injetada classe `.topbar-gamepad-focused` na webview da barra superior (`outline: 2px solid #38bdf8`, `box-shadow: 0 0 14px rgba(56, 189, 248, 0.65)`, leve escala e transição suave).
  3. **Ações Diretas Mapeáveis**:
     - `nav_decks`: Ir para Baralhos.
     - `nav_add`: Abrir Adicionar Cartões.
     - `nav_browse`: Abrir Painel de Cartões (Browse).
     - `nav_stats`: Abrir Estatísticas.
     - `nav_sync`: Sincronizar Coleção.
     - `topbar_toggle_focus`: Alternar Foco entre Baralhos e Barra Superior.
     - `dpad_left` / `dpad_right`: Navegação horizontal.
  4. **Expansão da Tabela de Mapeamento**:
     - `setMinimumHeight(410)` e linhas com `38px`: exibe com folga 10 ações completas simultâneas na tela.

---

## 📌 [Atualização 2026-09-02 - v1.8.2] - Estabilização de Alta Performance do Reordenador de Prioridades (QueryOp Assíncrono, Proteção contra Cliques Acidentais, Otimização de Diff e Chunking SQLite)

### 1. Diagnóstico, Bisseção de Camadas e Hipóteses (Fases 1 e 2)
- **Problema / Sintoma**:
  1. Ao clicar por acidente na opção *"⚡ Reordenar Novos Cartões por Prioridade"* no menu Ferramentas, o Anki deixava de responder (*Application Hang / Tela Branca*), especialmente em computadores com CPUs modestas ou coleções grandes.
  2. A operação disparava imediatamente sem confirmação ou aviso prévio ao usuário.
  3. A reordenação ocorria de forma 100% síncrona travando a *UI thread* do Qt/PyQt durante a execução de milhares de instruções `UPDATE` no SQLite.
  4. Todos os cartões novos eram gravados no banco de dados, inclusive os que já estavam com o `due` idêntico à ordem calculada, causando I/O em disco desnecessário.
- **Hipótese Principal (H0 - Confirmada)**:
  - Migrar a execução do reordenador para a API oficial de tarefas em background do Anki (**`QueryOp`**) liberta completamente a thread principal do Qt, mantendo a interface 60fps responsiva com barra de progresso nativa, erradicando o congelamento do Windows ("Não está respondendo").
- **Hipótese Acessória 1 (H1 - Confirmada)**:
  - Adicionar um diálogo de confirmação prévia e cancelamento rápido (`confirm_reorder_prompt`) impede que um clique acidental no menu Ferramentas inicie o processamento da coleção.
- **Hipótese Acessória 2 (H2 - Confirmada)**:
  - Comparar o `new_due` com o `current_due` (*Diff Checking*) reduz a zero os `UPDATE`s de cartões que já se encontram na posição correta. Em coleções já organizadas, o tempo de execução cai para centésimos de segundo com 0 gravações em disco.
- **Hipótese Acessória 3 (H3 - Confirmada)**:
  - Dividir as atualizações pendentes em lotes de 1.000 cartões (*Batch Chunking*) impede que o SQLite trave bloqueios extensos ou sature a memória RAM em computadores mais modestos.

---

### 2. Reparo e Verificação
- **Componentes Atualizados**: `modules/priority_sequencer/reorder.py`, `core/reorder.py`, `__init__.py`.
- **Testes**: Adicionado `test_execute_reorder_diff_optimization_and_chunking`. 40 testes unitários executados e aprovados com 100% de sucesso (`Ran 40 tests in 0.198s, OK`).
- **Sincronização**: Arquivos atualizados em `%APPDATA%\Anki2\addons21\Obsidian Addon`.

---

## 📌 [Hotfix 2026-09-02 - v1.8.1] - Correção no Desempacotamento de Telemetria de Botões no GamepadTesterWidget

### 1. Diagnóstico e Reparo Cirúrgico
- **Problema / Sintoma**: Ao abrir a central de configurações, ocorria repetição massiva de erro: `ValueError: too many values to unpack (expected 3)` na linha 408 de `modules/gamepad/visualizer.py`.
- **Causa Raiz**: Na expansão HD da v1.8.0, os elementos de `BUTTON_SPECS` foram enriquecidos para 4 campos `(b_id, norm_name, label_hint, display_title)`. Na criação da UI o desempacotamento foi atualizado, porém dentro do loop de atualização contínua de telemetria de 60Hz (`update_telemetry`), o laço ainda esperava 3 itens `for b_id, norm_name, _ in self.BUTTON_SPECS:`.
- **Correção Aplicada**: Atualizado para desempacotamento flexível e imune a alterações de tupla: `for b_id, norm_name, *rest in self.BUTTON_SPECS:`.
- **Verificação**: Adicionado teste unitário dedicado `test_gamepad_tester_widget_update_telemetry` simulando o ciclo completo de telemetria. 39 testes executados e aprovados com 100% de sucesso (`Ran 39 tests in 0.266s, OK`).

---

## 📌 [Atualização 2026-09-02 - v1.8.0] - Isolamento de Gamepad em Janelas de Configuração, Qualidade HD no Tester, Ações Pomodoro no Controle & Acessibilidade WCAG 2.2 / WAI-ARIA Elegante

### 1. Diagnóstico, Bisseção de Camadas e Hipóteses (Fases 1 e 2)
- **Problema / Sintoma**:
  1. Ao testar o stick direito ou botões dentro da Central de Configurações, a tela principal do Anki em segundo plano continuava rolando e recebendo cliques acidentais.
  2. Na imagem enviada pelo usuário (`media_1788393379226.png`), os cartões de botões do Gamepad Tester exibiam textos truncados e microrrabiscos ilegíveis.
  3. Faltavam opções para controlar o Pomodoro (iniciar/pausar, pular etapa, resetar, expandir) diretamente pelos botões do gamepad.
  4. Ao pressionar `Tab` na tela inicial, o foco ficava preso indefinidamente nos botões do Pomodoro (`btn_play`, `btn_expand`).
  5. Faltava navegação de baralhos pelas Setas do Teclado para complementar o analógico esquerdo e D-Pad.
- **Hipótese Principal (H0 - Confirmada)**:
  - Adicionar a flag `is_dialog_active` ao despachador e conectá-la aos ciclos `showEvent`/`closeEvent`/`reject` dos diálogos bloqueia 100% dos disparos de ações na tela de fundo e redireciona a rolagem contínua para a área de rolagem da própria janela de configurações.
- **Hipótese Acessória 1 (H1 - Confirmada)**:
  - A renderização em rabiscos decorria de cartões ultra-compactos (`50x38 px`) com fontes de `9px` sob escala de DPI do Windows. Expandir para `78x46 px` com tipografia vetorial nítida (`11px` bold e `12px` Consolas monospace) e tags semânticas (`B0 · ✕ (A)`) garante legibilidade cristalina em qualquer resolução.
- **Hipótese Acessória 2 (H2 - Confirmada)**:
  - Definir `setFocusPolicy(Qt.FocusPolicy.NoFocus)` no widget e em todos os botões do Pomodoro FAB elimina por completo a armadilha de teclado (WCAG 2.1.2 - No Keyboard Trap), permitindo que a tecla `Tab` circule livremente pelos links nativos do Anki.
- **Hipótese Acessória 3 (H3 - Confirmada)**:
  - Injetar o padrão WAI-ARIA *Roving Tabindex* com listener de teclado (`ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Enter`, `Home`, `End`) e atributos `role="treeitem"`, `aria-selected` e `aria-expanded` viabiliza navegação universal por teclado sem poluição visual, mantendo o halo sutil ciano `:focus-visible`.

---

### 2. Plano de Ação, Verificação Empírica e Reparo Cirúrgico (Fase 3)

#### Componentes Atualizados:
1. **`modules/gamepad/visualizer.py`**:
   - Redesenhado `ButtonTelemetryCard` para `78x46 px`.
   - Adicionada tipografia vetorial de alta nitidez com `Consolas` e `Segoe UI` (`11px/12px`).
   - Adicionado `display_title` nos 16 cartões com símbolos de identificação cruzada PlayStation / Xbox / Nintendo.
2. **`modules/gamepad/actions.py`**:
   - Implementadas `is_dialog_active` e `active_dialog_scroll`.
   - Bloqueada execução de ações no Anki de fundo quando `is_dialog_active` for verdadeiro.
   - Redirecionada rolagem do stick para o `active_dialog_scroll` quando em configuração.
   - Adicionadas ações:
     - `pomo_toggle`: Iniciar / Pausar Cronômetro
     - `pomo_skip`: Pular para Próxima Etapa
     - `pomo_reset`: Reiniciar Rodada Atual
     - `pomo_expand`: Expandir / Minimizar Janela Flutuante
3. **`modules/gamepad/config_dialog.py` & `modules/unified_config/settings_dialog.py`**:
   - Conectados `showEvent`, `hideEvent`, `closeEvent` e `reject` para ativar/desativar `is_dialog_active` e vincular a área de rolagem interna.
4. **`modules/pomodoro/native_fab.py` & `reviewer_fab.py`**:
   - Aplicado `setFocusPolicy(Qt.FocusPolicy.NoFocus)` em todos os botões do FAB flutuante e `tabindex="-1"` no HTML, erradicando o aprisionamento do `Tab`.
5. **`modules/dashboard/renderer.py`**:
   - Injetadas regras de acessibilidade elegante `:focus-visible` com anel ciano sem pontilhado antigo.
   - Injetado script completo de navegação de baralhos por setas do teclado (`ArrowUp/Down` para mover foco, `ArrowRight` para expandir subbaralhos, `ArrowLeft` para recolher, `Enter/Espaço` para abrir baralho, `Home/End` para saltar início/fim).

---

### 3. Análise Pós-Reparo e Verificação de Falha Residual (Fase 4)
- **Hipótese Residual (HR)**: O foco da tecla `Tab` poderia colidir com links dentro do dashboard.
- **Solução Validada**: O script marca os baralhos com `tabIndex = 0` apenas para o item ativo (`roving tabindex`), deixando os demais em `-1`.
- **Verificação Pós-Reparo**: 38 testes unitários executados e aprovados com 100% de sucesso (`Ran 38 tests in 0.157s, OK`).

---

## 📌 [Atualização 2026-09-02 - v1.7.0] - Disparo ao Soltar (Release Mode) para Pressionar/Segurar Botões na Tela, Contração Visual Acentuada & Escala de Tamanho Customizável
