# Resumo Arquitetural & Cheat Sheet dos Módulos

## 1. `modules/pomodoro/`
- `timer_engine.py`:
  - Estados: `WORK`, `SOFT_BREAK`, `BREAK`, `LONG_BREAK`, `PAUSED`.
  - Inatividade: `self.state == PomodoroState.WORK and config.get("inactivity_detection", True)`.
  - Intervalo: decrementa livremente mesmo inativo ou sem foco.
- `focus_guard.py`:
  - `QGuiApplication.instance().applicationStateChanged` detecta perda de foco global.
  - Pausa e alarme ocorrem apenas se `state == PomodoroState.WORK`.
- `sounds.py`:
  - No Windows, `.wav` usa `winsound.PlaySound(..., winsound.SND_FILENAME | winsound.SND_ASYNC)`.
  - Eventos suportados: `work_end`, `break_end`, `focus_loss`, `inactivity`.

## 2. `modules/theme_manager/`
- `engine.py`:
  - WCAG 2.1 CIE Luminance & Contrast:
    - `get_perceptual_luminance(hex_str)`
    - `get_contrast_ratio(c1, c2)`
    - `get_accessible_text_color(bg_hex)` (garante ≥ 4.5:1).
  - `#study` e `#ansbut` recebem cor acessível dinâmica calculada sobre `accent`.
- `presets.py`:
  - Dracula, Nord, Solarized Dark, Warm Paper, Clean Light, Catppuccin Mocha, OLED Dark.

## 3. `modules/dashboard/`
- `renderer.py`: Modern Dashboard HTML com 5 cards e layout responsivo.
- `stats.py`: Métricas de retenção, ritmo e maturidade.

## 4. `modules/gamepad/`
- Suporte a botões 0-17, analógicos esquerdo/direito e atalhos de teclado configuráveis.

## 5. `modules/unified_config/`
- `settings_dialog.py` (`ObsidianSuiteHubDialog`): Central única com 6 abas.
- Sliders/spinboxes usam classes customizadas com foco para não roubar o scroll da página.

## 6. `utils/i18n.py`
- Suporte a 4 idiomas: `en` (padrão), `pt`, `es`, `fr`.
- Resolução multicamada: override manual -> `mw.pm.defaultLang` -> `prefs21.db` -> `QLocale` -> fallback para `en`.
