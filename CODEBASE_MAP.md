# 🗺️ MAPA TOPOLÓGICO DO CÓDIGO (CODEBASE_MAP.md)
<!-- Inventário funcional e mapa cirúrgico do repositório Obsidian Addon Suite -->

Este arquivo é o índice topológico oficial de navegação do projeto. Subagentes recebem coordenadas deste arquivo em seus **Context Packets** para eliminar varreduras redundantes via disco.

---

## 1. Módulos do Sistema & Coordenadas Topológicas

### A. Núcleo do Add-on (Root & Core)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Root Entrypoint** | `__init__.py` | - | `init_all_modules()`, carregamento de módulos e hooks globais | Estável |
| **Core Models** | `core/models.py` | `PriorityConfig`, `ScopeType`, `DeckHierarchyNode`, `DeckConfig`, `ProcessingLog` | Modelagem DTO de nós de baralhos, enums e configurações de priorização | Estável |
| **Core Hierarchy** | `core/hierarchy.py` | `HierarchyManager` | `build_tree()`, `get_flattened_order()`, cálculo de pesos hierárquicos de decks | Estável |
| **Core Reorder** | `core/reorder.py` | `CardReorderEngine` | `reorder_queue()`, `evaluate_deck_cards()`, reordenação determinística da fila de estudo | Estável |

---

### B. Módulo Pomodoro & Anti-Distração (`modules/pomodoro/`)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Entrypoint** | `modules/pomodoro/__init__.py` | - | Inicialização do módulo, registro de atalhos e acoplamento de hooks | Estável |
| **Engine de Tempo** | `modules/pomodoro/timer_engine.py` | `PomodoroEngine`, `PomodoroState` | Máquina de estados (`WORK`, `SOFT_BREAK`, `BREAK`, `LONG_BREAK`, `PAUSED`); suporte a `is_paused_by_editing`, `pause_for_editing()`, `resume_from_editing()`, `pause_for_focus_loss()`, `resume_from_focus_loss()`, `tick()`, `register_user_activity()` | Estável |
| **Guardião de Foco** | `modules/pomodoro/focus_guard.py` | `FocusGuard`, `FocusReminderDialog` | Polling OS Win32 (250ms), resolução de parentesco modal via `QApplication.activeModalWidget()`, auto-hide do cursor mouse (2s idle), alerta de distração | Estável |
| **Hooks e Eventos** | `modules/pomodoro/hooks.py` | - | `setup_pomodoro_hooks()`, `get_focus_guard()`, `on_editor_did_init()`, `on_add_cards_did_init()`, `on_reviewer_card_shown()`, logging forense | Estável |
| **FAB Flutuante Nativo** | `modules/pomodoro/native_fab.py` | `NativePomodoroFab`, `DraggableCard` | Widget flutuante PyQt6 sem bordas, arraste com clamping, sombra expandida anti-corte, clique-through na margem transparente | Estável |
| **FAB Revisor** | `modules/pomodoro/reviewer_fab.py` | `ReviewerPomodoroFab` | Integração do widget Pomodoro com a barra inferior e interface do revisor | Estável |
| **Gerenciador HUD** | `modules/pomodoro/hud_manager.py` | `PomodoroHudManager` | Gerencia overlays do HUD no Deck Browser e Reviewer | Estável |
| **Motor de Áudio** | `modules/pomodoro/sounds.py` | - | `play_pomodoro_sound(event_type)`: `work_end`, `break_end`, `focus_loss`, `inactivity` via `winsound.PlaySound` assíncrono no Windows | Estável |
| **Sintetizador Sonoro** | `modules/pomodoro/sound_generator.py` | `SoundGenerator` | Geração procedural de arquivos `.wav` de alarme e sino no padrão PCM 16-bit | Estável |
| **Análise de Fadiga** | `modules/pomodoro/fatigue_analytics.py` | `FatigueAnalyticsEngine` | Cálculo de índice de fadiga do usuário com base no ritmo de respostas | Estável |
| **UI Configuração** | `modules/pomodoro/config_dialog.py` | `PomodoroConfigDialog` | Diálogo com sliders anti-scroll steal, seletor de áudio e teste imediato | Estável |

---

### C. Módulo Buscador de Imagens (`modules/image_search/`)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Entrypoint & Hooks** | `modules/image_search/__init__.py` | - | `open_image_search_for_editor()`, `insert_image_into_editor()`, `on_editor_did_init_buttons()`, integração com atalho `Ctrl+Shift+I`; flush preventivo de edição na webview via `saveNow(true)`, escape e sanitização de mídia e inserção sincronizada sem perda de texto | Estável |
| **Motor de Busca** | `modules/image_search/search_engine.py` | - | `translate_query_to_english()`, `_TRANSLATION_CACHE`, `search_wikimedia()`, `search_wikipedia_articles()`, `search_google_images()`, `search_web_images()`, `search_duckduckgo_images()`, `download_image_bytes()`, `_calculate_relevance_score()`, filtros médicos anti-spam; download com bypass anti-hotlinking de Referer, suporte a certificados SSL expirados de servidores médicos, expansão e tradução de coleções fluidas peripancreáticas (`fluido peripancreático` -> `peripancreatic fluid collection`), insensibilidade universal a acentos (`_strip_accents`), normalização médica de prefixos (`peripancre`, `pancreat`, `pseudocist`, `fluido`, `liquido`, `colecao`), integração com DuckDuckGo Images de alto rendimento com CookieJar e headers de segurança do navegador, paginação multi-página (`page`), busca dual concorrente na web (PT + EN), normalização radiológica (CECT/CT/MRI), scoring para Radiopaedia e periódicos médicos de alta autoridade | Estável |
| **Gerenciador de Recentes** | `modules/image_search/recent_manager.py` | - | `get_recent_images()`, `add_recent_image()`, `clear_recent_images()`, `item_to_dict()`, `dict_to_item()`; persistência em cache MRU atômico (`user_files/recent_images.json`) de até 15 imagens, parâmetro `force_reload`, suporte a `thumb_url`, deduplicação estrita e sincronização com `config_manager` | Estável |
| **Editor Gráfico e Anotação** | `modules/image_search/ui/image_editor.py` | `ImageAnnotationCanvas`, `ImageEditorDialog` | `calculate_arrowhead_points()`, `normalize_rect_coords()`, anotação visual com setas, círculos e recorte retangular anti-aliased em alta resolução, desfazer ilimitado (`Ctrl+Z`), redefinição e exportação de bytes de imagem anotada | Estável |
| **Diálogo de Busca** | `modules/image_search/ui/search_dialog.py` | `ImageSearchDialog` | Janela modal com `QTabWidget` contendo abas "🔍 Pesquisa" e "🕒 Recentes (X)", seletor de motores, pré-preenchimento de seleção, visualização em grade 4xN com renderização garantida via `card.show()`, grade da aba Recentes conectada diretamente ao `QScrollArea` sem contêineres intermediários colapsáveis, desvinculação imediata de widgets com `setParent(None)`, pausa e retomada automática do Pomodoro, infinite scroll com detecção de scrollbar, footer dinâmico, deduplicação de cards, botão "🌐 Abrir página da imagem", botão "✏️ Editar e Inserir" acionando `ImageEditorDialog`, método `open_editor_for_item` garantindo inserção da imagem editada no card e gravação da imagem original intacta no histórico de recentes | Estável |
| **Card de Imagem** | `modules/image_search/ui/image_card.py` | `ImageCardWidget` | Miniatura assíncrona multi-tier com fallback de Referer e SSL permissivo, visualização com zoom parcial, botão de download flutuante, botão "🌐 Abrir página da imagem" no rodapé do card, suporte a menu de contexto com opções de download, zoom e "✏️ Editar e Inserir" acionando o editor | Estável |

---

### D. Módulo Theme Manager & Acessibilidade (`modules/theme_manager/`)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Entrypoint** | `modules/theme_manager/__init__.py` | - | `init_theme_manager()`, injeção no Anki e monitoramento de mudanças de perfil | Estável |
| **Motor CSS & WCAG** | `modules/theme_manager/engine.py` | - | `generate_global_theme_css()`, `inject_theme_into_dynamic_webview()`, `_sync_editor_theme_deferred()`, `get_perceptual_luminance()`, `get_contrast_ratio()`, `get_accessible_text_color()`, `get_hover_text_color()`, `apply_theme_to_anki()`, `get_qt_dialog_stylesheet()` (com suporte integral a `QScrollArea`, viewports, sliders, scrollbars e subcontroles de diálogos), sincronização dinâmica de temas claros/escuros no editor com injeção imperativa recursiva no Shadow DOM (`<anki-editable>`, `rich-text-editable`, `Ctrl+Shift+X`), `-webkit-text-fill-color`, sobrescrita de `style#userBase`, `MutationObserver` dedicado por `shadowRoot`, reforço periódico em background (200ms) e neutralização de `$pageTheme.isDark` do Svelte, tokens de sintaxe e seleção de alto contraste no CodeMirror, suporte integral a rotas SvelteKit (`/congrats`, `card-info`, `preferences`) e tela de parabéns/conclusão de baralho | Estável |
| **Presets de Tema** | `modules/theme_manager/presets.py` | - | Paletas WCAG AA: Dracula, Nord, Solarized Dark, Warm Paper, Clean Light, Catppuccin Mocha, OLED Dark, Midnight Blue | Estável |

---

### E. Módulo Dashboard Moderno (`modules/dashboard/`)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Entrypoint** | `modules/dashboard/__init__.py` | - | `init_dashboard()`, registro de hooks | Estável |
| **Renderizador HTML** | `modules/dashboard/renderer.py` | `ModernDashboardRenderer` | Renderização responsiva dos 5 cards; script `initAria` com restauração automática de baralho focado via `sessionStorage` pós-colapso/expansão | Estável |
| **Engine Estatístico** | `modules/dashboard/stats_engine.py` | `DashboardStatsEngine` | Extração de retenção, velocidade (cards/min), novos, cards maduros (≥21d) direto do SQLite | Estável |
| **Hooks do DeckBrowser** | `modules/dashboard/hooks.py` | - | `setup_dashboard_hooks()`, injeção antes da lista de baralhos | Estável |
| **UI Configuração** | `modules/dashboard/config_dialog.py` | `DashboardConfigDialog` | Configuração de metas de estudo, metas de novos e visibilidade de métricas | Estável |

---

### F. Módulo Gamepad & Controles (`modules/gamepad/`)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Entrypoint** | `modules/gamepad/__init__.py` | - | `init_gamepad()`, inicialização de threads de escuta de periféricos | Estável |
| **Input Manager** | `modules/gamepad/input_manager.py` | `GamepadInputManager` | Despacho de eventos de botões e sticks analógicos com debounce; `_ping_activity` com throttle de 1.0s para rolagem contínua e disparo imediato em botões/navegação para manter tela e Pomodoro acordados | Estável |
| **Executor de Ações** | `modules/gamepad/actions.py` | `GamepadActionDispatcher` | Roteamento de ações do Revisor, DeckBrowser e diálogos; `keep_system_and_pomodoro_active()`, preservação de baralho focado, delegação de borda ao DOM (`curIdx === 0 && delta < 0`), `ascend_to_topbar()`, `descend_from_topbar()`, `sync_deck_focus()` | Estável |
| **Hooks & Lifecycle** | `modules/gamepad/hooks.py` | - | `setup_gamepad_hooks()`, `on_webview_js_message()` para captura de pontes JS (`gamepad_ascend_topbar`, `gamepad_deck_focused`) e ciclo de vida de perfil | Estável |
| **Drivers de Hardware** | `modules/gamepad/drivers/` | `BaseGamepadDriver`, `XInputGamepadDriver`, `DirectInputGamepadDriver`, `PygameGamepadDriver`, `CompositeGamepadDriver` | Camada de abstração para controle Xbox (XInput), PlayStation e genéricos DirectInput | Estável |
| **Visualizador** | `modules/gamepad/visualizer.py` | `GamepadVisualizerDialog` | Interface gráfica de teste e visualização de botões pressionados em tempo real | Estável |
| **Feedback Sonoro** | `modules/gamepad/sounds.py` | - | `play_gamepad_sound()`: feedback tátil-sonoro para ações executadas | Estável |
| **UI Configuração** | `modules/gamepad/config_dialog.py` | `GamepadConfigDialog` | Tabela de mapeamento customizável botão ➔ ação com paleta adaptativa | Estável |

---

### G. Módulo Central de Configurações Unificada (`modules/unified_config/`)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Entrypoint** | `modules/unified_config/__init__.py` | - | `init_unified_config()`, atalhos e menu na barra superior | Estável |
| **Hub Dialog** | `modules/unified_config/settings_dialog.py` | `ObsidianSuiteHubDialog`, `FocusWheelSlider`, `FocusWheelSpinBox` | Janela unificada com abas de todos os módulos; `apply_dialog_theme()` com preview em tempo real ao alterar presets/swatches; estilização integral de viewports, scroll areas, spinboxes, sliders e checkboxes; controle anti-scroll steal | Estável |

---

### H. Módulos Auxiliares (Multiple Choice, Priority Sequencer & AnkiConnect)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Multiple Choice** | `modules/multiple_choice/` | `MultipleChoiceConfig`, `MultipleChoiceTemplate` | Templates de cartões de múltipla escolha com embaralhamento dinâmico e estilos customizados | Estável |
| **Priority Sequencer** | `modules/priority_sequencer/` | `PriorityManagerDialog`, `SetPriorityModal`, `ReorderProgressDialog`, `ReorderSummaryDialog`, `DeckNode`, `CardItem`, `IntegrityReport` | `build_deck_tree()`, `count_new_cards_by_deck()`, `run_reorder_with_ui()`, `execute_reorder_in_col()`, `verify_and_repair_card_order()` (DNA Proofreading e autocura in-flight), feedback visual com progresso e resumo rico | Estável |
| **AnkiConnect Ext** | `modules/ankiconnect/` | Web & Edit Extensions | Endpoints HTTP locais para automações externas e integrações com o editor | Estável |

---

### I. Utilitários Globais (`utils/`)
| Módulo / Camada | Arquivo | Principais Classes | Principais Funções / Responsabilidades | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Gerenciador Config** | `utils/config_manager.py` | `_DualKeyPriorityDict` | `get_config()`, `write_config()`, `get_module_config()`, `write_module_config()`, `get_deck_priorities()` e `set_deck_priority()` com compatibilidade bidirecional transparente de chaves `int` e `str` | Estável |
| **Internacionalização** | `utils/i18n.py` | - | `tr(key, default)`, `detect_anki_language()`; dicionário multilíngue nos 4 idiomas (`en`, `pt`, `es`, `fr`) | Estável |
| **Helpers de UI** | `utils/ui_helpers.py` | - | Helpers para formatação de widgets PyQt6, paletas, layout defensivo | Estável |
| **Motor de Áudio Central** | `utils/audio_player.py` | - | `get_volume_adjusted_wav()`, `play_sound_with_volume()`; atenuação PCM 16-bit com cache em disco e winsound assíncrono | Estável |

---

### J. Bateria de Testes Unitários (`tests/`)
| Arquivo de Teste | Alvo de Cobertura | Casos Principais Testados | Status |
| :--- | :--- | :--- | :--- |
| `tests/test_pomodoro.py` | `modules/pomodoro/` | Máquina de estados, avanço contínuo no intervalo, auto-pause por inatividade/perda de foco, ocultamento de cursor mouse, `is_paused_by_editing` | 100% Passing |
| `tests/test_image_search.py` | `modules/image_search/` | Scraper Google Images (udm=2) com bypass GDPR, API Wikimedia Commons, tradução médica para inglês, filtro anti-spam, inserção segura no editor | 100% Passing |
| `tests/test_theme_manager.py` | `modules/theme_manager/` | Cálculo WCAG 2.1 AA, luminância CIE, contraste de botões de facilidade (`.nobold`), contraste de `#study`/`#ansbut` | 100% Passing |
| `tests/test_gamepad.py` | `modules/gamepad/` | Mapeamento de botões B0-B17, triggers de ação, drivers | 100% Passing |
| `tests/test_dashboard_stats.py` | `modules/dashboard/` | Métricas de retenção, cálculo de maturidade e metas diárias | 100% Passing |
| `tests/test_i18n.py` | `utils/i18n.py` | Paridade de chaves entre idiomas `pt`, `en`, `es`, `fr` | 100% Passing |
| `tests/test_unified_config.py` | `modules/unified_config/` | Persistência e integridade das seções do `config.json` | 100% Passing |
| `tests/test_hierarchy.py` | `core/hierarchy.py` | Resolução da árvore hierárquica de baralhos | 100% Passing |
| `tests/test_reorder.py` | `core/reorder.py` | Reordenação estável da fila de cartões | 100% Passing |
| `tests/test_integrity.py` | `core/integrity.py`, `modules/priority_sequencer/integrity.py` | Auditoria de contiguidade de blocos, monotonicidade, detecção de colisões de `due` e autocura atômica (DNA Proofreading) | 100% Passing |
| `tests/test_pomodoro_editing_pause.py` | `modules/pomodoro/`, `modules/image_search/` | Pausa por edição em WORK, imunidade nos descansos (BREAK/LONG_BREAK), retomada pós-edição, supressão de alarme no FocusGuard, resolução de activeModalWidget no FocusReminderDialog, WindowModal no ImageSearchDialog | 100% Passing |
| `tests/test_image_search_pagination.py` | `modules/image_search/` | Paginação multi-página (`page`), busca dual web (PT + EN), normalização radiológica (CECT/CT/MRI), infinite scroll e deduplicação de cards | 100% Passing |
| `tests/test_image_search_medical_routing.py` | `modules/image_search/` | Roteamento estrito por motor (sem vazamento cruzado), filtro anti-biografia Wikidata (`-haswbstatement:P31=Q5`), preservação de URLs canônicas da Wikipédia, resiliência do parser do Google Images e integridade dos links de fonte externa (`item.source`) | 100% Passing |
| `tests/test_image_search_recent.py` | `modules/image_search/recent_manager.py`, `modules/image_search/ui/search_dialog.py` | Ordem MRU (mais recente no topo), teto estrito de 15 imagens, deduplicação por URL, serialização JSON, integração com abas, inserção no diálogo e validação de transição de layout vazio vs populado | 100% Passing |
| `tests/test_image_editor.py` | `modules/image_search/ui/image_editor.py`, `modules/image_search/ui/search_dialog.py` | Trigonometria de setas vetoriais, normalização retangular de recorte, paridade de 11 chaves de i18n e preservação da imagem original no histórico de recentes | 100% Passing |
| `tests/test_gamepad_accessibility.py` | `modules/gamepad/`, `modules/pomodoro/`, `modules/unified_config/` | Ações `pomo_fullscreen` e `open_settings`, navegação bidirecional no `RestOverlayDialog` (+5 min vs Retomar) e controle total do `ObsidianSuiteHubDialog` (LB/RB abas, LS navegação, A ativação, RS sliders, B sair/fechar) | 100% Passing |
| `tests/test_gamepad_deck_preservation.py` | `modules/gamepad/`, `modules/pomodoro/` | Preservação do ID do baralho selecionado, keep-alive do display do Windows e do temporizador do Pomodoro, algoritmo de ponto fixo de PIDs do Anki e verificação rápida de janela ativa no FocusGuard | 100% Passing |
| `tests/test_audio_volume.py` | `utils/audio_player.py`, `modules/gamepad/`, `modules/pomodoro/` | Atenuação PCM 16-bit, integridade de cabeçalho WAV, cache atômico em disco, supressão de som em volume zero e resolução de volume individual por evento | 100% Passing |

