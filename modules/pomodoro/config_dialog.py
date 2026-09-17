# -*- coding: utf-8 -*-
"""
Graphical Configuration Dialog for Pomodoro Timer & Fatigue Analytics.
Includes sound notifications with preset synthesized chimes and custom MP3/WAV selection.
"""

import os
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
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QMessageBox,
        QComboBox,
        QLineEdit,
        QFileDialog,
        QSlider,
    )
    from PyQt6.QtCore import Qt
    from aqt import mw
    from aqt.utils import tooltip
except ImportError:
    QDialog = object
    mw = None
    tooltip = None
    QSlider = object

from .timer_engine import PomodoroEngine
from .sounds import play_pomodoro_sound
try:
    from ...utils.config_manager import get_module_config, write_module_config
    from ...utils.ui_helpers import FocusWheelSlider
    from ...utils.i18n import tr
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config, write_module_config
        from utils.ui_helpers import FocusWheelSlider
        from utils.i18n import tr
    except ImportError:
        FocusWheelSlider = QSlider
        def tr(key, default=None, **kwargs):
            return default if default is not None else key


class PomodoroConfigDialog(QDialog):
    """Settings and analytics dialog for Pomodoro timer."""

    def __init__(self, engine: Optional[PomodoroEngine] = None, parent=None):
        super().__init__(parent or (mw if mw else None))
        self.engine = engine
        self.setWindowTitle("🍅 Pomodoro Timer & Análise de Fadiga")
        self.resize(640, 560)
        self.setMinimumSize(560, 500)

        self.config = get_module_config("pomodoro")
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        tabs = QTabWidget()

        # Tab 1: Configuração do Timer
        tab_timer = QWidget()
        layout_t = QVBoxLayout(tab_timer)
        layout_t.setSpacing(10)

        grp_durations = QGroupBox("Durações Padrão (Minutos)")
        v_dur = QVBoxLayout(grp_durations)

        # Work
        h_work = QHBoxLayout()
        h_work.addWidget(QLabel("Tempo de Foco (Trabalho):"))
        self.spin_work = QSpinBox()
        self.spin_work.setRange(1, 120)
        self.spin_work.setValue(int(self.config.get("work_duration_minutes", 25)))
        h_work.addWidget(self.spin_work)
        h_work.addWidget(QLabel("min"))
        h_work.addStretch()
        v_dur.addLayout(h_work)

        # Short Break
        h_short = QHBoxLayout()
        h_short.addWidget(QLabel("Pausa Curta (Intervalo):"))
        self.spin_short = QSpinBox()
        self.spin_short.setRange(1, 60)
        self.spin_short.setValue(int(self.config.get("short_break_minutes", 5)))
        h_short.addWidget(self.spin_short)
        h_short.addWidget(QLabel("min"))
        h_short.addStretch()
        v_dur.addLayout(h_short)

        # Long Break
        h_long = QHBoxLayout()
        h_long.addWidget(QLabel("Pausa Longa:"))
        self.spin_long = QSpinBox()
        self.spin_long.setRange(1, 90)
        self.spin_long.setValue(int(self.config.get("long_break_minutes", 15)))
        h_long.addWidget(self.spin_long)
        h_long.addWidget(QLabel("min"))
        h_long.addStretch()
        v_dur.addLayout(h_long)

        # Long Break Interval
        h_int = QHBoxLayout()
        h_int.addWidget(QLabel(tr("pomo_rounds_to_long_break", "Ciclos até Pausa Longa:")))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 20)
        self.spin_interval.setValue(int(self.config.get("long_break_interval", 4)))
        h_int.addWidget(self.spin_interval)
        h_int.addWidget(QLabel("pomodoros"))
        h_int.addStretch()
        v_dur.addLayout(h_int)

        layout_t.addWidget(grp_durations)

        # Smart Mechanics Group
        grp_smart = QGroupBox("Mecânica Adaptativa de Cards")
        v_smart = QVBoxLayout(grp_smart)

        self.chk_soft_break = QCheckBox(tr("pomo_soft_break_chk", "Modo 'Soft Break' (Avisa ao fim do tempo e abre o intervalo automaticamente após responder o card)"))
        self.chk_soft_break.setChecked(self.config.get("soft_break_mode", True))
        v_smart.addWidget(self.chk_soft_break)

        self.chk_auto_pause = QCheckBox("Pausa Automática fora do Reviewer (ao ir para Browser, Add, etc.)")
        self.chk_auto_pause.setChecked(self.config.get("auto_pause_outside_reviewer", True))
        v_smart.addWidget(self.chk_auto_pause)

        self.chk_focus_loss = QCheckBox("Pausar e alertar ao clicar fora do Anki (Anti-Distração / Perda de Foco)")
        self.chk_focus_loss.setChecked(self.config.get("pause_on_focus_loss", True))
        v_smart.addWidget(self.chk_focus_loss)

        self.chk_hide_cursor = QCheckBox("Ocultar cursor do mouse por inatividade durante o Modo Foco")
        self.chk_hide_cursor.setChecked(self.config.get("auto_hide_cursor_in_focus", True))
        v_smart.addWidget(self.chk_hide_cursor)

        h_inact = QHBoxLayout()
        h_inact.addWidget(QLabel("Detecção de Inatividade:"))
        self.spin_inactivity = QSpinBox()
        self.spin_inactivity.setRange(10, 600)
        self.spin_inactivity.setValue(int(self.config.get("inactivity_timeout_seconds", 60)))
        h_inact.addWidget(self.spin_inactivity)
        h_inact.addWidget(QLabel("segundos sem interação"))
        h_inact.addStretch()
        v_smart.addLayout(h_inact)

        # Smart Auto-Advance
        self.chk_auto_advance = QCheckBox(tr("pomo_auto_advance_chk", "Ativar Passagem Automática de Perguntas e Respostas durante o Foco"))
        self.chk_auto_advance.setChecked(self.config.get("auto_advance_enabled", False))
        v_smart.addWidget(self.chk_auto_advance)

        h_q_timeout = QHBoxLayout()
        h_q_timeout.addWidget(QLabel(tr("pomo_auto_show_ans_sec", "Tempo Limite da Pergunta (segundos):")))
        self.spin_auto_show_answer = QSpinBox()
        self.spin_auto_show_answer.setRange(3, 120)
        self.spin_auto_show_answer.setValue(int(self.config.get("auto_show_answer_seconds", 20)))
        h_q_timeout.addWidget(self.spin_auto_show_answer)
        h_q_timeout.addStretch()
        v_smart.addLayout(h_q_timeout)

        h_a_timeout = QHBoxLayout()
        h_a_timeout.addWidget(QLabel(tr("pomo_auto_ans_again_sec", "Tempo da Resposta (segundos antes de Errar):")))
        self.spin_auto_answer_again = QSpinBox()
        self.spin_auto_answer_again.setRange(2, 60)
        self.spin_auto_answer_again.setValue(int(self.config.get("auto_answer_again_seconds", 8)))
        h_a_timeout.addWidget(self.spin_auto_answer_again)
        h_a_timeout.addStretch()
        v_smart.addLayout(h_a_timeout)

        layout_t.addWidget(grp_smart)

        # Sounds & Alerts Group
        grp_sound = QGroupBox("🔔 Alertas Sonoros e Notificações")
        v_sound = QVBoxLayout(grp_sound)

        self.chk_sound = QCheckBox("Tocar som ao terminar o Pomodoro / Intervalo")
        self.chk_sound.setChecked(self.config.get("sound_notifications", True))
        v_sound.addWidget(self.chk_sound)

        # 1. Focus Sound
        h_sound_w = QHBoxLayout()
        h_sound_w.addWidget(QLabel("Som de Fim de Foco:"))
        self.combo_sound = QComboBox()
        self.combo_sound.addItem("🔔 Sino / Chime Suave", "bell")
        self.combo_sound.addItem("🏫 Sinal / Campainha Escolar", "school_bell")
        self.combo_sound.addItem("⏰ Alarme de Relógio Analógico", "analog_alarm")
        self.combo_sound.addItem("📟 Alarme de Relógio Digital (Bip-Bip)", "digital_alarm")
        self.combo_sound.addItem("🎵 Som Padrão do Sistema", "system")
        self.combo_sound.addItem("📁 Arquivo Personalizado (MP3/WAV)...", "custom")

        cur_sound = self.config.get("sound_preset", "bell")
        idx = self.combo_sound.findData(cur_sound)
        self.combo_sound.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_sound.currentIndexChanged.connect(self._on_sound_preset_changed)
        h_sound_w.addWidget(self.combo_sound)

        btn_test_sound = QPushButton("▶️ Testar")
        btn_test_sound.clicked.connect(self._test_current_sound)
        h_sound_w.addWidget(btn_test_sound)
        v_sound.addLayout(h_sound_w)

        # Custom Audio File Row (Work)
        self.custom_file_widget = QWidget()
        h_file = QHBoxLayout(self.custom_file_widget)
        h_file.setContentsMargins(0, 0, 0, 0)
        h_file.addWidget(QLabel("Arquivo (Foco):"))
        self.txt_custom_path = QLineEdit()
        self.txt_custom_path.setText(self.config.get("custom_sound_path", ""))
        self.txt_custom_path.setPlaceholderText("Selecione um arquivo .mp3 ou .wav...")
        h_file.addWidget(self.txt_custom_path)

        btn_browse = QPushButton("📁 Procurar...")
        btn_browse.clicked.connect(self._browse_custom_sound)
        h_file.addWidget(btn_browse)
        v_sound.addWidget(self.custom_file_widget)

        # Volume Slider (Work)
        h_vol_w = QHBoxLayout()
        h_vol_w.addWidget(QLabel("Volume (Foco):"))
        self.slider_volume_work = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_volume_work.setRange(0, 100)
        self.slider_volume_work.setValue(int(self.config.get("sound_volume", 100)))
        self.lbl_volume_work_val = QLabel(f"{self.slider_volume_work.value()}%")
        self.lbl_volume_work_val.setFixedWidth(40)
        self.slider_volume_work.valueChanged.connect(lambda v: self.lbl_volume_work_val.setText(f"{v}%"))
        h_vol_w.addWidget(self.slider_volume_work)
        h_vol_w.addWidget(self.lbl_volume_work_val)
        v_sound.addLayout(h_vol_w)

        # 2. Break Sound
        h_sound_b = QHBoxLayout()
        h_sound_b.addWidget(QLabel("Som de Fim de Intervalo:"))
        self.combo_sound_break = QComboBox()
        self.combo_sound_break.addItem("🏫 Sinal / Campainha Escolar", "school_bell")
        self.combo_sound_break.addItem("🔔 Sino / Chime Suave", "bell")
        self.combo_sound_break.addItem("⏰ Alarme de Relógio Analógico", "analog_alarm")
        self.combo_sound_break.addItem("📟 Alarme de Relógio Digital (Bip-Bip)", "digital_alarm")
        self.combo_sound_break.addItem("🎵 Som Padrão do Sistema", "system")
        self.combo_sound_break.addItem("📁 Arquivo Personalizado (MP3/WAV)...", "custom")

        cur_sound_b = self.config.get("break_sound_preset", "school_bell")
        idx_b = self.combo_sound_break.findData(cur_sound_b)
        self.combo_sound_break.setCurrentIndex(idx_b if idx_b >= 0 else 0)
        self.combo_sound_break.currentIndexChanged.connect(self._on_sound_preset_changed)
        h_sound_b.addWidget(self.combo_sound_break)

        btn_test_break = QPushButton("▶️ Testar")
        btn_test_break.clicked.connect(self._test_break_sound)
        h_sound_b.addWidget(btn_test_break)
        v_sound.addLayout(h_sound_b)

        # Custom Audio File Row (Break)
        self.custom_file_widget_break = QWidget()
        h_file_b = QHBoxLayout(self.custom_file_widget_break)
        h_file_b.setContentsMargins(0, 0, 0, 0)
        h_file_b.addWidget(QLabel("Arquivo (Intervalo):"))
        self.txt_custom_break_path = QLineEdit()
        self.txt_custom_break_path.setText(self.config.get("custom_break_sound_path", ""))
        self.txt_custom_break_path.setPlaceholderText("Selecione um arquivo .mp3 ou .wav...")
        h_file_b.addWidget(self.txt_custom_break_path)

        btn_browse_b = QPushButton("📁 Procurar...")
        btn_browse_b.clicked.connect(self._browse_custom_break_sound)
        h_file_b.addWidget(btn_browse_b)
        v_sound.addWidget(self.custom_file_widget_break)

        # Volume Slider (Break)
        h_vol_b = QHBoxLayout()
        h_vol_b.addWidget(QLabel("Volume (Intervalo):"))
        self.slider_volume_break = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_volume_break.setRange(0, 100)
        self.slider_volume_break.setValue(int(self.config.get("break_sound_volume", 100)))
        self.lbl_volume_break_val = QLabel(f"{self.slider_volume_break.value()}%")
        self.lbl_volume_break_val.setFixedWidth(40)
        self.slider_volume_break.valueChanged.connect(lambda v: self.lbl_volume_break_val.setText(f"{v}%"))
        h_vol_b.addWidget(self.slider_volume_break)
        h_vol_b.addWidget(self.lbl_volume_break_val)
        v_sound.addLayout(h_vol_b)

        # 3. Alarm Sound (Focus Loss / Inactivity)
        h_sound_a = QHBoxLayout()
        h_sound_a.addWidget(QLabel("Sinal de Alarme (Perda de Foco / Inatividade):"))
        self.combo_sound_alarm = QComboBox()
        self.combo_sound_alarm.addItem("📟 Alarme de Relógio Digital (Bip-Bip)", "digital_alarm")
        self.combo_sound_alarm.addItem("⏰ Alarme de Relógio Analógico", "analog_alarm")
        self.combo_sound_alarm.addItem("🏫 Sinal / Campainha Escolar", "school_bell")
        self.combo_sound_alarm.addItem("🔔 Sino / Chime Suave", "bell")
        self.combo_sound_alarm.addItem("🎵 Som Padrão do Sistema", "system")
        self.combo_sound_alarm.addItem("📁 Arquivo Personalizado (MP3/WAV)...", "custom")

        cur_sound_a = self.config.get("alarm_sound_preset", self.config.get("focus_loss_sound_preset", "digital_alarm"))
        idx_a = self.combo_sound_alarm.findData(cur_sound_a)
        self.combo_sound_alarm.setCurrentIndex(idx_a if idx_a >= 0 else 0)
        self.combo_sound_alarm.currentIndexChanged.connect(self._on_sound_preset_changed)
        h_sound_a.addWidget(self.combo_sound_alarm)

        btn_test_alarm = QPushButton("▶️ Testar")
        btn_test_alarm.clicked.connect(self._test_alarm_sound)
        h_sound_a.addWidget(btn_test_alarm)
        v_sound.addLayout(h_sound_a)

        # Custom Audio File Row (Alarm)
        self.custom_file_widget_alarm = QWidget()
        h_file_a = QHBoxLayout(self.custom_file_widget_alarm)
        h_file_a.setContentsMargins(0, 0, 0, 0)
        h_file_a.addWidget(QLabel("Arquivo (Alarme):"))
        self.txt_custom_alarm_path = QLineEdit()
        self.txt_custom_alarm_path.setText(self.config.get("custom_alarm_sound_path", ""))
        self.txt_custom_alarm_path.setPlaceholderText("Selecione um arquivo .mp3 ou .wav...")
        h_file_a.addWidget(self.txt_custom_alarm_path)

        btn_browse_a = QPushButton("📁 Procurar...")
        btn_browse_a.clicked.connect(self._browse_custom_alarm_sound)
        h_file_a.addWidget(btn_browse_a)
        v_sound.addWidget(self.custom_file_widget_alarm)

        # Volume Slider (Alarm)
        h_vol_a = QHBoxLayout()
        h_vol_a.addWidget(QLabel("Volume (Alarme):"))
        self.slider_volume_alarm = FocusWheelSlider(Qt.Orientation.Horizontal)
        self.slider_volume_alarm.setRange(0, 100)
        self.slider_volume_alarm.setValue(int(self.config.get("alarm_sound_volume", 100)))
        self.lbl_volume_alarm_val = QLabel(f"{self.slider_volume_alarm.value()}%")
        self.lbl_volume_alarm_val.setFixedWidth(40)
        self.slider_volume_alarm.valueChanged.connect(lambda v: self.lbl_volume_alarm_val.setText(f"{v}%"))
        h_vol_a.addWidget(self.slider_volume_alarm)
        h_vol_a.addWidget(self.lbl_volume_alarm_val)
        v_sound.addLayout(h_vol_a)

        self._on_sound_preset_changed()
        layout_t.addWidget(grp_sound)

        layout_t.addStretch()
        tabs.addTab(tab_timer, "Temporizador e Áudio")

        # Tab 2: Análise de Fadiga Cognitiva
        tab_analytics = QWidget()
        layout_a = QVBoxLayout(tab_analytics)
        layout_a.setSpacing(10)

        layout_a.addWidget(QLabel("<b>Desempenho por Ciclo & Detecção de Fadiga Cognitiva</b>"))

        self.lbl_fatigue_summary = QLabel("Carregando análise...")
        self.lbl_fatigue_summary.setWordWrap(True)
        self.lbl_fatigue_summary.setStyleSheet("background: rgba(0, 120, 215, 0.08); padding: 10px; border-radius: 8px;")
        layout_a.addWidget(self.lbl_fatigue_summary)

        self.table_cycles = QTableWidget()
        self.table_cycles.setColumnCount(5)
        self.table_cycles.setHorizontalHeaderLabels(["Ciclo", "Cards Revisados", "Ritmo Médio", "Retenção (%)", "Erros (Again)"])
        self.table_cycles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout_a.addWidget(self.table_cycles)

        self._populate_fatigue_table()

        tabs.addTab(tab_analytics, "Análise de Fadiga")

        main_layout.addWidget(tabs)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Salvar Configurações")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_settings)
        btn_bar.addWidget(self.btn_save)

        main_layout.addLayout(btn_bar)

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
            "Selecione o arquivo de áudio para fim de foco",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_custom_path.setText(file_path)

    def _browse_custom_break_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o arquivo de áudio para fim de intervalo",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_custom_break_path.setText(file_path)

    def _browse_custom_alarm_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o arquivo de áudio para o sinal de alarme",
            "",
            "Arquivos de Áudio (*.mp3 *.wav *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.txt_custom_alarm_path.setText(file_path)

    def _test_current_sound(self):
        sound_key = self.combo_sound.currentData()
        custom_path = self.txt_custom_path.text().strip()
        vol = self.slider_volume_work.value()
        play_pomodoro_sound(sound_key, custom_path, event_type="work_end", volume=vol)

    def _test_break_sound(self):
        sound_key = self.combo_sound_break.currentData()
        custom_path = self.txt_custom_break_path.text().strip()
        vol = self.slider_volume_break.value()
        play_pomodoro_sound(sound_key, custom_path, event_type="break_end", volume=vol)

    def _test_alarm_sound(self):
        sound_key = self.combo_sound_alarm.currentData()
        custom_path = self.txt_custom_alarm_path.text().strip()
        vol = self.slider_volume_alarm.value()
        play_pomodoro_sound(sound_key, custom_path, event_type="focus_loss", volume=vol)

    def _populate_fatigue_table(self):
        if not self.engine:
            self.lbl_fatigue_summary.setText("Nenhum ciclo concluído na sessão atual.")
            return

        cycles = self.engine.fatigue_tracker.cycles_history
        if not cycles:
            self.lbl_fatigue_summary.setText("Nenhum ciclo concluído ainda nesta sessão.")
            return

        advice = self.engine.fatigue_tracker.get_fatigue_advice()
        self.lbl_fatigue_summary.setText(f"<b>Diagnóstico de Fadiga:</b> {advice.get('message', 'Ritmo ideal de estudo.')}")

        self.table_cycles.setRowCount(len(cycles))
        for row, c in enumerate(cycles):
            self.table_cycles.setItem(row, 0, QTableWidgetItem(f"#{c.cycle_index} ({c.phase_type})"))
            self.table_cycles.setItem(row, 1, QTableWidgetItem(str(c.cards_reviewed)))
            self.table_cycles.setItem(row, 2, QTableWidgetItem(f"{c.speed_cards_per_minute:.1f} c/min"))
            self.table_cycles.setItem(row, 3, QTableWidgetItem(f"{c.retention_pct:.1f}%"))
            self.table_cycles.setItem(row, 4, QTableWidgetItem(str(c.again_count)))

    def _save_settings(self):
        self.config["work_duration_minutes"] = self.spin_work.value()
        self.config["short_break_minutes"] = self.spin_short.value()
        self.config["long_break_minutes"] = self.spin_long.value()
        self.config["long_break_interval"] = self.spin_interval.value()
        self.config["soft_break_mode"] = self.chk_soft_break.isChecked()
        self.config["auto_pause_outside_reviewer"] = self.chk_auto_pause.isChecked()
        self.config["pause_on_focus_loss"] = self.chk_focus_loss.isChecked()
        self.config["auto_hide_cursor_in_focus"] = self.chk_hide_cursor.isChecked()
        self.config["auto_advance_enabled"] = self.chk_auto_advance.isChecked()
        self.config["auto_show_answer_seconds"] = self.spin_auto_show_answer.value()
        self.config["auto_answer_again_seconds"] = self.spin_auto_answer_again.value()
        self.config["inactivity_timeout_seconds"] = self.spin_inactivity.value()
        self.config["sound_notifications"] = self.chk_sound.isChecked()
        self.config["sound_preset"] = self.combo_sound.currentData()
        self.config["sound_volume"] = self.slider_volume_work.value()
        self.config["custom_sound_path"] = self.txt_custom_path.text().strip()
        self.config["break_sound_preset"] = self.combo_sound_break.currentData()
        self.config["break_sound_volume"] = self.slider_volume_break.value()
        self.config["custom_break_sound_path"] = self.txt_custom_break_path.text().strip()
        self.config["alarm_sound_preset"] = self.combo_sound_alarm.currentData()
        self.config["alarm_sound_volume"] = self.slider_volume_alarm.value()
        self.config["custom_alarm_sound_path"] = self.txt_custom_alarm_path.text().strip()

        write_module_config("pomodoro", self.config)

        if tooltip:
            tooltip("Configurações do Pomodoro salvas com sucesso!")
        self.accept()
