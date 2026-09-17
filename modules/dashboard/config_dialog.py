# -*- coding: utf-8 -*-
"""
Graphical Configuration Dialog for Modern Stats Dashboard.
Provides color pickers, opacity slider, layout and section visibility settings.
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
        QCheckBox,
        QComboBox,
        QSlider,
        QSpinBox,
        QPushButton,
        QGroupBox,
        QColorDialog,
        QScrollArea,
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor
    from aqt import mw
    from aqt.utils import tooltip
except ImportError:
    QDialog = object
    QPushButton = object
    QWidget = object
    mw = None
    tooltip = None

try:
    from ...utils.config_manager import get_module_config, write_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config, write_module_config


class ColorButton(QPushButton):
    """Button showing a color swatch that opens a QColorDialog."""

    def __init__(self, color_hex: str, on_changed=None, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.on_changed = on_changed
        self.setFixedHeight(28)
        self.setFixedWidth(70)
        self._update_swatch()
        self.clicked.connect(self._pick_color)

    def _update_swatch(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                border: 2px solid #a0aec0;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border: 2px solid #3182ce;
            }}
        """)

    def _pick_color(self):
        initial = QColor(self.color_hex)
        chosen = QColorDialog.getColor(initial, self.parent(), "Selecionar Cor")
        if chosen.isValid():
            self.color_hex = chosen.name()
            self._update_swatch()
            if self.on_changed:
                self.on_changed(self.color_hex)

    def get_color(self) -> str:
        return self.color_hex

    def set_color(self, color_hex: str):
        self.color_hex = color_hex
        self._update_swatch()


class DashboardConfigDialog(QDialog):
    """Modern Stats Dashboard settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações do Modern Stats Dashboard")
        self.resize(580, 520)
        self.setMinimumSize(520, 460)

        self.config = get_module_config("dashboard")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        tabs = QTabWidget()

        # Tab 1: Visibilidade e Comportamento
        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)
        layout_gen.setSpacing(10)

        grp_vis = QGroupBox("Painéis e Seções")
        v_vis = QVBoxLayout(grp_vis)

        self.chk_enabled = QCheckBox("Ativar Modern Stats Dashboard")
        self.chk_enabled.setChecked(self.config.get("enabled", True))
        v_vis.addWidget(self.chk_enabled)

        self.chk_overview = QCheckBox("Exibir ao clicar em um baralho (Tela de Overview - Per Deck)")
        self.chk_overview.setChecked(self.config.get("show_on_overview", True))
        v_vis.addWidget(self.chk_overview)

        self.chk_deck_browser = QCheckBox("Exibir na tela inicial de baralhos (Deck Browser - Global)")
        self.chk_deck_browser.setChecked(self.config.get("show_on_deck_browser", True))
        v_vis.addWidget(self.chk_deck_browser)

        self.chk_today = QCheckBox("Painel: Progresso de Hoje (Estudados, Tempo, Ritmo, Retenção)")
        self.chk_today.setChecked(self.config.get("show_today_progress", True))
        v_vis.addWidget(self.chk_today)

        self.chk_remaining = QCheckBox("Painel: Cartões Restantes (Novos, Aprendizado, Devidos, Previsão)")
        self.chk_remaining.setChecked(self.config.get("show_remaining", True))
        v_vis.addWidget(self.chk_remaining)

        self.chk_done = QCheckBox("Painel: Concluídos Hoje (Novos Aprendidos, Repetições, Maduros, Erros)")
        self.chk_done.setChecked(self.config.get("show_done_today", True))
        v_vis.addWidget(self.chk_done)

        self.chk_inc_new = QCheckBox("Incluir cartões novos na contagem total de 'Restantes'")
        self.chk_inc_new.setChecked(self.config.get("include_new_in_remaining_total", True))
        v_vis.addWidget(self.chk_inc_new)

        self.chk_hide_native = QCheckBox("Ocultar barra nativa de mensagens do Anki (evita redundância visual)")
        self.chk_hide_native.setChecked(self.config.get("hide_native_msg_box", False))
        v_vis.addWidget(self.chk_hide_native)

        layout_gen.addWidget(grp_vis)

        # Columns
        grp_layout = QGroupBox("Layout de Colunas")
        h_col = QHBoxLayout(grp_layout)
        h_col.addWidget(QLabel("Quantidade máxima de colunas:"))
        self.combo_cols = QComboBox()
        self.combo_cols.addItems(["1 Coluna", "2 Colunas", "3 Colunas"])
        cur_cols = self.config.get("layout_columns", 3)
        self.combo_cols.setCurrentIndex(min(2, max(0, cur_cols - 1)))
        h_col.addWidget(self.combo_cols)
        h_col.addStretch()
        layout_gen.addWidget(grp_layout)

        layout_gen.addStretch()
        tabs.addTab(tab_general, "Geral e Seções")

        # Tab 2: Cores e Transparência
        tab_theme = QWidget()
        layout_theme = QVBoxLayout(tab_theme)
        layout_theme.setSpacing(10)

        # Mode
        h_mode = QHBoxLayout()
        h_mode.addWidget(QLabel("<b>Modo de Tema:</b>"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Automático (Segue o Anki)", "Forçar Modo Claro", "Forçar Modo Escuro"])
        mode_str = self.config.get("theme_mode", "auto")
        mode_idx = 0 if mode_str == "auto" else (1 if mode_str == "light" else 2)
        self.combo_theme.setCurrentIndex(mode_idx)
        h_mode.addWidget(self.combo_theme)
        h_mode.addStretch()
        layout_theme.addLayout(h_mode)

        # Opacity slider
        grp_opacity = QGroupBox("Transparência dos Cards (Glassmorphism)")
        v_op = QVBoxLayout(grp_opacity)
        h_slider = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(40, 100)
        self.slider_opacity.setValue(self.config.get("card_opacity", 90))
        self.lbl_opacity_val = QLabel(f"{self.slider_opacity.value()}%")
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v}%"))
        h_slider.addWidget(self.slider_opacity)
        h_slider.addWidget(self.lbl_opacity_val)
        v_op.addLayout(h_slider)
        layout_theme.addWidget(grp_opacity)

        # Colors Palette
        custom = self.config.get("custom_colors", {})
        light = custom.get("light", {})
        dark = custom.get("dark", {})

        grp_colors = QGroupBox("Paleta de Cores Personalizada")
        grid_colors = QVBoxLayout(grp_colors)

        # Light mode row
        grid_colors.addWidget(QLabel("<b>Tema Claro:</b>"))
        h_cl = QHBoxLayout()
        h_cl.addWidget(QLabel("Fundo:"))
        self.btn_l_bg = ColorButton(light.get("card_bg", "#ffffff"))
        h_cl.addWidget(self.btn_l_bg)

        h_cl.addWidget(QLabel("Destaque:"))
        self.btn_l_acc = ColorButton(light.get("accent", "#0078d4"))
        h_cl.addWidget(self.btn_l_acc)

        h_cl.addWidget(QLabel("Texto:"))
        self.btn_l_txt = ColorButton(light.get("text_primary", "#2d3748"))
        h_cl.addWidget(self.btn_l_txt)

        h_cl.addWidget(QLabel("Borda:"))
        self.btn_l_bor = ColorButton(light.get("border", "#e2e8f0"))
        h_cl.addWidget(self.btn_l_bor)
        grid_colors.addLayout(h_cl)

        grid_colors.addSpacing(6)

        # Dark mode row
        grid_colors.addWidget(QLabel("<b>Tema Escuro:</b>"))
        h_cd = QHBoxLayout()
        h_cd.addWidget(QLabel("Fundo:"))
        self.btn_d_bg = ColorButton(dark.get("card_bg", "#2d3748"))
        h_cd.addWidget(self.btn_d_bg)

        h_cd.addWidget(QLabel("Destaque:"))
        self.btn_d_acc = ColorButton(dark.get("accent", "#63b3ed"))
        h_cd.addWidget(self.btn_d_acc)

        h_cd.addWidget(QLabel("Texto:"))
        self.btn_d_txt = ColorButton(dark.get("text_primary", "#f7fafc"))
        h_cd.addWidget(self.btn_d_txt)

        h_cd.addWidget(QLabel("Borda:"))
        self.btn_d_bor = ColorButton(dark.get("border", "#4a5568"))
        h_cd.addWidget(self.btn_d_bor)
        grid_colors.addLayout(h_cd)

        layout_theme.addWidget(grp_colors)
        layout_theme.addStretch()
        tabs.addTab(tab_theme, "Cores e Estilo")

        main_layout.addWidget(tabs)

        # Action Buttons
        btn_bar = QHBoxLayout()

        self.btn_restore = QPushButton("Restaurar Padrões")
        self.btn_restore.clicked.connect(self._restore_defaults)
        btn_bar.addWidget(self.btn_restore)

        btn_bar.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Salvar e Aplicar")
        self.btn_save.setDefault(True)
        self.btn_save.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_save.clicked.connect(self._save_and_apply)
        btn_bar.addWidget(self.btn_save)

        main_layout.addLayout(btn_bar)

    def _save_and_apply(self):
        modes = ["auto", "light", "dark"]
        theme_mode = modes[self.combo_theme.currentIndex()]

        new_config = {
            "enabled": self.chk_enabled.isChecked(),
            "show_on_overview": self.chk_overview.isChecked(),
            "show_on_deck_browser": self.chk_deck_browser.isChecked(),
            "show_today_progress": self.chk_today.isChecked(),
            "show_remaining": self.chk_remaining.isChecked(),
            "show_done_today": self.chk_done.isChecked(),
            "include_new_in_remaining_total": self.chk_inc_new.isChecked(),
            "hide_native_msg_box": self.chk_hide_native.isChecked(),
            "layout_columns": self.combo_cols.currentIndex() + 1,
            "theme_mode": theme_mode,
            "card_opacity": self.slider_opacity.value(),
            "custom_colors": {
                "light": {
                    "card_bg": self.btn_l_bg.get_color(),
                    "accent": self.btn_l_acc.get_color(),
                    "text_primary": self.btn_l_txt.get_color(),
                    "text_secondary": "#718096",
                    "border": self.btn_l_bor.get_color(),
                },
                "dark": {
                    "card_bg": self.btn_d_bg.get_color(),
                    "accent": self.btn_d_acc.get_color(),
                    "text_primary": self.btn_d_txt.get_color(),
                    "text_secondary": "#a0aec0",
                    "border": self.btn_d_bor.get_color(),
                },
            },
        }

        write_module_config("dashboard", new_config)

        if mw:
            mw.reset()
            if tooltip:
                tooltip("Configurações do Dashboard salvas com sucesso!")

        self.accept()

    def _restore_defaults(self):
        from ...utils.config_manager import DEFAULT_CONFIG
        default_dash = DEFAULT_CONFIG["dashboard"]
        self.chk_enabled.setChecked(default_dash["enabled"])
        self.chk_overview.setChecked(default_dash["show_on_overview"])
        self.chk_deck_browser.setChecked(default_dash["show_on_deck_browser"])
        self.chk_today.setChecked(default_dash["show_today_progress"])
        self.chk_remaining.setChecked(default_dash["show_remaining"])
        self.chk_done.setChecked(default_dash["show_done_today"])
        self.chk_inc_new.setChecked(default_dash["include_new_in_remaining_total"])
        self.chk_hide_native.setChecked(default_dash["hide_native_msg_box"])
        self.combo_cols.setCurrentIndex(default_dash["layout_columns"] - 1)
        self.combo_theme.setCurrentIndex(0)
        self.slider_opacity.setValue(default_dash["card_opacity"])

        l_def = default_dash["custom_colors"]["light"]
        self.btn_l_bg.set_color(l_def["card_bg"])
        self.btn_l_acc.set_color(l_def["accent"])
        self.btn_l_txt.set_color(l_def["text_primary"])
        self.btn_l_bor.set_color(l_def["border"])

        d_def = default_dash["custom_colors"]["dark"]
        self.btn_d_bg.set_color(d_def["card_bg"])
        self.btn_d_acc.set_color(d_def["accent"])
        self.btn_d_txt.set_color(d_def["text_primary"])
        self.btn_d_bor.set_color(d_def["border"])
