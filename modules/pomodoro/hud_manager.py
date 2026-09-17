# -*- coding: utf-8 -*-
"""
Floating Action Button (FAB) & Expanded HUD for Pomodoro in Reviewer.
Provides a modern floating pill / expandable card with countdown, ETA, and Rest Overlay.
"""

from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget,
        QHBoxLayout,
        QVBoxLayout,
        QLabel,
        QPushButton,
        QDialog,
        QFrame,
        QGraphicsDropShadowEffect,
    )
    from PyQt6.QtCore import Qt, QPoint, QEvent
    from PyQt6.QtGui import QColor, QFont, QCursor
    from aqt import mw
except ImportError:
    QWidget = object
    QDialog = object
    QFrame = object
    mw = None

from .timer_engine import PomodoroEngine, PomodoroState
try:
    from ...utils.config_manager import get_module_config
    from ...utils.i18n import tr
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config
        from utils.i18n import tr
    except ImportError:
        def tr(key, default=None, **kwargs):
            return default if default is not None else key


class RestOverlayDialog(QDialog):
    """
    Forced Rest Overlay displayed during short or long breaks.
    Encourages true cognitive rest with countdown, overtime tracking, +5min extension,
    and direct resume study option.
    """

    def __init__(self, engine: PomodoroEngine, parent=None):
        if QDialog is not object:
            super().__init__(parent or (mw if mw else None))
            self.setWindowTitle("Intervalo Pomodoro - Descanso Cognitivo")
            self.setFixedSize(540, 370)
            self.setModal(True)
            if hasattr(Qt, "WidgetAttribute"):
                self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        else:
            super().__init__()
        self.engine = engine

        self._selected_btn_idx: int = 1

        if QDialog is not object:
            self._setup_ui()
            self._update_gamepad_selection_styles()
        else:
            class _MockBtn:
                def __init__(self):
                    self.focused = False
                def setStyleSheet(self, s):
                    pass
                def setFocus(self):
                    self.focused = True
            self.btn_add_5m = _MockBtn()
            self.btn_resume = _MockBtn()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(32, 28, 32, 28)

        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111827, stop:1 #1f2937);
                border: 2px solid #374151;
                border-radius: 20px;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        self.icon_lbl = QLabel("☕")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 46px; font-family: 'Segoe UI Emoji';")
        layout.addWidget(self.icon_lbl)

        self.lbl_title = QLabel(tr("rest_title", "☕ Hora de Descansar a Mente!"))
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #60a5fa;")
        layout.addWidget(self.lbl_title)

        self.lbl_timer = QLabel(self.engine.get_formatted_time())
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timer.setStyleSheet("font-size: 46px; font-weight: 800; color: #4ade80; font-family: Consolas, monospace;")
        layout.addWidget(self.lbl_timer)

        self.lbl_desc = QLabel(tr("rest_desc", "Levante-se, tome uma água, alongue o corpo e descanse a visão."))
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("font-size: 13px; color: #9ca3af; margin-bottom: 4px;")
        layout.addWidget(self.lbl_desc)

        # Action Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # +5 min button
        self.btn_add_5m = QPushButton(tr("rest_btn_add_5m", "➕ +5 min no Intervalo"))
        self.btn_add_5m.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_5m.setStyleSheet("""
            QPushButton {
                background-color: rgba(56, 189, 248, 0.18);
                color: #38bdf8;
                border: 1.5px solid rgba(56, 189, 248, 0.45);
                border-radius: 12px;
                padding: 10px 18px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.35);
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.btn_add_5m.clicked.connect(self._add_5_minutes)
        btn_layout.addWidget(self.btn_add_5m)

        # Return to study button
        self.btn_resume = QPushButton(tr("rest_btn_resume", "🚀 Voltar a Estudar"))
        self.btn_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_resume.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #22c55e, stop:1 #16a34a);
                color: #ffffff;
                border: 1.5px solid #22c55e;
                border-radius: 12px;
                padding: 10px 22px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #16a34a;
                border-color: #4ade80;
            }
        """)
        self.btn_resume.clicked.connect(self._resume_work)
        btn_layout.addWidget(self.btn_resume)

        layout.addLayout(btn_layout)

    def _update_gamepad_selection_styles(self):
        """Highlights the selected button with border/glow and resets the other."""
        if not hasattr(self, "btn_add_5m") or not hasattr(self, "btn_resume"):
            return

        if self._selected_btn_idx == 0:
            # Highlight +5 min button
            self.btn_add_5m.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.40);
                    color: #ffffff;
                    border: 2.5px solid #38bdf8;
                    border-radius: 12px;
                    padding: 10px 18px;
                    font-weight: 800;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.55);
                    border-color: #7dd3fc;
                }
            """)
            self.btn_resume.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #15803d, stop:1 #14532d);
                    color: #9ca3af;
                    border: 1.5px solid #166534;
                    border-radius: 12px;
                    padding: 10px 22px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #16a34a;
                    color: #ffffff;
                    border-color: #22c55e;
                }
            """)
            if hasattr(self.btn_add_5m, "setFocus"):
                try:
                    self.btn_add_5m.setFocus()
                except Exception:
                    pass
        else:
            # Highlight Resume Study button (default)
            self.btn_add_5m.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.12);
                    color: #94a3b8;
                    border: 1.5px solid rgba(56, 189, 248, 0.30);
                    border-radius: 12px;
                    padding: 10px 18px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.25);
                    color: #38bdf8;
                    border-color: #38bdf8;
                }
            """)
            self.btn_resume.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #22c55e, stop:1 #16a34a);
                    color: #ffffff;
                    border: 2.5px solid #86efac;
                    border-radius: 12px;
                    padding: 10px 22px;
                    font-weight: 800;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #16a34a;
                    border-color: #bbf7d0;
                }
            """)
            if hasattr(self.btn_resume, "setFocus"):
                try:
                    self.btn_resume.setFocus()
                except Exception:
                    pass

    def handle_gamepad_button(self, btn: str) -> bool:
        """
        Processes gamepad navigation and selection when RestOverlayDialog is active.
        DPAD/Stick Left/Up: selects '+5 min' (idx 0).
        DPAD/Stick Right/Down: selects 'Voltar a Estudar' (idx 1).
        A: triggers selected button action.
        B: fast shortcut to resume work.
        """
        if btn in ("DPAD_LEFT", "STICK_LS_LEFT", "STICK_RS_LEFT", "DPAD_UP", "STICK_LS_UP", "LS_LEFT", "RS_LEFT", "LS_UP"):
            self._selected_btn_idx = 0
            self._update_gamepad_selection_styles()
            return True
        elif btn in ("DPAD_RIGHT", "STICK_LS_RIGHT", "STICK_RS_RIGHT", "DPAD_DOWN", "STICK_LS_DOWN", "LS_RIGHT", "RS_RIGHT", "LS_DOWN"):
            self._selected_btn_idx = 1
            self._update_gamepad_selection_styles()
            return True
        elif btn == "A":
            if self._selected_btn_idx == 0:
                self._add_5_minutes()
            else:
                self._resume_work()
            return True
        elif btn == "B":
            self._resume_work()
            return True
        return False

    def _get_gamepad_dispatcher(self):
        try:
            from ..gamepad.hooks import get_gamepad_dispatcher
            return get_gamepad_dispatcher()
        except (ImportError, ValueError):
            try:
                from modules.gamepad.hooks import get_gamepad_dispatcher
                return get_gamepad_dispatcher()
            except Exception:
                return None

    def _register_gamepad(self, active: bool):
        try:
            disp = self._get_gamepad_dispatcher()
            if disp:
                target = self if active else None
                if hasattr(disp, "set_active_dialog"):
                    disp.set_active_dialog(target)
                elif hasattr(disp, "is_dialog_active"):
                    disp.is_dialog_active = active
                    disp.active_dialog = target
        except Exception:
            pass

    def showEvent(self, event):
        try:
            super().showEvent(event)
        except Exception:
            pass
        self._selected_btn_idx = 1
        self._update_gamepad_selection_styles()
        self._register_gamepad(True)

    def hideEvent(self, event):
        self._register_gamepad(False)
        try:
            super().hideEvent(event)
        except Exception:
            pass

    def closeEvent(self, event):
        self._register_gamepad(False)
        try:
            super().closeEvent(event)
        except Exception:
            pass

    def reject(self):
        self._register_gamepad(False)
        try:
            super().reject()
        except Exception:
            pass

    def show_centered(self):
        if mw:
            geo = mw.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        self._selected_btn_idx = 1
        self._update_gamepad_selection_styles()
        self.show()
        if hasattr(self, "raise_"):
            self.raise_()
        if hasattr(self, "activateWindow"):
            self.activateWindow()
        self._register_gamepad(True)

    def update_countdown(self):
        rem_sec = self.engine.remaining_seconds
        formatted = self.engine.get_formatted_time()
        self.lbl_timer.setText(formatted)

        if rem_sec < 0:
            # Overtime state
            self.icon_lbl.setText("⏰")
            self.lbl_title.setText(tr("rest_overtime_title", "⚠️ Intervalo Concluído (+Overtime)"))
            self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f87171;")
            self.lbl_timer.setStyleSheet("font-size: 46px; font-weight: 800; color: #f87171; font-family: Consolas, monospace;")
            self.lbl_desc.setText(tr("rest_overtime_desc", "O tempo do intervalo acabou! Pronto para voltar ou precisa de mais 5 min?"))
        else:
            # Normal countdown state
            self.icon_lbl.setText("☕")
            self.lbl_title.setText(tr("rest_title", "☕ Hora de Descansar a Mente!"))
            self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #60a5fa;")
            self.lbl_timer.setStyleSheet("font-size: 46px; font-weight: 800; color: #4ade80; font-family: Consolas, monospace;")
            self.lbl_desc.setText(tr("rest_desc", "Levante-se, tome uma água, alongue o corpo e descanse a visão."))

        if self.engine.state not in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
            self.hide()

    def _add_5_minutes(self):
        from .hooks import log_runtime_event
        log_runtime_event("REST_DIALOG_CLICK: add_5_minutes")
        self.engine.add_time_seconds(300)
        self.update_countdown()

    def _resume_work(self):
        from .hooks import log_runtime_event
        log_runtime_event("REST_DIALOG_CLICK: resume_work")
        self._register_gamepad(False)
        self.engine.start_work_cycle()
        self.hide()

    def _skip_break(self):
        self._resume_work()


class FloatingPomodoroFAB(QWidget):
    """
    Modern Floating Action Button (FAB) that expands into a full Pomodoro Dashboard card.
    Floats in the bottom-right corner of the Anki main window.
    """

    def __init__(self, engine: PomodoroEngine, parent=None):
        super().__init__(parent or mw)
        self.engine = engine
        self.is_expanded = False
        self.drag_position = QPoint()

        # Frameless floating widget
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.rest_overlay = RestOverlayDialog(engine, None)

        self._setup_ui()
        self._apply_theme_style()

        # Engine callbacks
        self.engine.on_tick_callback = self.on_timer_tick
        self.engine.on_state_change_callback = self.on_timer_state_change

        # Track parent resize events
        if mw:
            mw.installEventFilter(self)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Outer card container frame
        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("pomo_fab_frame")
        self.frame_layout = QVBoxLayout(self.card_frame)
        self.frame_layout.setContentsMargins(12, 8, 12, 8)
        self.frame_layout.setSpacing(6)

        # 1. Compact Header Bar (Always visible)
        self.header_bar = QWidget()
        h_layout = QHBoxLayout(self.header_bar)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        # State pill
        self.lbl_state_icon = QLabel("🍅")
        self.lbl_state_icon.setStyleSheet("font-size: 16px;")
        h_layout.addWidget(self.lbl_state_icon)

        self.lbl_timer = QLabel(self.engine.get_formatted_time())
        self.lbl_timer.setStyleSheet("font-weight: 800; font-size: 14px; font-family: monospace;")
        h_layout.addWidget(self.lbl_timer)

        self.lbl_cycles = QLabel(f"🍅x{self.engine.completed_cycles}")
        self.lbl_cycles.setStyleSheet("font-size: 11px; font-weight: 600; opacity: 0.8;")
        h_layout.addWidget(self.lbl_cycles)

        # Quick Play/Pause button in compact bar
        self.btn_quick_pause = QPushButton("⏸️")
        self.btn_quick_pause.setFixedSize(24, 24)
        self.btn_quick_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_pause.setStyleSheet("border-radius: 12px; font-size: 11px; padding: 0;")
        self.btn_quick_pause.clicked.connect(self.engine.toggle_pause)
        h_layout.addWidget(self.btn_quick_pause)

        # Expand/Collapse toggle button
        self.btn_toggle_expand = QPushButton("⛶")
        self.btn_toggle_expand.setToolTip("Expandir / Minimizar")
        self.btn_toggle_expand.setFixedSize(24, 24)
        self.btn_toggle_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_expand.setStyleSheet("border-radius: 12px; font-size: 11px; padding: 0;")
        self.btn_toggle_expand.clicked.connect(self.toggle_expand)
        h_layout.addWidget(self.btn_toggle_expand)

        self.frame_layout.addWidget(self.header_bar)

        # 2. Expanded Content Panel (Shown when expanded)
        self.expanded_panel = QWidget()
        v_exp = QVBoxLayout(self.expanded_panel)
        v_exp.setContentsMargins(0, 6, 0, 0)
        v_exp.setSpacing(8)

        # State badge full
        self.lbl_full_state = QLabel("Foco Ativo")
        self.lbl_full_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_full_state.setStyleSheet("""
            background: rgba(0, 120, 215, 0.2);
            color: #3182ce;
            font-weight: 700;
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 8px;
        """)
        v_exp.addWidget(self.lbl_full_state)

        # ETA details
        self.lbl_eta = QLabel("Calculando ETA...")
        self.lbl_eta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_eta.setStyleSheet("font-size: 11px; opacity: 0.75;")
        v_exp.addWidget(self.lbl_eta)

        # Action button bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        self.btn_skip = QPushButton("⏩ Intervalo")
        self.btn_skip.setToolTip("Pular para o Intervalo (Alt+S)")
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: 600; border-radius: 8px;")
        self.btn_skip.clicked.connect(lambda: self.engine.skip_to_break())
        btn_bar.addWidget(self.btn_skip)

        self.btn_reset = QPushButton("🔄 Reset")
        self.btn_reset.setToolTip("Reiniciar Bloco (Alt+R)")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: 600; border-radius: 8px;")
        self.btn_reset.clicked.connect(lambda: self.engine.reset_current_phase())
        btn_bar.addWidget(self.btn_reset)

        self.btn_cfg = QPushButton("⚙️")
        self.btn_cfg.setToolTip("Configurações do Pomodoro")
        self.btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cfg.setFixedSize(26, 26)
        self.btn_cfg.setStyleSheet("padding: 0; font-size: 12px; border-radius: 13px;")
        self.btn_cfg.clicked.connect(self._open_config)
        btn_bar.addWidget(self.btn_cfg)

        v_exp.addLayout(btn_bar)
        self.frame_layout.addWidget(self.expanded_panel)

        self.main_layout.addWidget(self.card_frame)

        # Initial state: compact
        self.expanded_panel.setVisible(False)
        self.setFixedSize(200, 48)

    def _apply_theme_style(self):
        """Applies sleek glassmorphic floating styling."""
        is_night = False
        if mw and hasattr(mw, "pm") and mw.pm:
            is_night = mw.pm.night_mode()

        if is_night:
            bg_color = "rgba(26, 32, 44, 0.92)"
            border_color = "rgba(74, 85, 104, 0.7)"
            text_color = "#f7fafc"
            btn_bg = "rgba(255, 255, 255, 0.12)"
        else:
            bg_color = "rgba(255, 255, 255, 0.94)"
            border_color = "rgba(226, 232, 240, 0.9)"
            text_color = "#2d3748"
            btn_bg = "rgba(0, 120, 215, 0.08)"

        self.card_frame.setStyleSheet(f"""
            QFrame#pomo_fab_frame {{
                background-color: {bg_color};
                border: 1.5px solid {border_color};
                border-radius: 20px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {border_color};
            }}
            QPushButton:hover {{
                background-color: rgba(0, 120, 215, 0.22);
            }}
        """)

    def toggle_expand(self):
        """Toggles between compact pill and expanded card."""
        self.is_expanded = not self.is_expanded
        self.expanded_panel.setVisible(self.is_expanded)
        self.btn_toggle_expand.setText("✕" if self.is_expanded else "⛶")

        if self.is_expanded:
            self.setFixedSize(225, 155)
        else:
            self.setFixedSize(200, 48)

        self.reposition()

    def reposition(self):
        """Positions the FAB at the bottom-right of Anki's main window."""
        if not mw or not self.isVisible():
            return
        geo = mw.geometry()
        margin_right = 24
        margin_bottom = 44  # Above bottom toolbar
        x = geo.width() - self.width() - margin_right
        y = geo.height() - self.height() - margin_bottom
        self.move(x, y)

    def eventFilter(self, obj, event):
        if obj == mw and event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self.reposition()
        return super().eventFilter(obj, event)

    def _open_config(self):
        from .config_dialog import PomodoroConfigDialog
        dialog = PomodoroConfigDialog(self.engine, mw)
        dialog.exec()

    def update_hud(self):
        self.lbl_timer.setText(self.engine.get_formatted_time())
        self.lbl_cycles.setText(f"🍅x{self.engine.completed_cycles}")

        # Update State
        state = self.engine.state
        if state == PomodoroState.WORK:
            self.lbl_state_icon.setText("🍅")
            self.lbl_full_state.setText("🍅 Foco Ativo")
            self.lbl_full_state.setStyleSheet("background: rgba(0, 120, 215, 0.2); color: #3182ce; font-weight: 700; font-size: 12px; padding: 3px 8px; border-radius: 8px;")
            self.btn_quick_pause.setText("⏸️")
        elif state == PomodoroState.SOFT_BREAK:
            self.lbl_state_icon.setText("⏸️")
            self.lbl_full_state.setText("⏸️ Pausa Suave (Finalize o Card)")
            self.lbl_full_state.setStyleSheet("background: rgba(221, 107, 32, 0.25); color: #dd6b20; font-weight: 700; font-size: 12px; padding: 3px 8px; border-radius: 8px;")
            self.btn_quick_pause.setText("▶️")
        elif state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
            self.lbl_state_icon.setText("☕")
            self.lbl_full_state.setText("☕ Intervalo de Descanso")
            self.lbl_full_state.setStyleSheet("background: rgba(56, 161, 105, 0.25); color: #38a169; font-weight: 700; font-size: 12px; padding: 3px 8px; border-radius: 8px;")
            self.btn_quick_pause.setText("⏸️")
        elif state == PomodoroState.PAUSED:
            reason = "Inatividade" if self.engine.is_paused_by_inactivity else "Pausado"
            self.lbl_state_icon.setText("⏸️")
            self.lbl_full_state.setText(f"⏸️ {reason}")
            self.lbl_full_state.setStyleSheet("background: rgba(113, 128, 150, 0.25); color: #718096; font-weight: 700; font-size: 12px; padding: 3px 8px; border-radius: 8px;")
            self.btn_quick_pause.setText("▶️")

        # Update ETA
        if mw and mw.col:
            try:
                cur_did = mw.col.decks.get_current_id()
                from ..dashboard.stats_engine import compute_dashboard_stats
                stats = compute_dashboard_stats(mw.col, cur_did)
                rem_cards = stats.remaining.total_remaining
                if rem_cards > 0:
                    eta_data = self.engine.fatigue_tracker.compute_eta(rem_cards)
                    self.lbl_eta.setText(f"Restantes: <b>{rem_cards}</b> | ETA: <b>{eta_data['formatted_eta']}</b>")
                else:
                    self.lbl_eta.setText("Todos os cards concluídos! 🎉")
            except Exception:
                self.lbl_eta.setText("")

    def on_timer_tick(self, engine: PomodoroEngine):
        self.update_hud()
        if engine.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
            if not self.rest_overlay.isVisible():
                self.rest_overlay.show_centered()
            self.rest_overlay.update_countdown()
        else:
            if self.rest_overlay.isVisible():
                self.rest_overlay.hide()

    def on_timer_state_change(self, engine: PomodoroEngine):
        self.update_hud()
        if engine.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
            self.rest_overlay.show_centered()
            self.rest_overlay.update_countdown()
        else:
            self.rest_overlay.hide()


# Alias for backward compatibility
ReviewerPomodoroHUD = FloatingPomodoroFAB
