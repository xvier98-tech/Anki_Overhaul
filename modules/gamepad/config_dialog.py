# -*- coding: utf-8 -*-
"""
Configuration UI for Gamepad Module.
Provides real-time connection status, interactive listening mode for key binding,
deadzone & scroll sensitivity calibration sliders, and preset management.
"""

from typing import Dict, List, Optional
try:
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QSlider,
        QGroupBox,
        QComboBox,
        QScrollArea,
        QFrame,
        QCheckBox,
        QLineEdit,
        QFileDialog,
    )
    from PyQt6.QtCore import Qt, QEvent, pyqtSignal
    from PyQt6.QtGui import QFont, QColor
    from aqt import mw
    from aqt.utils import tooltip
except ImportError:
    class _MockUIMeta(type):
        def __getattr__(cls, name):
            return _MockUI()

    class _MockUI(metaclass=_MockUIMeta):
        def __init__(self, *args, **kwargs):
            self._min_h = 0
            self._def_s = 38
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return _MockUI()
        def __or__(self, other):
            return self
        def __ror__(self, other):
            return self
        def setMinimumHeight(self, h):
            self._min_h = h
        def minimumHeight(self):
            return self._min_h
        def verticalHeader(self):
            return self
        def horizontalHeader(self):
            return self
        def setDefaultSectionSize(self, s):
            self._def_s = s
        def defaultSectionSize(self):
            return self._def_s
        def setVisible(self, v): pass
        def setSectionResizeMode(self, *a): pass
        def setColumnWidth(self, *a): pass
        def setSelectionBehavior(self, *a): pass
        def addWidget(self, *a): pass
        def addLayout(self, *a): pass
        def addStretch(self, *a): pass
        def setContentsMargins(self, *a): pass
        def setSpacing(self, *a): pass
        def setRowCount(self, *a): pass
        def setColumnCount(self, *a): pass
        def setHorizontalHeaderLabels(self, *a): pass
        def setItem(self, *a): pass
        def setCellWidget(self, *a): pass
        def setStyleSheet(self, *a): pass
        def setWidget(self, *a): pass
        def setWidgetResizable(self, *a): pass
        def setText(self, *a): pass
        def text(self): return ""
        def setChecked(self, *a): pass
        def isChecked(self): return False
        def setValue(self, *a): pass
        def value(self): return 0
        def setRange(self, *a): pass
        def setToolTip(self, *a): pass
        def addItem(self, *a): pass
        def findData(self, *a): return 0
        def setCurrentIndex(self, *a): pass
        def currentData(self): return ""
        def connect(self, *a): pass
        def installEventFilter(self, *a): pass
        def removeEventFilter(self, *a): pass
        def setFixedSize(self, *a): pass
        def cellWidget(self, *a): return self
        def instance(self): return self

    QApplication = _MockUI
    QWidget = _MockUI
    QDialog = _MockUI
    QVBoxLayout = _MockUI
    QHBoxLayout = _MockUI
    QLabel = _MockUI
    QPushButton = _MockUI
    QTableWidget = _MockUI
    QTableWidgetItem = _MockUI
    QHeaderView = _MockUI
    QSlider = _MockUI
    QGroupBox = _MockUI
    QComboBox = _MockUI
    QScrollArea = _MockUI
    QFrame = _MockUI
    QCheckBox = _MockUI
    QLineEdit = _MockUI
    QFileDialog = _MockUI
    Qt = _MockUI()
    QEvent = _MockUI
    mw = None
    tooltip = None
from .actions import ACTION_DEFINITIONS, get_default_bindings, qt_key_event_to_string
from .input_manager import GamepadInputManager
from .visualizer import GamepadTesterWidget
from .sounds import play_gamepad_sound
try:
    from ...utils.config_manager import get_module_config, write_module_config
    from ...utils.ui_helpers import FocusWheelSlider, FocusWheelComboBox
    from ...utils.i18n import tr
    from ..theme_manager.presets import get_active_theme_colors
    from ..theme_manager.engine import is_light_color
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config, write_module_config
        from utils.ui_helpers import FocusWheelSlider, FocusWheelComboBox
        from utils.i18n import tr
        from modules.theme_manager.presets import get_active_theme_colors
        from modules.theme_manager.engine import is_light_color
    except ImportError:
        FocusWheelSlider = QSlider
        FocusWheelComboBox = QComboBox
        def tr(key, default=None, **kwargs):
            return default if default is not None else key
        def get_active_theme_colors(c): return {}
        def is_light_color(c): return False


class ShortcutsCellWidget(QWidget):
    """
    Renders an unlimited horizontal badge container of assigned shortcuts (Gamepad, Sticks, and Keyboard)
    with individual remove buttons [✕] and an [+ Adicionar] trigger button.
    """

    def __init__(
        self,
        action_id: str,
        triggers: List[str],
        is_listening: bool,
        on_add_clicked,
        on_remove_clicked,
        parent=None,
    ):
        super().__init__(parent)
        self.action_id = action_id
        self.triggers = triggers
        self.is_listening = is_listening
        self.on_add_clicked = on_add_clicked
        self.on_remove_clicked = on_remove_clicked
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        theme_cfg = get_module_config("theme")
        colors = get_active_theme_colors(theme_cfg)
        is_light = is_light_color(colors.get("bg_primary", "#000000"))

        # 1. Badges for each assigned trigger
        for trigger in self.triggers:
            badge = QFrame()
            b_layout = QHBoxLayout(badge)
            b_layout.setContentsMargins(6, 2, 4, 2)
            b_layout.setSpacing(4)

            # Keyboard shortcut
            if trigger.startswith("KEY:"):
                key_name = trigger[4:]
                disp_text = f"⌨️ {key_name}"
                if is_light:
                    badge.setStyleSheet("""
                        QFrame {
                            background: rgba(79, 70, 229, 0.12);
                            border: 1px solid rgba(79, 70, 229, 0.40);
                            border-radius: 4px;
                        }
                    """)
                    lbl = QLabel(disp_text)
                    lbl.setStyleSheet("color: #4338ca; font-weight: bold; font-size: 11px;")
                else:
                    badge.setStyleSheet("""
                        QFrame {
                            background: rgba(99, 102, 241, 0.22);
                            border: 1px solid rgba(129, 140, 248, 0.55);
                            border-radius: 4px;
                        }
                    """)
                    lbl = QLabel(disp_text)
                    lbl.setStyleSheet("color: #c7d2fe; font-weight: bold; font-size: 11px;")

            # Analog stick gestures (LS / RS)
            elif trigger.startswith("LS_") or trigger.startswith("RS_"):
                stick_map = {
                    "LS_UP": "LS Cima", "LS_DOWN": "LS Baixo", "LS_LEFT": "LS Esq", "LS_RIGHT": "LS Dir",
                    "RS_UP": "RS Cima", "RS_DOWN": "RS Baixo", "RS_LEFT": "RS Esq", "RS_RIGHT": "RS Dir",
                }
                s_name = stick_map.get(trigger, trigger)
                disp_text = f"🕹️ {s_name}"
                if is_light:
                    badge.setStyleSheet("""
                        QFrame {
                            background: rgba(2, 132, 199, 0.12);
                            border: 1px solid rgba(2, 132, 199, 0.40);
                            border-radius: 4px;
                        }
                    """)
                    lbl = QLabel(disp_text)
                    lbl.setStyleSheet("color: #0369a1; font-weight: bold; font-size: 11px;")
                else:
                    badge.setStyleSheet("""
                        QFrame {
                            background: rgba(14, 165, 233, 0.22);
                            border: 1px solid rgba(56, 189, 248, 0.55);
                            border-radius: 4px;
                        }
                    """)
                    lbl = QLabel(disp_text)
                    lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")

            # Standard Gamepad button
            else:
                disp_text = f"🎮 {trigger}"
                if is_light:
                    badge.setStyleSheet("""
                        QFrame {
                            background: rgba(15, 118, 110, 0.12);
                            border: 1px solid rgba(15, 118, 110, 0.40);
                            border-radius: 4px;
                        }
                    """)
                    lbl = QLabel(disp_text)
                    lbl.setStyleSheet("color: #0f766e; font-weight: bold; font-size: 11px;")
                else:
                    badge.setStyleSheet("""
                        QFrame {
                            background: rgba(56, 189, 248, 0.16);
                            border: 1px solid rgba(56, 189, 248, 0.45);
                            border-radius: 4px;
                        }
                    """)
                    lbl = QLabel(disp_text)
                    lbl.setStyleSheet("color: #7dd3fc; font-weight: bold; font-size: 11px;")

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(16, 16)
            btn_del.setToolTip(f"Remover atalho {trigger}")
            btn_del_color = "#475569" if is_light else "#94a3b8"
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {btn_del_color};
                    font-weight: bold;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    color: #ef4444;
                }}
            """)
            btn_del.clicked.connect(lambda _, t=trigger: self.on_remove_clicked(self.action_id, t))

            b_layout.addWidget(lbl)
            b_layout.addWidget(btn_del)
            layout.addWidget(badge)

        # 2. Add / Listening Button
        btn_add = QPushButton()
        if self.is_listening:
            btn_add.setText(tr("gp_btn_press", "🟡 Pressione botão, stick ou tecla..."))
            btn_add.setStyleSheet("""
                QPushButton {
                    background: #eab308;
                    color: #000000;
                    font-weight: bold;
                    border-radius: 4px;
                    padding: 3px 12px;
                    font-size: 11px;
                }
            """)
        else:
            btn_add.setText(tr("gp_btn_add", "+ Adicionar"))
            if is_light:
                btn_add.setStyleSheet("""
                    QPushButton {
                        background: rgba(100, 116, 139, 0.12);
                        border: 1px dashed #64748b;
                        color: #334155;
                        font-weight: 600;
                        border-radius: 4px;
                        padding: 3px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        border-color: #0284c7;
                        color: #0284c7;
                    }
                """)
            else:
                btn_add.setStyleSheet("""
                    QPushButton {
                        background: rgba(148, 163, 184, 0.12);
                        border: 1px dashed #64748b;
                        color: #94a3b8;
                        border-radius: 4px;
                        padding: 3px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        border-color: #38bdf8;
                        color: #38bdf8;
                    }
                """)

        btn_add.clicked.connect(lambda: self.on_add_clicked(self.action_id))
        layout.addWidget(btn_add)
        layout.addStretch()


class GamepadConfigWidget(QWidget):
    """
    Gamepad Settings & Keybinding management widget.
    Can be used as a tab in ObsidianSuiteHubDialog or embedded in a QDialog.
    """

    def __init__(self, input_manager: GamepadInputManager, parent=None):
        super().__init__(parent)
        self.input_manager = input_manager
        self.config = get_module_config("gamepad")
        self.bindings: Dict[str, List[str]] = dict(self.config.get("bindings", get_default_bindings()))

        self._listening_action: Optional[str] = None

        self._setup_ui()
        self._load_values()
        self._connect_signals()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area = scroll

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(14)

        # 1. Connection Status Banner
        self.grp_status = QGroupBox(tr("gp_status_grp", "🎮 Status do Dispositivo"))
        h_status = QHBoxLayout(self.grp_status)

        self.lbl_status_icon = QLabel("🔌")
        self.lbl_status_icon.setStyleSheet("font-size: 20px;")
        h_status.addWidget(self.lbl_status_icon)

        self.lbl_status_text = QLabel(tr("gp_status_checking", "Verificando controles conectados..."))
        self.lbl_status_text.setStyleSheet("font-size: 13px; font-weight: bold;")
        h_status.addWidget(self.lbl_status_text)
        h_status.addStretch()

        self.lbl_driver_info = QLabel("Driver: Windows XInput")
        self.lbl_driver_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        h_status.addWidget(self.lbl_driver_info)

        main_layout.addWidget(self.grp_status)

        # 2. Live Gamepad Tester Visualizer
        self.tester_widget = GamepadTesterWidget(self)
        main_layout.addWidget(self.tester_widget)

        # 3. Calibration & Sensitivity Group
        grp_calib = QGroupBox(tr("gp_calib_grp", "⚙️ Calibração de Analógicos e Gatilhos"))
        v_calib = QVBoxLayout(grp_calib)

        # Deadzone Slider
        h_dead = QHBoxLayout()
        h_dead.addWidget(QLabel(tr("gp_deadzone_lbl", "Zona Morta Radial (Deadzone):")))
        self.slider_deadzone = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_deadzone.setRange(5, 40)
        self.slider_deadzone.setValue(int(self.config.get("deadzone", 0.15) * 100))
        self.lbl_deadzone_val = QLabel(f"{self.slider_deadzone.value()}%")
        self.lbl_deadzone_val.setFixedWidth(40)
        self.slider_deadzone.valueChanged.connect(lambda v: self.lbl_deadzone_val.setText(f"{v}%"))
        h_dead.addWidget(self.slider_deadzone)
        h_dead.addWidget(self.lbl_deadzone_val)
        v_calib.addLayout(h_dead)

        # Scroll Sensitivity Slider
        h_scroll = QHBoxLayout()
        h_scroll.addWidget(QLabel(tr("gp_scroll_lbl", "Sensibilidade de Rolagem (Scroll):")))
        self.slider_scroll = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_scroll.setRange(10, 150)
        self.slider_scroll.setValue(int(self.config.get("scroll_sensitivity", 50)))
        self.lbl_scroll_val = QLabel(f"{self.slider_scroll.value()} px")
        self.lbl_scroll_val.setFixedWidth(50)
        self.slider_scroll.valueChanged.connect(lambda v: self.lbl_scroll_val.setText(f"{v} px"))
        h_scroll.addWidget(self.slider_scroll)
        h_scroll.addWidget(self.lbl_scroll_val)
        v_calib.addLayout(h_scroll)

        # Trigger Threshold Slider
        h_trig = QHBoxLayout()
        h_trig.addWidget(QLabel(tr("gp_trigger_lbl", "Limiar dos Gatilhos LT / RT:")))
        self.slider_trigger = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_trigger.setRange(20, 80)
        self.slider_trigger.setValue(int(self.config.get("trigger_threshold", 0.5) * 100))
        self.lbl_trig_val = QLabel(f"{self.slider_trigger.value()}%")
        self.lbl_trig_val.setFixedWidth(40)
        self.slider_trigger.valueChanged.connect(lambda v: self.lbl_trig_val.setText(f"{v}%"))
        h_trig.addWidget(self.slider_trigger)
        h_trig.addWidget(self.lbl_trig_val)
        v_calib.addLayout(h_trig)

        # Stick Selector for Scrolling
        h_stick = QHBoxLayout()
        h_stick.addWidget(QLabel(tr("gp_stick_scroll_lbl", "Analógico para Rolagem:")))
        self.combo_stick = FocusWheelComboBox()
        self.combo_stick.addItem(tr("gp_stick_right", "Analógico Direito (Recomendado)"), "right")
        self.combo_stick.addItem(tr("gp_stick_left", "Analógico Esquerdo"), "left")
        idx_stick = self.combo_stick.findData(self.config.get("continuous_scroll_stick", "right"))
        self.combo_stick.setCurrentIndex(idx_stick if idx_stick >= 0 else 0)
        h_stick.addWidget(self.combo_stick)
        h_stick.addStretch()
        v_calib.addLayout(h_stick)

        main_layout.addWidget(grp_calib)

        # 3.5. Sound Feedback Group
        grp_sound = QGroupBox(tr("gp_sound_grp", "🔊 Feedback Sonoro de Comandos"))
        v_sound = QVBoxLayout(grp_sound)

        self.chk_sound_enabled = QCheckBox(tr("gp_sound_enable", "Ativar feedback auditivo ao pressionar botões no controle"))
        self.chk_sound_enabled.setChecked(self.config.get("audio_feedback", True))
        v_sound.addWidget(self.chk_sound_enabled)

        h_snd = QHBoxLayout()
        h_snd.addWidget(QLabel(tr("gp_sound_preset_lbl", "Som dos Botões:")))
        self.combo_sound = FocusWheelComboBox()
        self.combo_sound.addItem(tr("gp_snd_click", "🎮 Clique Tátil Moderno"), "click")
        self.combo_sound.addItem(tr("gp_snd_pop", "💧 Pop Suave / Bubble"), "pop")
        self.combo_sound.addItem(tr("gp_snd_chime", "🔔 Chime / Sino Suave"), "chime")
        self.combo_sound.addItem(tr("gp_snd_beep", "📟 Bip Eletrônico Curto"), "beep")
        self.combo_sound.addItem(tr("snd_system", "🎵 Som Padrão do Sistema"), "system")
        self.combo_sound.addItem(tr("snd_custom", "📁 Arquivo Personalizado (MP3/WAV)..."), "custom")

        cur_snd = self.config.get("sound_preset", "click")
        idx_snd = self.combo_sound.findData(cur_snd)
        self.combo_sound.setCurrentIndex(idx_snd if idx_snd >= 0 else 0)
        self.combo_sound.currentIndexChanged.connect(self._on_sound_preset_changed)
        h_snd.addWidget(self.combo_sound)

        btn_test_snd = QPushButton(tr("btn_test", "▶️ Testar"))
        btn_test_snd.clicked.connect(self._test_gamepad_sound)
        h_snd.addWidget(btn_test_snd)
        v_sound.addLayout(h_snd)

        # Custom Audio File Row
        self.custom_file_widget = QWidget()
        h_cust = QHBoxLayout(self.custom_file_widget)
        h_cust.setContentsMargins(0, 0, 0, 0)
        h_cust.addWidget(QLabel(tr("snd_file_audio", "Arquivo de Áudio:")))
        self.txt_custom_sound = QLineEdit()
        self.txt_custom_sound.setText(self.config.get("custom_sound_path", ""))
        h_cust.addWidget(self.txt_custom_sound)

        btn_browse_snd = QPushButton(tr("btn_browse", "Procurar..."))
        btn_browse_snd.clicked.connect(self._browse_custom_sound)
        h_cust.addWidget(btn_browse_snd)
        v_sound.addWidget(self.custom_file_widget)

        # Volume Slider
        h_vol = QHBoxLayout()
        h_vol.addWidget(QLabel(tr("gp_sound_volume_lbl", "Volume do Feedback Sonoro:")))
        self.slider_sound_volume = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_sound_volume.setRange(0, 100)
        self.slider_sound_volume.setValue(int(self.config.get("sound_volume", 80)))
        self.lbl_sound_volume_val = QLabel(f"{self.slider_sound_volume.value()}%")
        self.lbl_sound_volume_val.setFixedWidth(40)
        self.slider_sound_volume.valueChanged.connect(lambda v: self.lbl_sound_volume_val.setText(f"{v}%"))
        h_vol.addWidget(self.slider_sound_volume)
        h_vol.addWidget(self.lbl_sound_volume_val)
        v_sound.addLayout(h_vol)

        self._on_sound_preset_changed()
        main_layout.addWidget(grp_sound)

        # 3.6. Visual Feedback Group
        grp_visual = QGroupBox(tr("gp_visual_grp", "✨ Feedback Visual dos Botões na Tela"))
        v_vis = QVBoxLayout(grp_visual)

        self.chk_release_mode = QCheckBox(tr("gp_release_mode_chk", "Acionar comandos ao soltar o botão (Release Mode - permite segurar para ver o botão afundar na tela)"))
        self.chk_release_mode.setChecked(self.config.get("trigger_on_release", True))
        v_vis.addWidget(self.chk_release_mode)

        h_int = QHBoxLayout()
        h_int.addWidget(QLabel(tr("gp_intensity_lbl", "Intensidade da Contração Visual:")))
        self.combo_intensity = FocusWheelComboBox()
        self.combo_intensity.addItem(tr("gp_int_subtle", "Sutil (Contração a 88%)"), "subtle")
        self.combo_intensity.addItem(tr("gp_int_moderate", "Moderada (Contração a 78% - Recomendado)"), "moderate")
        self.combo_intensity.addItem(tr("gp_int_intense", "Intensa (Contração a 68% com Halo Reforçado)"), "intense")
        idx_int = self.combo_intensity.findData(self.config.get("visual_feedback_intensity", "moderate"))
        self.combo_intensity.setCurrentIndex(idx_int if idx_int >= 0 else 1)
        h_int.addWidget(self.combo_intensity)
        h_int.addStretch()
        v_vis.addLayout(h_int)

        h_btn_sz = QHBoxLayout()
        h_btn_sz.addWidget(QLabel(tr("gp_btn_scale_lbl", "Tamanho Básico dos Botões de Resposta:")))
        self.slider_btn_scale = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_btn_scale.setRange(80, 160)
        self.slider_btn_scale.setValue(int(self.config.get("button_scale", 1.15) * 100))
        self.lbl_btn_scale_val = QLabel(f"{self.slider_btn_scale.value()}%")
        self.lbl_btn_scale_val.setFixedWidth(45)
        self.slider_btn_scale.valueChanged.connect(lambda v: self.lbl_btn_scale_val.setText(f"{v}%"))
        h_btn_sz.addWidget(self.slider_btn_scale)
        h_btn_sz.addWidget(self.lbl_btn_scale_val)
        v_vis.addLayout(h_btn_sz)

        main_layout.addWidget(grp_visual)

        # 4. Action Mapping Table
        grp_mappings = QGroupBox(tr("gp_mappings_grp", "🎯 Mapeamento de Botões do Controle"))
        v_map = QVBoxLayout(grp_mappings)

        self.table_bindings = QTableWidget()
        self.table_bindings.setColumnCount(3)
        self.table_bindings.setHorizontalHeaderLabels([
            tr("gp_tbl_action", "Ação do Anki"),
            tr("gp_tbl_triggers", "Atalhos Vinculados (Controle, Analógicos & Teclado)"),
            tr("gp_tbl_actions_btn", "Ações"),
        ])
        self.table_bindings.setColumnWidth(0, 260)
        self.table_bindings.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table_bindings.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_bindings.setColumnWidth(2, 90)
        self.table_bindings.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_bindings.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_bindings.setMinimumHeight(410)
        self.table_bindings.verticalHeader().setDefaultSectionSize(40)
        self.table_bindings.verticalHeader().setVisible(False)
        v_map.addWidget(self.table_bindings)

        # Table Control Buttons
        h_tbl_ctrl = QHBoxLayout()
        btn_reset_defaults = QPushButton(tr("gp_reset_defaults", "🔄 Restaurar Padrões (8BitDo / Xbox)"))
        btn_reset_defaults.clicked.connect(self._reset_to_defaults)
        h_tbl_ctrl.addWidget(btn_reset_defaults)

        btn_clear_all = QPushButton(tr("gp_clear_all", "🧹 Desvincular Todos"))
        btn_clear_all.clicked.connect(self._clear_all_bindings)
        h_tbl_ctrl.addWidget(btn_clear_all)
        h_tbl_ctrl.addStretch()
        v_map.addLayout(h_tbl_ctrl)

        main_layout.addWidget(grp_mappings)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        self._populate_table()

    def _connect_signals(self):
        self.input_manager.connection_changed.connect(self._on_connection_changed)
        self.input_manager.listening_captured.connect(self._on_listening_captured)
        self.input_manager.telemetry_updated.connect(self.tester_widget.update_telemetry)
        self._on_connection_changed(self.input_manager.is_connected(), self.input_manager.get_device_name())

    def _load_values(self):
        dead = self.slider_deadzone.value() / 100.0
        scroll = float(self.slider_scroll.value())
        trig = self.slider_trigger.value() / 100.0
        stick = self.combo_stick.currentData()

        self.input_manager.deadzone = dead
        self.input_manager.scroll_sensitivity = scroll
        self.input_manager.trigger_threshold = trig
        self.input_manager.continuous_scroll_stick = stick

    def _on_connection_changed(self, connected: bool, device_name: str):
        driver_name = self.input_manager.driver.get_driver_name() if self.input_manager.driver else "Universal"
        self.lbl_driver_info.setText(f"Driver: {driver_name}")
        if connected:
            self.lbl_status_icon.setText("🎮")
            self.lbl_status_text.setText(tr("gp_status_connected", "<span style='color: #4ade80;'>Conectado:</span> {name}", name=device_name))
            self.grp_status.setStyleSheet("QGroupBox { border-color: #22c55e; }")
        else:
            self.lbl_status_icon.setText("🔌")
            self.lbl_status_text.setText(tr("gp_status_none", "<span style='color: #f87171;'>Nenhum controle detectado</span> (Conecte via USB ou Bluetooth)"))
            self.grp_status.setStyleSheet("QGroupBox { border-color: #ef4444; }")

    def _populate_table(self):
        self.table_bindings.setRowCount(len(ACTION_DEFINITIONS))

        for row, (action_id, meta) in enumerate(ACTION_DEFINITIONS.items()):
            # 0. Action Name
            item_name = QTableWidgetItem(meta["name"])
            item_name.setToolTip(meta["description"])
            item_name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table_bindings.setItem(row, 0, item_name)

            triggers = self.bindings.get(action_id, [])
            is_listening = (self._listening_action == action_id)

            # 1. Multi-shortcut cell widget (Badges + [+ Adicionar])
            cell_shortcuts = ShortcutsCellWidget(
                action_id=action_id,
                triggers=triggers,
                is_listening=is_listening,
                on_add_clicked=self._toggle_listening,
                on_remove_clicked=self._remove_shortcut,
                parent=self.table_bindings,
            )
            self.table_bindings.setCellWidget(row, 1, cell_shortcuts)

            # 2. Clear action button
            btn_clear = QPushButton(tr("gp_btn_clear", "🧹 Limpar"))
            btn_clear.setToolTip(tr("gp_btn_clear_tip", "Remover todos os atalhos desta ação"))
            theme_cfg = get_module_config("theme")
            colors = get_active_theme_colors(theme_cfg)
            if is_light_color(colors.get("bg_primary", "#000000")):
                btn_clear.setStyleSheet("""
                    QPushButton {
                        background: rgba(220, 38, 38, 0.08);
                        border: 1px solid rgba(220, 38, 38, 0.40);
                        color: #b91c1c;
                        font-weight: 600;
                        border-radius: 4px;
                        padding: 3px 8px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: rgba(220, 38, 38, 0.20);
                        border-color: #b91c1c;
                        color: #991b1b;
                    }
                """)
            else:
                btn_clear.setStyleSheet("""
                    QPushButton {
                        background: rgba(239, 68, 68, 0.12);
                        border: 1px solid rgba(239, 68, 68, 0.35);
                        color: #f87171;
                        border-radius: 4px;
                        padding: 3px 8px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: rgba(239, 68, 68, 0.25);
                        border-color: #ef4444;
                        color: #ffffff;
                    }
                """)
            btn_clear.clicked.connect(lambda _, aid=action_id: self._clear_action_binding(aid))
            self.table_bindings.setCellWidget(row, 2, btn_clear)

    def _toggle_listening(self, action_id: str):
        if self._listening_action == action_id:
            self._cancel_listening()
        else:
            self._start_listening(action_id)

    def _start_listening(self, action_id: str):
        self._cancel_listening()
        self._listening_action = action_id
        self.input_manager.listening_mode = True

        app = QApplication.instance() if hasattr(QApplication, "instance") else None
        if app and hasattr(app, "installEventFilter"):
            try:
                app.installEventFilter(self)
            except Exception:
                pass

        self._populate_table()

    def _cancel_listening(self):
        if self.input_manager:
            self.input_manager.listening_mode = False

        app = QApplication.instance() if hasattr(QApplication, "instance") else None
        if app and hasattr(app, "removeEventFilter"):
            try:
                app.removeEventFilter(self)
            except Exception:
                pass

        if self._listening_action:
            self._listening_action = None
            self._populate_table()
        else:
            self._listening_action = None

    def eventFilter(self, obj, event):
        try:
            if self._listening_action and hasattr(event, "type") and hasattr(QEvent, "Type"):
                if event.type() == QEvent.Type.KeyPress:
                    key_name = qt_key_event_to_string(event)
                    if key_name == "Escape":
                        self._cancel_listening()
                        return True
                    if key_name:
                        self._on_listening_captured(f"KEY:{key_name}")
                        return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _on_listening_captured(self, captured_trigger: str):
        if not self._listening_action:
            return

        action_id = self._listening_action
        current_list = list(self.bindings.get(action_id, []))
        if captured_trigger not in current_list:
            current_list.append(captured_trigger)
        self.bindings[action_id] = current_list

        self._cancel_listening()
        self.save_settings()
        play_gamepad_sound("click")

        if tooltip:
            act_name = ACTION_DEFINITIONS.get(action_id, {}).get("name", action_id)
            tooltip(f"Atalho [{captured_trigger}] adicionado a '{act_name}'!", period=1500)

    def _remove_shortcut(self, action_id: str, trigger: str):
        self._cancel_listening()
        current_list = list(self.bindings.get(action_id, []))
        if trigger in current_list:
            current_list.remove(trigger)
            self.bindings[action_id] = current_list
            self.save_settings()
            self._populate_table()
            play_gamepad_sound("pop")

    def _clear_action_binding(self, action_id: str):
        self._cancel_listening()
        self.bindings[action_id] = []
        self.save_settings()
        self._populate_table()
        play_gamepad_sound("pop")

    def _reset_to_defaults(self):
        self._cancel_listening()
        self.bindings = get_default_bindings()
        self.save_settings()
        self._populate_table()
        if tooltip:
            tooltip("Mapeamento padrão restaurado!", period=1500)

    def _clear_all_bindings(self):
        self._cancel_listening()
        for k in self.bindings.keys():
            self.bindings[k] = []
        self.save_settings()
        self._populate_table()
        if tooltip:
            tooltip("Todos os atalhos foram desvinculados!", period=1500)

    def _on_sound_preset_changed(self):
        is_custom = (self.combo_sound.currentData() == "custom")
        self.custom_file_widget.setVisible(is_custom)

    def _browse_custom_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o Som para o Gamepad",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_custom_sound.setText(file_path)

    def _test_gamepad_sound(self):
        sound_key = self.combo_sound.currentData()
        custom_path = self.txt_custom_sound.text().strip()
        vol = self.slider_sound_volume.value()
        play_gamepad_sound(sound_key, custom_path, volume=vol)

    def save_settings(self):
        """Persists current calibration values, sound settings, and bindings to module configuration."""
        self.config["bindings"] = self.bindings
        self.config["deadzone"] = self.slider_deadzone.value() / 100.0
        self.config["scroll_sensitivity"] = float(self.slider_scroll.value())
        self.config["trigger_threshold"] = self.slider_trigger.value() / 100.0
        self.config["continuous_scroll_stick"] = self.combo_stick.currentData()
        self.config["audio_feedback"] = self.chk_sound_enabled.isChecked()
        self.config["sound_preset"] = self.combo_sound.currentData()
        self.config["sound_volume"] = self.slider_sound_volume.value()
        self.config["custom_sound_path"] = self.txt_custom_sound.text().strip()
        self.config["trigger_on_release"] = self.chk_release_mode.isChecked()
        self.config["visual_feedback_intensity"] = self.combo_intensity.currentData()
        self.config["button_scale"] = self.slider_btn_scale.value() / 100.0

        write_module_config("gamepad", self.config)

        # Apply to live input manager
        self.input_manager.deadzone = self.config["deadzone"]
        self.input_manager.scroll_sensitivity = self.config["scroll_sensitivity"]
        self.input_manager.trigger_threshold = self.config["trigger_threshold"]
        self.input_manager.continuous_scroll_stick = self.config["continuous_scroll_stick"]

        # Sync button_scale to theme config and refresh theme live
        try:
            theme_cfg = get_module_config("theme")
            if "answer_buttons" not in theme_cfg:
                theme_cfg["answer_buttons"] = {}
            theme_cfg["answer_buttons"]["button_scale"] = self.config["button_scale"]
            write_module_config("theme", theme_cfg)
            from ..theme_manager.engine import apply_theme_to_anki
            apply_theme_to_anki()
        except Exception:
            pass

        # Update dispatcher live with new bindings and settings
        try:
            from .hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.set_bindings(self.bindings)
                disp.trigger_on_release = self.config["trigger_on_release"]
                disp.visual_intensity = self.config["visual_feedback_intensity"]
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        try:
            from .hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.is_dialog_active = True
                disp.active_dialog_scroll = getattr(self, "scroll_area", None)
        except Exception:
            pass

    def hideEvent(self, event):
        try:
            from .hooks import get_gamepad_dispatcher
            disp = get_gamepad_dispatcher()
            if disp:
                disp.is_dialog_active = False
                disp.active_dialog_scroll = None
        except Exception:
            pass
        super().hideEvent(event)
