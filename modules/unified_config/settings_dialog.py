# -*- coding: utf-8 -*-
"""
Obsidian Suite Hub - Unified Settings & Control Center Dialog.
Consolidates Themes, Dashboard, Pomodoro, Audio Notifications, Priorities, and Integrations into a modern multi-tab window.
"""

from typing import Dict, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QTabWidget,
        QWidget,
        QLabel,
        QSpinBox,
        QCheckBox,
        QPushButton,
        QGroupBox,
        QColorDialog,
        QComboBox,
        QLineEdit,
        QFileDialog,
        QSlider,
        QScrollArea,
        QFrame,
    )
    from PyQt6.QtGui import QColor, QFont, QIcon
    from PyQt6.QtCore import Qt
    from aqt import mw
    from aqt.utils import tooltip
except ImportError:
    class _MockUIMeta(type):
        def __getattr__(cls, name):
            return _MockUI()

    class _MockUI(metaclass=_MockUIMeta):
        def __init__(self, *args, **kwargs):
            self.color_hex = "#000000"
            self._cur_data = "oled_dark"
            self._cur_idx = 0
            self._items = []
            self._checked = True
            self._val = 100
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return _MockUI()
        def addItem(self, text, data=None):
            self._items.append((text, data))
            if len(self._items) == 1:
                self._cur_data = data
        def addTab(self, widget, label=""):
            self._items.append((label, widget))
        def count(self):
            return len(self._items)
        def setWidget(self, w):
            self._inner_widget = w
        def widget(self, idx=None):
            if idx is not None and 0 <= idx < len(self._items):
                return self._items[idx][1]
            if hasattr(self, "_inner_widget"):
                return self._inner_widget
            if len(self._items) > 0 and idx is None:
                return self._items[0][1]
            return _MockUI()
        def currentWidget(self):
            if 0 <= self._cur_idx < len(self._items):
                return self._items[self._cur_idx][1]
            return _MockUI()
        def findData(self, val):
            for i, (_, data) in enumerate(self._items):
                if data == val:
                    return i
            return -1
        def setCurrentIndex(self, idx):
            self._cur_idx = idx
            if 0 <= idx < len(self._items):
                self._cur_data = self._items[idx][1]
        def currentData(self):
            return self._cur_data
        def currentIndex(self):
            return self._cur_idx
        def blockSignals(self, b):
            pass
        def isChecked(self):
            return self._checked
        def setChecked(self, b):
            self._checked = bool(b)
        def value(self):
            return self._val
        def setValue(self, v):
            self._val = v
        def singleStep(self):
            return 1
        def stepDown(self):
            self._val -= 1
        def stepUp(self):
            self._val += 1
        def text(self):
            return ""

    QDialog = _MockUI
    QVBoxLayout = _MockUI
    QHBoxLayout = _MockUI
    QTabWidget = _MockUI
    QWidget = _MockUI
    QLabel = _MockUI
    QSpinBox = _MockUI
    QCheckBox = _MockUI
    QPushButton = _MockUI
    QGroupBox = _MockUI
    QColorDialog = _MockUI
    QComboBox = _MockUI
    QLineEdit = _MockUI
    QFileDialog = _MockUI
    QSlider = _MockUI
    QScrollArea = _MockUI
    QFrame = _MockUI
    QColor = _MockUI
    QFont = _MockUI
    QIcon = _MockUI
    Qt = _MockUI()
    mw = None
    tooltip = None

from ..theme_manager.presets import THEME_PRESETS, get_active_theme_colors
try:
    from ..theme_manager.engine import (
        apply_theme_to_anki,
        get_qt_dialog_stylesheet,
        get_accessible_text_color,
        is_light_color,
        get_contrast_ratio,
        get_perceptual_luminance,
    )
except (ImportError, ValueError):
    try:
        from modules.theme_manager.engine import (
            apply_theme_to_anki,
            get_qt_dialog_stylesheet,
            get_accessible_text_color,
            is_light_color,
            get_contrast_ratio,
            get_perceptual_luminance,
        )
    except ImportError:
        def apply_theme_to_anki(): pass
        def get_qt_dialog_stylesheet(c): return ""
        def get_accessible_text_color(bg, dark="#0f172a", light="#ffffff"): return light
        def is_light_color(c): return False
        def get_contrast_ratio(a, b): return 5.0
        def get_perceptual_luminance(c): return 0.5
from ..priority_sequencer.ui.priority_dialog import DeckPriorityManagerDialog
from ..pomodoro.sounds import play_pomodoro_sound
try:
    from ..gamepad import GamepadConfigWidget, get_gamepad_manager
except Exception:
    try:
        from modules.gamepad import GamepadConfigWidget, get_gamepad_manager
    except Exception:
        GamepadConfigWidget = None
        get_gamepad_manager = None
try:
    from ...utils.config_manager import get_module_config, write_module_config
    from ...utils.ui_helpers import FocusWheelSlider, FocusWheelComboBox, FocusWheelSpinBox
    from ...utils.i18n import tr, set_language_override
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config, write_module_config
        from utils.ui_helpers import FocusWheelSlider, FocusWheelComboBox, FocusWheelSpinBox
        from utils.i18n import tr, set_language_override
    except ImportError:
        FocusWheelSlider = QSlider
        FocusWheelComboBox = QComboBox
        FocusWheelSpinBox = QSpinBox
        def tr(key, default=None, **kwargs):
            return default if default is not None else key
        def set_language_override(lang):
            pass
        FocusWheelSpinBox = QSpinBox


class ColorPickerButton(QPushButton):
    """Interactive button for picking hex colors with visual swatch preview."""

    def __init__(self, initial_color: str, on_changed=None, parent=None):
        super().__init__(parent)
        self.color_hex = initial_color
        self.on_changed = on_changed
        self.setFixedHeight(30)
        self.setFixedWidth(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._choose_color)
        self._update_swatch()

    def _update_swatch(self):
        self.setText(self.color_hex)
        try:
            r, g, b = (
                int(self.color_hex[1:3], 16),
                int(self.color_hex[3:5], 16),
                int(self.color_hex[5:7], 16),
            )
            is_dark = (r * 0.299 + g * 0.587 + b * 0.114) < 128
        except Exception:
            is_dark = True
        txt_color = "#ffffff" if is_dark else "#000000"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                color: {txt_color};
                border: 1px solid #555555;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover, QPushButton:focus, QPushButton[gamepadFocused="true"] {{
                border: 2px solid #38bdf8;
            }}
        """)

    def _choose_color(self):
        try:
            color = QColorDialog.getColor(QColor(self.color_hex), self, "Selecione a Cor")
            if color.isValid():
                self.color_hex = color.name()
                self._update_swatch()
                if self.on_changed:
                    self.on_changed(self.color_hex)
        except Exception:
            pass


class ObsidianSuiteHubDialog(QDialog):
    """
    Unified Hub Dialog providing a single centralized interface for all modules.
    """

    def __init__(self, parent=None):
        super().__init__(parent or (mw if mw else None))
        self.setWindowTitle("⚙️ Obsidian Addon Suite - Central de Configurações")
        self.resize(860, 680)
        self.setMinimumSize(780, 580)

        self._setup_ui()

    def _setup_ui(self):
        theme_cfg = get_module_config("theme")
        colors = get_active_theme_colors(theme_cfg)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Header Title Banner
        self.header = QWidget()
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(4, 4, 4, 8)

        self.lbl_title = QLabel("🔮 <b>Obsidian Addon Suite</b> — Painel de Controle Unificado")
        h_layout.addWidget(self.lbl_title)
        h_layout.addStretch()

        main_layout.addWidget(self.header)

        # Tabs
        self.tabs = QTabWidget()

        self.tab_general = self._wrap_tab_in_scroll(self._build_general_tab())
        self.tab_themes = self._wrap_tab_in_scroll(self._build_themes_tab())
        self.tab_dashboard = self._wrap_tab_in_scroll(self._build_dashboard_tab())
        self.tab_pomodoro = self._wrap_tab_in_scroll(self._build_pomodoro_tab())
        self.tab_gamepad = self._build_gamepad_tab()
        self.tab_priority = self._wrap_tab_in_scroll(self._build_priority_tab())
        self.tab_integrations = self._wrap_tab_in_scroll(self._build_integrations_tab())

        self.tabs.addTab(self.tab_general, tr("tab_general", "🌐 Geral"))
        self.tabs.addTab(self.tab_themes, tr("tab_theme", "🎨 Temas & Cores"))
        self.tabs.addTab(self.tab_dashboard, tr("tab_dashboard", "📊 Modern Dashboard"))
        self.tabs.addTab(self.tab_pomodoro, tr("tab_pomodoro", "🍅 Pomodoro & Áudio"))
        self.tabs.addTab(self.tab_gamepad, tr("tab_gamepad", "🎮 Gamepad & Controles"))
        self.tabs.addTab(self.tab_priority, tr("tab_priority", "🗂️ Sequenciador"))
        self.tabs.addTab(self.tab_integrations, tr("tab_integrations", "🔌 Integrações"))

        self.tabs.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.tabs)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.btn_cancel = QPushButton(tr("btn_cancel", "Cancelar"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton(tr("btn_save_apply", "💾 Salvar & Aplicar"))
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_all_settings)
        btn_bar.addWidget(self.btn_save)

        main_layout.addLayout(btn_bar)

        # Apply complete theme stylesheet, colors, and titlebar
        self.apply_dialog_theme(colors)

    def apply_dialog_theme(self, colors: Optional[Dict[str, str]] = None):
        """Applies or updates the complete Qt theme stylesheet across the entire dialog in real-time."""
        if colors is None:
            theme_cfg = get_module_config("theme")
            colors = get_active_theme_colors(theme_cfg)

        self._current_theme_colors = colors
        accent = colors.get("accent", "#38bdf8")
        bg_pri = colors.get("bg_primary", "#000000")
        border = colors.get("border_color", "#27272a")
        text_pri = colors.get("text_primary", "#f8fafc")

        # 1. Native Windows Titlebar
        try:
            from ..theme_manager.engine import set_windows_titlebar_color
            if hasattr(self, "winId") and self.winId():
                set_windows_titlebar_color(bg_pri, hwnd=int(self.winId()))
        except Exception:
            pass

        # 2. Qt Dialog Stylesheet + Gamepad Focus Rings
        base_ss = get_qt_dialog_stylesheet(colors)
        gp_focus_style = f"""
            *[gamepadFocused="true"] {{
                border: 2px solid {accent} !important;
                outline: 2px solid {accent} !important;
            }}
            QCheckBox[gamepadFocused="true"], QRadioButton[gamepadFocused="true"] {{
                border: 2px solid {accent} !important;
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton[gamepadFocused="true"] {{
                border: 2px solid {accent} !important;
            }}
            QComboBox[gamepadFocused="true"] {{
                border: 2px solid {accent} !important;
            }}
            QSlider[gamepadFocused="true"] {{
                border: 2px solid {accent} !important;
                border-radius: 4px;
            }}
            QSpinBox[gamepadFocused="true"] {{
                border: 2px solid {accent} !important;
            }}
            QLineEdit[gamepadFocused="true"] {{
                border: 2px solid {accent} !important;
            }}
        """
        self.setStyleSheet(base_ss + gp_focus_style)

        # 3. Header title color
        if hasattr(self, "lbl_title") and self.lbl_title:
            title_color = accent if get_contrast_ratio(get_perceptual_luminance(accent), get_perceptual_luminance(bg_pri)) >= 4.0 else text_pri
            self.lbl_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {title_color}; background-color: transparent;")

        # 4. Save Button Styling
        if hasattr(self, "btn_save") and self.btn_save:
            btn_save_text = get_accessible_text_color(accent)
            self.btn_save.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: {btn_save_text};
                    font-weight: bold;
                    padding: 7px 22px;
                    border-radius: 6px;
                    border: 1px solid {border};
                }}
                QPushButton:hover {{
                    filter: brightness(1.15);
                }}
            """)

    # 0. General Tab
    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        gen_cfg = get_module_config("general")

        grp = QGroupBox(tr("tab_general", "🌐 Geral"))
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(10)

        lbl_desc = QLabel(tr("general_interface_desc", "Selecione o idioma utilizado nas janelas, notificações e widgets do addon. 'Automático' segue o idioma do Anki (com inglês como padrão para outros idiomas)."))
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; margin-bottom: 6px;")
        grp_layout.addWidget(lbl_desc)

        h_lang = QHBoxLayout()
        h_lang.addWidget(QLabel(tr("general_interface_lang", "Idioma da Interface do Addon:")))

        self.combo_lang = FocusWheelComboBox()
        self.combo_lang.addItem(tr("lang_auto", "🌐 Automático (Idioma do Anki)"), "auto")
        self.combo_lang.addItem(tr("lang_en", "🇺🇸 English (Default)"), "en")
        self.combo_lang.addItem(tr("lang_pt", "🇧🇷 / 🇵🇹 Português"), "pt")
        self.combo_lang.addItem(tr("lang_es", "🇪🇸 Español"), "es")
        self.combo_lang.addItem(tr("lang_fr", "🇫🇷 Français"), "fr")

        cur_lang = gen_cfg.get("language", "auto")
        idx = self.combo_lang.findData(cur_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        h_lang.addWidget(self.combo_lang)
        grp_layout.addLayout(h_lang)

        layout.addWidget(grp)
        layout.addStretch()
        return widget

    # 1. Themes Tab
    def _build_themes_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        theme_cfg = get_module_config("theme")

        self.chk_theme_enabled = QCheckBox(tr("theme_enable_chk", "Ativar Personalização Global de Cores no Anki"))
        self.chk_theme_enabled.setChecked(theme_cfg.get("enabled", True))
        layout.addWidget(self.chk_theme_enabled)

        # Preset Selector
        preset_grp = QGroupBox(tr("theme_palette_grp", "Paleta de Cores e Estilo Visual"))
        preset_layout = QVBoxLayout(preset_grp)

        h_pre = QHBoxLayout()
        h_pre.addWidget(QLabel(tr("theme_preset_lbl", "Tema Predefinido:")))
        self.combo_presets = FocusWheelComboBox()
        for k, v in THEME_PRESETS.items():
            self.combo_presets.addItem(v["name"], k)
        self.combo_presets.addItem(tr("theme_custom_option", "🛠️ Personalizado (Custom)"), "custom")

        cur_preset = theme_cfg.get("preset", "oled_dark")
        idx = self.combo_presets.findData(cur_preset)
        if idx >= 0:
            self.combo_presets.setCurrentIndex(idx)
        else:
            self.combo_presets.setCurrentIndex(0)
        self.combo_presets.currentIndexChanged.connect(self._on_preset_changed)
        h_pre.addWidget(self.combo_presets)
        preset_layout.addLayout(h_pre)

        # Custom Pickers Group
        self.custom_colors_grp = QGroupBox(tr("theme_custom_grp", "Cores Customizadas (Ajuste em Tempo Real)"))
        custom_layout = QVBoxLayout(self.custom_colors_grp)

        active_colors = get_active_theme_colors(theme_cfg)

        self.color_buttons: Dict[str, ColorPickerButton] = {}
        fields = [
            ("bg_primary", tr("theme_bg_primary", "Fundo Principal da Janela:")),
            ("bg_card", tr("theme_bg_card", "Fundo dos Cards e Painéis:")),
            ("accent", tr("theme_accent", "Cor de Destaque / Botões:")),
            ("text_primary", tr("theme_text_primary", "Texto Principal:")),
            ("text_secondary", tr("theme_text_secondary", "Texto Secundário:")),
            ("border_color", tr("theme_border", "Bordas dos Cards:")),
            ("new_color", tr("theme_new", "Cor de Novos Cards:")),
            ("learn_color", tr("theme_learn", "Cor de Aprendizado:")),
            ("review_color", tr("theme_review", "Cor de Revisão:")),
        ]

        grid_layout = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()

        for i, (key, label) in enumerate(fields):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            btn = ColorPickerButton(
                active_colors.get(key, "#181825"),
                on_changed=lambda _: self._on_custom_color_picked()
            )
            self.color_buttons[key] = btn
            row.addWidget(btn)
            if i < len(fields) // 2:
                col1.addLayout(row)
            else:
                col2.addLayout(row)

        grid_layout.addLayout(col1)
        grid_layout.addLayout(col2)
        custom_layout.addLayout(grid_layout)

        preset_layout.addWidget(self.custom_colors_grp)
        layout.addWidget(preset_grp)

        # Answer Buttons Colors Group
        self.ans_buttons_grp = QGroupBox(tr("theme_ans_grp", "🎨 Cores dos Botões de Resposta (Reviewer)"))
        ans_layout = QVBoxLayout(self.ans_buttons_grp)

        ans_cfg = theme_cfg.get("answer_buttons", {})
        self.chk_ans_buttons = QCheckBox(tr("theme_ans_enable", "Ativar Cores Personalizadas nos Botões de Resposta"))
        self.chk_ans_buttons.setChecked(ans_cfg.get("enabled", True))
        ans_layout.addWidget(self.chk_ans_buttons)

        ans_grid = QHBoxLayout()
        self.btn_ans_again = ColorPickerButton(ans_cfg.get("again_color", "#ef4444"))
        self.btn_ans_hard = ColorPickerButton(ans_cfg.get("hard_color", "#b45309"))
        self.btn_ans_good = ColorPickerButton(ans_cfg.get("good_color", "#16a34a"))
        self.btn_ans_easy = ColorPickerButton(ans_cfg.get("easy_color", "#2563eb"))

        for label, btn in [
            (tr("theme_ans_again", "🔴 De novo (1):"), self.btn_ans_again),
            (tr("theme_ans_hard", "🟤 Difícil (2):"), self.btn_ans_hard),
            (tr("theme_ans_good", "🟢 Bom (3):"), self.btn_ans_good),
            (tr("theme_ans_easy", "🔵 Fácil (4):"), self.btn_ans_easy),
        ]:
            col = QVBoxLayout()
            col.addWidget(QLabel(label))
            col.addWidget(btn)
            ans_grid.addLayout(col)

        ans_layout.addLayout(ans_grid)

        h_btn_scale = QHBoxLayout()
        h_btn_scale.addWidget(QLabel(tr("theme_ans_scale", "Tamanho dos Botões (Escala):")))
        self.slider_theme_btn_scale = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_theme_btn_scale.setRange(80, 160)
        self.slider_theme_btn_scale.setValue(int(ans_cfg.get("button_scale", 1.15) * 100))
        self.lbl_theme_btn_scale = QLabel(f"{self.slider_theme_btn_scale.value()}%")
        self.lbl_theme_btn_scale.setFixedWidth(45)
        self.slider_theme_btn_scale.valueChanged.connect(lambda v: self.lbl_theme_btn_scale.setText(f"{v}%"))
        h_btn_scale.addWidget(self.slider_theme_btn_scale)
        h_btn_scale.addWidget(self.lbl_theme_btn_scale)
        ans_layout.addLayout(h_btn_scale)

        layout.addWidget(self.ans_buttons_grp)

        layout.addStretch()
        return widget

    def _on_custom_color_picked(self):
        """When a user manually modifies a color swatch, switch combo to 'custom' and live-preview."""
        idx = self.combo_presets.findData("custom")
        if idx >= 0 and self.combo_presets.currentIndex() != idx:
            self.combo_presets.blockSignals(True)
            self.combo_presets.setCurrentIndex(idx)
            self.combo_presets.blockSignals(False)
        colors = {k: btn.color_hex for k, btn in self.color_buttons.items()}
        self.apply_dialog_theme(colors)

    def _on_preset_changed(self):
        preset_key = self.combo_presets.currentData()
        if preset_key in THEME_PRESETS:
            preset_data = THEME_PRESETS[preset_key]
            colors = preset_data.get("colors", preset_data)
            for k, btn in self.color_buttons.items():
                if k in colors:
                    btn.color_hex = colors[k]
                    btn._update_swatch()
            self.apply_dialog_theme(colors)

    # 2. Dashboard Tab
    def _build_dashboard_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        dash_cfg = get_module_config("dashboard")

        self.chk_dash_enabled = QCheckBox(tr("dash_enable_chk", "Ativar Modern Dashboard"))
        self.chk_dash_enabled.setChecked(dash_cfg.get("enabled", True))
        layout.addWidget(self.chk_dash_enabled)

        # Cards Toggle Group
        cards_grp = QGroupBox(tr("dash_cards_grp", "Cards & Seções Visíveis"))
        cards_layout = QVBoxLayout(cards_grp)

        self.chk_show_goals = QCheckBox(tr("dash_show_goals", "Metas Diárias & Foco do Dia"))
        self.chk_show_goals.setChecked(dash_cfg.get("show_daily_goals", True))
        cards_layout.addWidget(self.chk_show_goals)

        self.chk_show_comp = QCheckBox(tr("dash_show_comp", "Composição do Baralho (Novos / Aprendizado / Revisão)"))
        self.chk_show_comp.setChecked(dash_cfg.get("show_deck_composition", True))
        cards_layout.addWidget(self.chk_show_comp)

        self.chk_show_today = QCheckBox(tr("dash_show_today", "Progresso de Hoje (Retenção & Total Estudado)"))
        self.chk_show_today.setChecked(dash_cfg.get("show_today_progress", True))
        cards_layout.addWidget(self.chk_show_today)

        self.chk_show_remaining = QCheckBox(tr("dash_show_remaining", "Cartões Restantes na Fila de Hoje"))
        self.chk_show_remaining.setChecked(dash_cfg.get("show_remaining", True))
        cards_layout.addWidget(self.chk_show_remaining)

        self.chk_show_done = QCheckBox(tr("dash_show_done", "Resumo de Concluídos Hoje"))
        self.chk_show_done.setChecked(dash_cfg.get("show_done_today", True))
        cards_layout.addWidget(self.chk_show_done)

        layout.addWidget(cards_grp)

        # Placement Options
        place_grp = QGroupBox(tr("dash_place_grp", "Local de Exibição & Layout"))
        place_layout = QVBoxLayout(place_grp)

        self.chk_on_overview = QCheckBox(tr("dash_on_overview", "Exibir na Tela de Overview do Baralho"))
        self.chk_on_overview.setChecked(dash_cfg.get("show_on_overview", True))
        place_layout.addWidget(self.chk_on_overview)

        self.chk_on_browser = QCheckBox(tr("dash_on_browser", "Exibir no Deck Browser (Abaixo dos Baralhos)"))
        self.chk_on_browser.setChecked(dash_cfg.get("show_on_deck_browser", True))
        place_layout.addWidget(self.chk_on_browser)

        self.chk_hide_native = QCheckBox(tr("dash_hide_native", "Ocultar barra nativa de mensagens do Anki"))
        self.chk_hide_native.setChecked(dash_cfg.get("hide_native_msg_box", False))
        place_layout.addWidget(self.chk_hide_native)

        h_col = QHBoxLayout()
        h_col.addWidget(QLabel(tr("dash_columns", "Quantidade de Colunas no Layout:")))
        self.spin_columns = QSpinBox()
        self.spin_columns.setRange(1, 4)
        self.spin_columns.setValue(dash_cfg.get("layout_columns", 3))
        h_col.addWidget(self.spin_columns)
        place_layout.addLayout(h_col)

        layout.addWidget(place_grp)
        layout.addStretch()
        return widget

    # 3. Pomodoro Tab
    def _build_pomodoro_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        pomo_cfg = get_module_config("pomodoro")

        self.chk_pomo_enabled = QCheckBox(tr("pomo_enable_chk", "Ativar Pomodoro Timer & Floating Action Button (FAB)"))
        self.chk_pomo_enabled.setChecked(pomo_cfg.get("enabled", True))
        layout.addWidget(self.chk_pomo_enabled)

        # Durations
        dur_grp = QGroupBox(tr("pomo_durations_grp", "Durações de Foco e Intervalo"))
        dur_layout = QHBoxLayout(dur_grp)

        dur_layout.addWidget(QLabel(tr("pomo_focus_min", "Foco (min):")))
        self.spin_work = FocusWheelSpinBox()
        self.spin_work.setRange(1, 120)
        self.spin_work.setValue(pomo_cfg.get("work_duration_minutes", 25))
        dur_layout.addWidget(self.spin_work)

        dur_layout.addWidget(QLabel(tr("pomo_short_break_min", "Pausa Curta (min):")))
        self.spin_short = FocusWheelSpinBox()
        self.spin_short.setRange(1, 60)
        self.spin_short.setValue(pomo_cfg.get("short_break_minutes", 5))
        dur_layout.addWidget(self.spin_short)

        dur_layout.addWidget(QLabel(tr("pomo_long_break_min", "Pausa Longa (min):")))
        self.spin_long = FocusWheelSpinBox()
        self.spin_long.setRange(1, 120)
        self.spin_long.setValue(pomo_cfg.get("long_break_minutes", 15))
        dur_layout.addWidget(self.spin_long)

        dur_layout.addWidget(QLabel(tr("pomo_rounds_to_long_break", "Rodadas até Pausa Longa:")))
        self.spin_long_interval = FocusWheelSpinBox()
        self.spin_long_interval.setRange(1, 20)
        self.spin_long_interval.setValue(pomo_cfg.get("long_break_interval", 4))
        dur_layout.addWidget(self.spin_long_interval)

        layout.addWidget(dur_grp)

        # Smart Flow
        flow_grp = QGroupBox(tr("pomo_flow_grp", "Mecânica Adaptada aos Cards"))
        flow_layout = QVBoxLayout(flow_grp)

        self.chk_soft_break = QCheckBox(tr("pomo_soft_break_chk", "Modo Soft Break (Avisa ao fim do tempo e abre o intervalo automaticamente após responder o card)"))
        self.chk_soft_break.setChecked(pomo_cfg.get("soft_break_mode", True))
        flow_layout.addWidget(self.chk_soft_break)

        self.chk_inactivity = QCheckBox(tr("pomo_inactivity_chk", "Pausa Automática por Inatividade (evita contagem se o usuário se afastar)"))
        self.chk_inactivity.setChecked(pomo_cfg.get("inactivity_detection", True))
        flow_layout.addWidget(self.chk_inactivity)

        h_inact = QHBoxLayout()
        h_inact.addWidget(QLabel(tr("pomo_inactivity_sec", "Tempo Limite de Inatividade (segundos):")))
        self.spin_inact = FocusWheelSpinBox()
        self.spin_inact.setRange(10, 600)
        self.spin_inact.setValue(pomo_cfg.get("inactivity_timeout_seconds", 60))
        h_inact.addWidget(self.spin_inact)
        flow_layout.addLayout(h_inact)

        self.chk_auto_pause = QCheckBox(tr("pomo_auto_pause_chk", "Pausa Automática ao sair do Reviewer (Browser, Add, etc.)"))
        self.chk_auto_pause.setChecked(pomo_cfg.get("auto_pause_outside_reviewer", True))
        flow_layout.addWidget(self.chk_auto_pause)

        self.chk_focus_loss = QCheckBox(tr("pomo_focus_loss_chk", "Pausar e alertar ao clicar fora do Anki (Anti-Distração / Perda de Foco)"))
        self.chk_focus_loss.setChecked(pomo_cfg.get("pause_on_focus_loss", True))
        flow_layout.addWidget(self.chk_focus_loss)

        self.chk_hide_cursor = QCheckBox(tr("pomo_hide_cursor_chk", "Ocultar cursor do mouse por inatividade durante o Modo Foco"))
        self.chk_hide_cursor.setChecked(pomo_cfg.get("auto_hide_cursor_in_focus", True))
        flow_layout.addWidget(self.chk_hide_cursor)

        layout.addWidget(flow_grp)

        # Smart Auto-Advance Group
        advance_grp = QGroupBox(tr("pomo_auto_advance_grp", "⏩ Passagem Automática de Cards (Modo Foco)"))
        adv_layout = QVBoxLayout(advance_grp)

        self.chk_auto_advance = QCheckBox(tr("pomo_auto_advance_chk", "Ativar Passagem Automática de Perguntas e Respostas durante o Foco"))
        self.chk_auto_advance.setChecked(pomo_cfg.get("auto_advance_enabled", False))
        adv_layout.addWidget(self.chk_auto_advance)

        h_q_timeout = QHBoxLayout()
        h_q_timeout.addWidget(QLabel(tr("pomo_auto_show_ans_sec", "Tempo Limite da Pergunta (segundos para ver resposta):")))
        self.spin_auto_show_answer = FocusWheelSpinBox()
        self.spin_auto_show_answer.setRange(3, 120)
        self.spin_auto_show_answer.setValue(pomo_cfg.get("auto_show_answer_seconds", 20))
        h_q_timeout.addWidget(self.spin_auto_show_answer)
        adv_layout.addLayout(h_q_timeout)

        h_a_timeout = QHBoxLayout()
        h_a_timeout.addWidget(QLabel(tr("pomo_auto_ans_again_sec", "Tempo da Resposta (segundos antes de marcar 'Errei' se a pergunta estourou):")))
        self.spin_auto_answer_again = FocusWheelSpinBox()
        self.spin_auto_answer_again.setRange(2, 60)
        self.spin_auto_answer_again.setValue(pomo_cfg.get("auto_answer_again_seconds", 8))
        h_a_timeout.addWidget(self.spin_auto_answer_again)
        adv_layout.addLayout(h_a_timeout)

        lbl_hint = QLabel(tr("pomo_auto_advance_hint", "ℹ️ Se o tempo da pergunta estourar, a resposta será avaliada automaticamente como 'Errei'. Se você revelar a pergunta manualmente, a resposta não será temporizada. Pausa automaticamente por inatividade."))
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("font-size: 11px; opacity: 0.85; padding-top: 4px;")
        adv_layout.addWidget(lbl_hint)

        layout.addWidget(advance_grp)

        # Sound & Notifications Group
        sound_grp = QGroupBox(tr("pomo_sound_grp", "🔔 Alertas Sonoros e Notificações de Alarme"))
        sound_layout = QVBoxLayout(sound_grp)

        self.chk_sound_enabled = QCheckBox(tr("pomo_sound_enable", "Tocar som ao terminar o Pomodoro / Intervalo"))
        self.chk_sound_enabled.setChecked(pomo_cfg.get("sound_notifications", True))
        sound_layout.addWidget(self.chk_sound_enabled)

        # 1. Focus End Sound
        h_snd_w = QHBoxLayout()
        h_snd_w.addWidget(QLabel(tr("pomo_sound_work", "Som ao Fim do Foco:")))
        self.combo_sound = FocusWheelComboBox()
        self.combo_sound.addItem(tr("snd_bell", "🔔 Sino / Chime Suave"), "bell")
        self.combo_sound.addItem(tr("snd_school_bell", "🏫 Sinal / Campainha Escolar"), "school_bell")
        self.combo_sound.addItem(tr("snd_analog_alarm", "⏰ Alarme de Relógio Analógico"), "analog_alarm")
        self.combo_sound.addItem(tr("snd_digital_alarm", "📟 Alarme de Relógio Digital (Bip-Bip)"), "digital_alarm")
        self.combo_sound.addItem(tr("snd_system", "🎵 Som Padrão do Sistema"), "system")
        self.combo_sound.addItem(tr("snd_custom", "📁 Arquivo Personalizado (MP3/WAV)..."), "custom")

        cur_sound = pomo_cfg.get("sound_preset", "bell")
        idx_s = self.combo_sound.findData(cur_sound)
        self.combo_sound.setCurrentIndex(idx_s if idx_s >= 0 else 0)
        self.combo_sound.currentIndexChanged.connect(self._on_sound_preset_changed)
        h_snd_w.addWidget(self.combo_sound)

        btn_test_w = QPushButton(tr("btn_test", "▶️ Testar"))
        btn_test_w.clicked.connect(self._test_pomo_sound)
        h_snd_w.addWidget(btn_test_w)
        sound_layout.addLayout(h_snd_w)

        # Custom Audio File Row (Work)
        self.custom_file_widget = QWidget()
        h_file = QHBoxLayout(self.custom_file_widget)
        h_file.setContentsMargins(0, 0, 0, 0)
        h_file.addWidget(QLabel(tr("snd_file_focus", "Arquivo (Foco):")))
        self.txt_custom_sound = QLineEdit()
        self.txt_custom_sound.setText(pomo_cfg.get("custom_sound_path", ""))
        self.txt_custom_sound.setPlaceholderText(tr("snd_placeholder", "Selecione um arquivo .mp3 ou .wav..."))
        h_file.addWidget(self.txt_custom_sound)
        btn_browse = QPushButton(tr("btn_browse", "📁 Procurar..."))
        btn_browse.clicked.connect(self._browse_custom_sound)
        h_file.addWidget(btn_browse)
        sound_layout.addWidget(self.custom_file_widget)

        # Volume Slider (Work)
        h_vol_w = QHBoxLayout()
        h_vol_w.addWidget(QLabel(tr("pomo_sound_vol_focus", "Volume (Foco):")))
        self.slider_volume_work = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_volume_work.setRange(0, 100)
        self.slider_volume_work.setValue(int(pomo_cfg.get("sound_volume", 100)))
        self.lbl_volume_work_val = QLabel(f"{self.slider_volume_work.value()}%")
        self.lbl_volume_work_val.setFixedWidth(40)
        self.slider_volume_work.valueChanged.connect(lambda v: self.lbl_volume_work_val.setText(f"{v}%"))
        h_vol_w.addWidget(self.slider_volume_work)
        h_vol_w.addWidget(self.lbl_volume_work_val)
        sound_layout.addLayout(h_vol_w)

        # 2. Break End Sound
        h_snd_b = QHBoxLayout()
        h_snd_b.addWidget(QLabel(tr("pomo_sound_break", "Som ao Fim do Intervalo:")))
        self.combo_sound_break = FocusWheelComboBox()
        self.combo_sound_break.addItem(tr("snd_school_bell", "🏫 Sinal / Campainha Escolar"), "school_bell")
        self.combo_sound_break.addItem(tr("snd_bell", "🔔 Sino / Chime Suave"), "bell")
        self.combo_sound_break.addItem(tr("snd_analog_alarm", "⏰ Alarme de Relógio Analógico"), "analog_alarm")
        self.combo_sound_break.addItem(tr("snd_digital_alarm", "📟 Alarme de Relógio Digital (Bip-Bip)"), "digital_alarm")
        self.combo_sound_break.addItem(tr("snd_system", "🎵 Som Padrão do Sistema"), "system")
        self.combo_sound_break.addItem(tr("snd_custom", "📁 Arquivo Personalizado (MP3/WAV)..."), "custom")

        cur_sound_b = pomo_cfg.get("break_sound_preset", "school_bell")
        idx_sb = self.combo_sound_break.findData(cur_sound_b)
        self.combo_sound_break.setCurrentIndex(idx_sb if idx_sb >= 0 else 0)
        self.combo_sound_break.currentIndexChanged.connect(self._on_sound_preset_changed)
        h_snd_b.addWidget(self.combo_sound_break)

        btn_test_b = QPushButton(tr("btn_test", "▶️ Testar"))
        btn_test_b.clicked.connect(self._test_pomo_break_sound)
        h_snd_b.addWidget(btn_test_b)
        sound_layout.addLayout(h_snd_b)

        # Custom Audio File Row (Break)
        self.custom_file_widget_break = QWidget()
        h_file_b = QHBoxLayout(self.custom_file_widget_break)
        h_file_b.setContentsMargins(0, 0, 0, 0)
        h_file_b.addWidget(QLabel(tr("snd_file_break", "Arquivo (Intervalo):")))
        self.txt_custom_break_sound = QLineEdit()
        self.txt_custom_break_sound.setText(pomo_cfg.get("custom_break_sound_path", ""))
        self.txt_custom_break_sound.setPlaceholderText(tr("snd_placeholder", "Selecione um arquivo .mp3 ou .wav..."))
        h_file_b.addWidget(self.txt_custom_break_sound)
        btn_browse_b = QPushButton(tr("btn_browse", "📁 Procurar..."))
        btn_browse_b.clicked.connect(self._browse_custom_break_sound)
        h_file_b.addWidget(btn_browse_b)
        sound_layout.addWidget(self.custom_file_widget_break)

        # Volume Slider (Break)
        h_vol_b = QHBoxLayout()
        h_vol_b.addWidget(QLabel(tr("pomo_sound_vol_break", "Volume (Intervalo):")))
        self.slider_volume_break = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_volume_break.setRange(0, 100)
        self.slider_volume_break.setValue(int(pomo_cfg.get("break_sound_volume", 100)))
        self.lbl_volume_break_val = QLabel(f"{self.slider_volume_break.value()}%")
        self.lbl_volume_break_val.setFixedWidth(40)
        self.slider_volume_break.valueChanged.connect(lambda v: self.lbl_volume_break_val.setText(f"{v}%"))
        h_vol_b.addWidget(self.slider_volume_break)
        h_vol_b.addWidget(self.lbl_volume_break_val)
        sound_layout.addLayout(h_vol_b)

        # 3. Alarm Sound (Focus Loss / Inactivity)
        h_snd_a = QHBoxLayout()
        h_snd_a.addWidget(QLabel(tr("pomo_sound_alarm", "Sinal de Alarme (Perda de Foco & Inatividade):")))
        self.combo_sound_alarm = FocusWheelComboBox()
        self.combo_sound_alarm.addItem(tr("snd_digital_alarm", "📟 Alarme de Relógio Digital (Bip-Bip)"), "digital_alarm")
        self.combo_sound_alarm.addItem(tr("snd_analog_alarm", "⏰ Alarme de Relógio Analógico"), "analog_alarm")
        self.combo_sound_alarm.addItem(tr("snd_school_bell", "🏫 Sinal / Campainha Escolar"), "school_bell")
        self.combo_sound_alarm.addItem(tr("snd_bell", "🔔 Sino / Chime Suave"), "bell")
        self.combo_sound_alarm.addItem(tr("snd_system", "🎵 Som Padrão do Sistema"), "system")
        self.combo_sound_alarm.addItem(tr("snd_custom", "📁 Arquivo Personalizado (MP3/WAV)..."), "custom")

        cur_sound_a = pomo_cfg.get("alarm_sound_preset", pomo_cfg.get("focus_loss_sound_preset", "digital_alarm"))
        idx_sa = self.combo_sound_alarm.findData(cur_sound_a)
        self.combo_sound_alarm.setCurrentIndex(idx_sa if idx_sa >= 0 else 0)
        self.combo_sound_alarm.currentIndexChanged.connect(self._on_sound_preset_changed)
        h_snd_a.addWidget(self.combo_sound_alarm)

        btn_test_a = QPushButton(tr("btn_test", "▶️ Testar"))
        btn_test_a.clicked.connect(self._test_pomo_alarm_sound)
        h_snd_a.addWidget(btn_test_a)
        sound_layout.addLayout(h_snd_a)

        # Custom Audio File Row (Alarm)
        self.custom_file_widget_alarm = QWidget()
        h_file_a = QHBoxLayout(self.custom_file_widget_alarm)
        h_file_a.setContentsMargins(0, 0, 0, 0)
        h_file_a.addWidget(QLabel(tr("snd_file_alarm", "Arquivo (Alarme):")))
        self.txt_custom_alarm_sound = QLineEdit()
        self.txt_custom_alarm_sound.setText(pomo_cfg.get("custom_alarm_sound_path", ""))
        self.txt_custom_alarm_sound.setPlaceholderText(tr("snd_placeholder", "Selecione um arquivo .mp3 ou .wav..."))
        h_file_a.addWidget(self.txt_custom_alarm_sound)
        btn_browse_a = QPushButton(tr("btn_browse", "📁 Procurar..."))
        btn_browse_a.clicked.connect(self._browse_custom_alarm_sound)
        h_file_a.addWidget(btn_browse_a)
        sound_layout.addWidget(self.custom_file_widget_alarm)

        # Volume Slider (Alarm)
        h_vol_a = QHBoxLayout()
        h_vol_a.addWidget(QLabel(tr("pomo_sound_vol_alarm", "Volume (Alarme):")))
        self.slider_volume_alarm = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_volume_alarm.setRange(0, 100)
        self.slider_volume_alarm.setValue(int(pomo_cfg.get("alarm_sound_volume", 100)))
        self.lbl_volume_alarm_val = QLabel(f"{self.slider_volume_alarm.value()}%")
        self.lbl_volume_alarm_val.setFixedWidth(40)
        self.slider_volume_alarm.valueChanged.connect(lambda v: self.lbl_volume_alarm_val.setText(f"{v}%"))
        h_vol_a.addWidget(self.slider_volume_alarm)
        h_vol_a.addWidget(self.lbl_volume_alarm_val)
        sound_layout.addLayout(h_vol_a)

        self._on_sound_preset_changed()
        layout.addWidget(sound_grp)

        layout.addStretch()
        return widget

    def _on_sound_preset_changed(self):
        is_custom_w = (self.combo_sound.currentData() == "custom")
        self.custom_file_widget.setVisible(is_custom_w)
        is_custom_b = (self.combo_sound_break.currentData() == "custom")
        self.custom_file_widget_break.setVisible(is_custom_b)
        is_custom_a = (self.combo_sound_alarm.currentData() == "custom")
        self.custom_file_widget_alarm.setVisible(is_custom_a)

    def _browse_custom_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o áudio para fim de foco",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_custom_sound.setText(file_path)

    def _browse_custom_break_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o áudio para fim de intervalo",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_custom_break_sound.setText(file_path)

    def _browse_custom_alarm_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o áudio para o sinal de alarme",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_custom_alarm_sound.setText(file_path)

    def _test_pomo_sound(self):
        sound_key = self.combo_sound.currentData()
        custom_path = self.txt_custom_sound.text().strip()
        vol = self.slider_volume_work.value()
        play_pomodoro_sound(sound_key, custom_path, event_type="work_end", volume=vol)

    def _test_pomo_break_sound(self):
        sound_key = self.combo_sound_break.currentData()
        custom_path = self.txt_custom_break_sound.text().strip()
        vol = self.slider_volume_break.value()
        play_pomodoro_sound(sound_key, custom_path, event_type="break_end", volume=vol)

    def _test_pomo_alarm_sound(self):
        sound_key = self.combo_sound_alarm.currentData()
        custom_path = self.txt_custom_alarm_sound.text().strip()
        vol = self.slider_volume_alarm.value()
        play_pomodoro_sound(sound_key, custom_path, event_type="focus_loss", volume=vol)

    # 4. Gamepad Tab
    def _build_gamepad_tab(self) -> QWidget:
        if GamepadConfigWidget and get_gamepad_manager:
            self.gamepad_widget = GamepadConfigWidget(get_gamepad_manager(), self)
            return self.gamepad_widget
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Módulo de Gamepad indisponível."))
        return w

    # 5. Priority Tab
    def _build_priority_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        prio_cfg = get_module_config("priority_sequencer")

        self.chk_random_tie = QCheckBox(tr("prio_random_tie", "Desempate Aleatório para baralhos com a mesma prioridade"))
        self.chk_random_tie.setChecked(prio_cfg.get("random_tie_breaker", True))
        layout.addWidget(self.chk_random_tie)

        self.chk_auto_reorder = QCheckBox(tr("prio_auto_reorder", "Reordenar novos cartões automaticamente ao sincronizar"))
        self.chk_auto_reorder.setChecked(prio_cfg.get("auto_reorder_on_sync", True))
        layout.addWidget(self.chk_auto_reorder)

        btn_tree = QPushButton(tr("prio_open_tree", "📂 Abrir Gerenciador de Árvore de Prioridades..."))
        btn_tree.clicked.connect(self._open_priority_tree)
        layout.addWidget(btn_tree)

        layout.addStretch()
        return widget

    def _open_priority_tree(self):
        diag = DeckPriorityManagerDialog(self)
        diag.exec()

    # 6. Integrations Tab
    def _build_integrations_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        anki_grp = QGroupBox(tr("integ_anki_grp", "AnkiConnect (Integração com Obsidian / Yomichan)"))
        anki_layout = QVBoxLayout(anki_grp)
        anki_layout.addWidget(QLabel(tr("integ_anki_port", "Servidor JSON-RPC integrado rodando na porta: <b>8765</b>")))
        anki_layout.addWidget(QLabel(tr("integ_anki_status", "Status: <b>Ativo e Sincronizado</b>")))
        layout.addWidget(anki_grp)

        mc_grp = QGroupBox(tr("integ_mc_grp", "Multiple Choice for Anki"))
        mc_layout = QVBoxLayout(mc_grp)
        mc_layout.addWidget(QLabel(tr("integ_mc_desc", "Tipo de Nota: <b>AllInOne (kprim, mc, sc)</b> incorporado.")))
        layout.addWidget(mc_grp)

        layout.addStretch()
        return widget

    def _save_all_settings(self):
        """Saves all modified settings and applies theme instantly."""
        # 0. General
        if hasattr(self, "combo_lang"):
            gen_cfg = get_module_config("general")
            gen_cfg["language"] = self.combo_lang.currentData()
            write_module_config("general", gen_cfg)
            set_language_override(gen_cfg["language"] if gen_cfg["language"] != "auto" else None)

        # 1. Themes
        theme_cfg = get_module_config("theme")
        theme_cfg["enabled"] = self.chk_theme_enabled.isChecked()
        selected_preset = self.combo_presets.currentData()
        theme_cfg["preset"] = selected_preset
        if selected_preset == "custom":
            custom_dict = {}
            for k, btn in self.color_buttons.items():
                custom_dict[k] = btn.color_hex
            theme_cfg["custom_overrides"] = custom_dict
        else:
            theme_cfg["custom_overrides"] = {}
        theme_cfg["answer_buttons"] = {
            "enabled": self.chk_ans_buttons.isChecked(),
            "again_color": self.btn_ans_again.color_hex,
            "hard_color": self.btn_ans_hard.color_hex,
            "good_color": self.btn_ans_good.color_hex,
            "easy_color": self.btn_ans_easy.color_hex,
            "button_scale": self.slider_theme_btn_scale.value() / 100.0,
        }
        write_module_config("theme", theme_cfg)

        # 2. Dashboard
        dash_cfg = get_module_config("dashboard")
        dash_cfg["enabled"] = self.chk_dash_enabled.isChecked()
        dash_cfg["show_daily_goals"] = self.chk_show_goals.isChecked()
        dash_cfg["show_deck_composition"] = self.chk_show_comp.isChecked()
        dash_cfg["show_today_progress"] = self.chk_show_today.isChecked()
        dash_cfg["show_remaining"] = self.chk_show_remaining.isChecked()
        dash_cfg["show_done_today"] = self.chk_show_done.isChecked()
        dash_cfg["show_on_overview"] = self.chk_on_overview.isChecked()
        dash_cfg["show_on_deck_browser"] = self.chk_on_browser.isChecked()
        dash_cfg["hide_native_msg_box"] = self.chk_hide_native.isChecked()
        dash_cfg["layout_columns"] = self.spin_columns.value()
        write_module_config("dashboard", dash_cfg)

        # 3. Pomodoro
        pomo_cfg = get_module_config("pomodoro")
        pomo_cfg["enabled"] = self.chk_pomo_enabled.isChecked()
        pomo_cfg["work_duration_minutes"] = self.spin_work.value()
        pomo_cfg["short_break_minutes"] = self.spin_short.value()
        pomo_cfg["long_break_minutes"] = self.spin_long.value()
        pomo_cfg["long_break_interval"] = self.spin_long_interval.value()
        pomo_cfg["soft_break_mode"] = self.chk_soft_break.isChecked()
        pomo_cfg["inactivity_detection"] = self.chk_inactivity.isChecked()
        pomo_cfg["inactivity_timeout_seconds"] = self.spin_inact.value()
        pomo_cfg["auto_pause_outside_reviewer"] = self.chk_auto_pause.isChecked()
        pomo_cfg["pause_on_focus_loss"] = self.chk_focus_loss.isChecked()
        pomo_cfg["auto_hide_cursor_in_focus"] = self.chk_hide_cursor.isChecked()
        pomo_cfg["auto_advance_enabled"] = self.chk_auto_advance.isChecked()
        pomo_cfg["auto_show_answer_seconds"] = self.spin_auto_show_answer.value()
        pomo_cfg["auto_answer_again_seconds"] = self.spin_auto_answer_again.value()
        pomo_cfg["sound_notifications"] = self.chk_sound_enabled.isChecked()
        pomo_cfg["sound_preset"] = self.combo_sound.currentData()
        pomo_cfg["sound_volume"] = self.slider_volume_work.value()
        pomo_cfg["custom_sound_path"] = self.txt_custom_sound.text().strip()
        pomo_cfg["break_sound_preset"] = self.combo_sound_break.currentData()
        pomo_cfg["break_sound_volume"] = self.slider_volume_break.value()
        pomo_cfg["custom_break_sound_path"] = self.txt_custom_break_sound.text().strip()
        pomo_cfg["alarm_sound_preset"] = self.combo_sound_alarm.currentData()
        pomo_cfg["alarm_sound_volume"] = self.slider_volume_alarm.value()
        pomo_cfg["custom_alarm_sound_path"] = self.txt_custom_alarm_sound.text().strip()
        write_module_config("pomodoro", pomo_cfg)

        # 4. Priority
        prio_cfg = get_module_config("priority_sequencer")
        prio_cfg["random_tie_breaker"] = self.chk_random_tie.isChecked()
        prio_cfg["auto_reorder_on_sync"] = self.chk_auto_reorder.isChecked()
        write_module_config("priority_sequencer", prio_cfg)

        # 5. Gamepad
        if hasattr(self, "gamepad_widget") and self.gamepad_widget:
            self.gamepad_widget.save_settings()

        # Apply Theme to Anki & Floating Action Button (FAB)
        apply_theme_to_anki()
        try:
            from ..pomodoro.hooks import get_native_pomodoro_fab
            fab = get_native_pomodoro_fab()
            if fab:
                fab.refresh_theme()
        except Exception:
            pass

        if tooltip:
            tooltip(tr("settings_saved_success", "Configurações salvas com sucesso!"), period=2000)

        # Deactivate dialog isolation
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.set_active_dialog(None)
        except Exception:
            pass
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.is_dialog_active = False
                disp.active_dialog_scroll = None
        except Exception:
            pass

        self.accept()

    def _wrap_tab_in_scroll(self, widget: QWidget) -> QWidget:
        """Wraps a tab widget in a frameless, transparent QScrollArea if not already scrollable."""
        if isinstance(widget, QScrollArea) or getattr(widget, "scroll_area", None) is not None:
            return widget
        try:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            if hasattr(QFrame, "Shape"):
                scroll.setFrameShape(QFrame.Shape.NoFrame)
            else:
                scroll.setFrameShape(getattr(QFrame, "NoFrame", 0))
            if hasattr(Qt, "ScrollBarPolicy"):
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(widget)
            scroll.scroll_area = scroll
            return scroll
        except Exception:
            return widget

    def _get_current_scroll_area(self) -> Optional[QScrollArea]:
        """Returns the active QScrollArea for the currently displayed tab."""
        if not hasattr(self, "tabs") or not self.tabs:
            return None
        cur_tab = self.tabs.currentWidget() if hasattr(self.tabs, "currentWidget") else None
        if not cur_tab:
            return None
        if isinstance(cur_tab, QScrollArea):
            return cur_tab
        if hasattr(cur_tab, "scroll_area") and cur_tab.scroll_area:
            return cur_tab.scroll_area
        if hasattr(cur_tab, "findChild"):
            sa = cur_tab.findChild(QScrollArea)
            if sa:
                return sa
        return None

    def _get_interactive_widgets_for_current_tab(self) -> list:
        """Collects all visible, enabled interactive widgets in the current tab in logical order."""
        if not hasattr(self, "tabs") or not self.tabs:
            return []
        cur_tab = self.tabs.currentWidget() if hasattr(self.tabs, "currentWidget") else None
        if not cur_tab:
            return []

        search_root = cur_tab
        if isinstance(cur_tab, QScrollArea) and hasattr(cur_tab, "widget") and cur_tab.widget():
            search_root = cur_tab.widget()
        elif hasattr(cur_tab, "scroll_area") and cur_tab.scroll_area and hasattr(cur_tab.scroll_area, "widget") and cur_tab.scroll_area.widget():
            search_root = cur_tab.scroll_area.widget()

        types = (QCheckBox, QPushButton, QComboBox, QSlider, QSpinBox, QLineEdit)
        widgets = []
        if hasattr(search_root, "findChildren"):
            try:
                candidates = search_root.findChildren(QWidget)
                for w in candidates:
                    if isinstance(w, types):
                        p = w.parentWidget() if hasattr(w, "parentWidget") else None
                        if p and isinstance(p, (QSpinBox, QComboBox)):
                            continue
                        is_vis = w.isVisible() if hasattr(w, "isVisible") else True
                        is_en = w.isEnabled() if hasattr(w, "isEnabled") else True
                        if is_vis and is_en:
                            widgets.append(w)
            except Exception:
                pass
        return widgets

    def _is_combobox_popup_open(self, combo) -> bool:
        """Checks if the combobox view / popup is currently open."""
        if not isinstance(combo, QComboBox):
            return False
        if getattr(self, "_active_open_combobox", None) == combo:
            return True
        try:
            view = combo.view() if hasattr(combo, "view") else None
            if view:
                if hasattr(view, "isVisible") and view.isVisible():
                    return True
                win = view.window() if hasattr(view, "window") else None
                if win and hasattr(win, "isVisible") and win.isVisible():
                    return True
        except Exception:
            pass
        return False

    def _set_gamepad_focus(self, target):
        """Focuses a widget via gamepad, updating the glowing cyan visual ring and auto-scrolling."""
        old = getattr(self, "_current_gamepad_widget", None)
        if old and old != target:
            try:
                old.setProperty("gamepadFocused", False)
                if hasattr(old, "style") and old.style():
                    old.style().unpolish(old)
                    old.style().polish(old)
                old.update()
            except Exception:
                pass

        self._current_gamepad_widget = target
        if target:
            try:
                target.setProperty("gamepadFocused", True)
                if hasattr(target, "style") and target.style():
                    target.style().unpolish(target)
                    target.style().polish(target)
                target.update()
                target.setFocus()
            except Exception:
                pass

            # Auto-scroll to ensure focused widget is visible
            scroll_area = self._get_current_scroll_area()
            if scroll_area and hasattr(scroll_area, "ensureWidgetVisible"):
                try:
                    scroll_area.ensureWidgetVisible(target, 50, 50)
                except Exception:
                    pass

    def _focus_tab_first_widget(self):
        """Focuses the first interactive widget of the currently active tab."""
        widgets = self._get_interactive_widgets_for_current_tab()
        if widgets:
            self._set_gamepad_focus(widgets[0])

    def _on_tab_changed(self, idx: int):
        """Handles tab switching, synchronizing active scroll area and initial gamepad focus."""
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.active_dialog_scroll = self._get_current_scroll_area()
        except Exception:
            pass
        self._focus_tab_first_widget()

    def handle_gamepad_button(self, btn: str) -> bool:
        """
        Handles gamepad input for accessible navigation and control within the settings dialog.
        """
        if not hasattr(self, "tabs") or not self.tabs:
            return False

        # 1. Tab switching: LB / RB
        if btn == "LB":
            count = self.tabs.count() if hasattr(self.tabs, "count") else 0
            if count > 0:
                cur = self.tabs.currentIndex() if hasattr(self.tabs, "currentIndex") else 0
                new_idx = (cur - 1) % count
                self.tabs.setCurrentIndex(new_idx)
                self._focus_tab_first_widget()
            return True

        if btn == "RB":
            count = self.tabs.count() if hasattr(self.tabs, "count") else 0
            if count > 0:
                cur = self.tabs.currentIndex() if hasattr(self.tabs, "currentIndex") else 0
                new_idx = (cur + 1) % count
                self.tabs.setCurrentIndex(new_idx)
                self._focus_tab_first_widget()
            return True

        # 2. Vertical Navigation: DPAD_UP / STICK_LS_UP & DPAD_DOWN / STICK_LS_DOWN
        if btn in ("DPAD_UP", "STICK_LS_UP", "LS_UP", "DPAD_DOWN", "STICK_LS_DOWN", "LS_DOWN"):
            cur_w = getattr(self, "_current_gamepad_widget", None)

            # If current widget is a QComboBox with popup open, vertical navigates combo items
            if cur_w and isinstance(cur_w, QComboBox) and self._is_combobox_popup_open(cur_w):
                c_idx = cur_w.currentIndex() if hasattr(cur_w, "currentIndex") else 0
                total = cur_w.count() if hasattr(cur_w, "count") else len(getattr(cur_w, "_items", []))
                if btn in ("DPAD_UP", "STICK_LS_UP", "LS_UP"):
                    cur_w.setCurrentIndex(max(0, c_idx - 1))
                else:
                    cur_w.setCurrentIndex(min(max(0, total - 1), c_idx + 1))
                return True

            widgets = self._get_interactive_widgets_for_current_tab()
            if not widgets:
                return True

            if cur_w not in widgets:
                fw = self.focusWidget() if hasattr(self, "focusWidget") else None
                if fw in widgets:
                    cur_w = fw
                else:
                    for w in widgets:
                        if hasattr(w, "isAncestorOf") and w.isAncestorOf(fw):
                            cur_w = w
                            break

            if cur_w in widgets:
                idx = widgets.index(cur_w)
                if btn in ("DPAD_DOWN", "STICK_LS_DOWN", "LS_DOWN"):
                    next_idx = (idx + 1) % len(widgets)
                else:
                    next_idx = (idx - 1) % len(widgets)
            else:
                next_idx = 0 if btn in ("DPAD_DOWN", "STICK_LS_DOWN", "LS_DOWN") else (len(widgets) - 1)

            self._set_gamepad_focus(widgets[next_idx])
            return True

        # Ensure we have an active widget focused for interaction buttons
        cur_w = getattr(self, "_current_gamepad_widget", None)
        if not cur_w:
            widgets = self._get_interactive_widgets_for_current_tab()
            if widgets:
                cur_w = widgets[0]
                self._set_gamepad_focus(cur_w)
            else:
                if btn == "B":
                    self.reject()
                    return True
                return False

        # 3. Action / Activate: A
        if btn == "A":
            if isinstance(cur_w, QCheckBox):
                cur_w.setChecked(not cur_w.isChecked())
                if hasattr(cur_w, "clicked"):
                    try:
                        cur_w.clicked.emit(cur_w.isChecked())
                    except Exception:
                        pass
                return True

            if isinstance(cur_w, QPushButton):
                cur_w.click()
                return True

            if isinstance(cur_w, QComboBox):
                if self._is_combobox_popup_open(cur_w):
                    if hasattr(cur_w, "hidePopup"):
                        cur_w.hidePopup()
                    self._active_open_combobox = None
                else:
                    if hasattr(cur_w, "showPopup"):
                        cur_w.showPopup()
                    self._active_open_combobox = cur_w
                return True

            return True

        # 4. Horizontal Adjustment / Decrement: STICK_RS_LEFT / DPAD_LEFT
        if btn in ("STICK_RS_LEFT", "DPAD_LEFT", "RS_LEFT", "LS_LEFT", "STICK_LS_LEFT"):
            if isinstance(cur_w, QSlider):
                step = cur_w.singleStep() if hasattr(cur_w, "singleStep") else 1
                cur_w.setValue(cur_w.value() - (step or 1))
                return True

            if isinstance(cur_w, QSpinBox):
                if hasattr(cur_w, "stepDown"):
                    cur_w.stepDown()
                elif hasattr(cur_w, "setValue") and hasattr(cur_w, "value"):
                    cur_w.setValue(cur_w.value() - (cur_w.singleStep() if hasattr(cur_w, "singleStep") else 1))
                return True

            if isinstance(cur_w, QComboBox):
                if not self._is_combobox_popup_open(cur_w):
                    c_idx = cur_w.currentIndex() if hasattr(cur_w, "currentIndex") else 0
                    cur_w.setCurrentIndex(max(0, c_idx - 1))
                return True

            return True

        # 5. Horizontal Adjustment / Increment: STICK_RS_RIGHT / DPAD_RIGHT
        if btn in ("STICK_RS_RIGHT", "DPAD_RIGHT", "RS_RIGHT", "LS_RIGHT", "STICK_LS_RIGHT"):
            if isinstance(cur_w, QSlider):
                step = cur_w.singleStep() if hasattr(cur_w, "singleStep") else 1
                cur_w.setValue(cur_w.value() + (step or 1))
                return True

            if isinstance(cur_w, QSpinBox):
                if hasattr(cur_w, "stepUp"):
                    cur_w.stepUp()
                elif hasattr(cur_w, "setValue") and hasattr(cur_w, "value"):
                    cur_w.setValue(cur_w.value() + (cur_w.singleStep() if hasattr(cur_w, "singleStep") else 1))
                return True

            if isinstance(cur_w, QComboBox):
                if not self._is_combobox_popup_open(cur_w):
                    c_idx = cur_w.currentIndex() if hasattr(cur_w, "currentIndex") else 0
                    total = cur_w.count() if hasattr(cur_w, "count") else len(getattr(cur_w, "_items", []))
                    cur_w.setCurrentIndex(min(max(0, total - 1), c_idx + 1))
                return True

            return True

        # 6. Back / Cancel: B
        if btn == "B":
            # If a combobox popup is open or widget in sub-selection: close it and keep dialog open
            if getattr(self, "_active_open_combobox", None):
                combo = self._active_open_combobox
                if hasattr(combo, "hidePopup"):
                    combo.hidePopup()
                self._active_open_combobox = None
                return True

            if isinstance(cur_w, QComboBox) and self._is_combobox_popup_open(cur_w):
                if hasattr(cur_w, "hidePopup"):
                    cur_w.hidePopup()
                self._active_open_combobox = None
                return True

            # If no widget in sub-selection, close dialog
            self.reject()
            return True

        return False

    def showEvent(self, event):
        super().showEvent(event)
        try:
            from ..theme_manager.engine import set_windows_titlebar_color
            if hasattr(self, "_current_theme_colors") and self._current_theme_colors:
                bg_pri = self._current_theme_colors.get("bg_primary", "#000000")
                if hasattr(self, "winId") and self.winId():
                    set_windows_titlebar_color(bg_pri, hwnd=int(self.winId()))
        except Exception:
            pass
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.set_active_dialog(self)
        except Exception:
            pass
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.is_dialog_active = True
                disp.active_dialog_scroll = self._get_current_scroll_area()
        except Exception:
            pass
        self._focus_tab_first_widget()

    def hideEvent(self, event):
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.set_active_dialog(None)
        except Exception:
            pass
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.is_dialog_active = False
                disp.active_dialog_scroll = None
        except Exception:
            pass
        super().hideEvent(event)

    def closeEvent(self, event):
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.set_active_dialog(None)
        except Exception:
            pass
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.is_dialog_active = False
                disp.active_dialog_scroll = None
        except Exception:
            pass
        super().closeEvent(event)

    def reject(self):
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.set_active_dialog(None)
        except Exception:
            pass
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.is_dialog_active = False
                disp.active_dialog_scroll = None
        except Exception:
            pass
        super().reject()
