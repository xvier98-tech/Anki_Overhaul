# -*- coding: utf-8 -*-
"""
Native PyQt6 Floating Pomodoro Action Widget (FAB).
Provides 100% reliable, zero-IPC direct GUI controls for Anki Desktop.
Runs directly on the Qt main window as a translucent floating overlay.
"""

from typing import Optional, Dict, Any

try:
    from PyQt6.QtWidgets import (
        QWidget,
        QPushButton,
        QLabel,
        QHBoxLayout,
        QVBoxLayout,
        QProgressBar,
        QGraphicsDropShadowEffect,
        QFrame,
    )
    from PyQt6.QtCore import Qt, QPoint, QTimer, QEvent
    from PyQt6.QtGui import QFont, QColor, QKeySequence, QShortcut
    from aqt import mw, gui_hooks
except ImportError:
    class _MockUIMeta(type):
        def __getattr__(cls, name):
            return _MockUI()

    class _MockUI(metaclass=_MockUIMeta):
        def __init__(self, *args, **kwargs):
            self._ss = ""
            self._text = args[0] if args and isinstance(args[0], str) else ""
            self._visible = True
            self._flags = None
        def __call__(self, *args, **kwargs):
            return self
        def __getattr__(self, name):
            return _MockUI()
        def __or__(self, other):
            return self
        def __ror__(self, other):
            return self
        def styleSheet(self):
            return self._ss
        def setStyleSheet(self, ss):
            self._ss = ss
        def text(self):
            return self._text
        def setText(self, t):
            self._text = str(t)
        def isVisible(self):
            return self._visible
        def setVisible(self, v):
            self._visible = bool(v)
        def hide(self):
            self._visible = False
        def show(self):
            self._visible = True
        def setWindowFlags(self, flags):
            self._flags = flags
        def windowFlags(self):
            return self._flags
        def eventFilter(self, obj, event):
            return False

    mw = None
    gui_hooks = None
    QWidget = _MockUI
    QPushButton = _MockUI
    QLabel = _MockUI
    QHBoxLayout = _MockUI
    QVBoxLayout = _MockUI
    QProgressBar = _MockUI
    QGraphicsDropShadowEffect = _MockUI
    QFrame = _MockUI
    Qt = _MockUI()
    QPoint = _MockUI
    QTimer = None
    QFont = _MockUI
    QColor = _MockUI
    QShortcut = _MockUI
    QKeySequence = _MockUI

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

try:
    from ..theme_manager.presets import get_active_theme_colors
except (ImportError, ValueError):
    try:
        from modules.theme_manager.presets import get_active_theme_colors
    except ImportError:
        def get_active_theme_colors(theme_cfg):
            return {
                "bg_card": "#121316",
                "border_color": "#27272a",
                "accent": "#38bdf8",
                "text_primary": "#f8fafc",
                "text_secondary": "#94a3b8",
            }


def _is_event_type(ev_type, target_name: str, fallback_int: int) -> bool:
    """Helper to reliably match QEvent types in both real PyQt6 and headless test mocks."""
    try:
        if QEvent and hasattr(QEvent, "Type") and hasattr(QEvent.Type, target_name):
            target = getattr(QEvent.Type, target_name)
            if ev_type == target or ev_type == fallback_int:
                return True
    except Exception:
        pass
    return ev_type == fallback_int or ev_type == str(fallback_int)


class NativePomodoroFab(QWidget):
    """
    Floating Qt overlay widget displaying the Pomodoro timer, progress, and controls.
    """

    def __init__(self, engine: PomodoroEngine, parent: Optional[QWidget] = None):
        super().__init__(parent or mw)
        self.engine = engine
        self.is_expanded = False
        self._drag_pos: Optional[QPoint] = None
        self._custom_pos: Optional[QPoint] = None
        self._auto_advance_timer: Optional[Any] = None

        if QTimer:
            self._auto_advance_timer = QTimer(self)
            self._auto_advance_timer.setInterval(250)
            self._auto_advance_timer.timeout.connect(self._update_auto_advance_display)

        config = get_module_config("pomodoro")
        saved_pos = config.get("fab_position")
        if isinstance(saved_pos, dict) and "x" in saved_pos and "y" in saved_pos:
            self._custom_pos = QPoint(int(saved_pos["x"]), int(saved_pos["y"]))

        self._init_ui()
        self._setup_events()
        self.update_display()

    def _init_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip(tr("fab_tooltip", "🍅 Pomodoro - Clique e arraste para posicionar onde desejar (Clique duplo para restaurar)"))
        self.setAccessibleName(tr("aria_pomo_fab", "Widget flutuante do Pomodoro"))

        # Main Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("pomoCard")
        self.card.setCursor(Qt.CursorShape.SizeAllCursor)
        self.card.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Shadow Effect - Balanced radius and offset for natural, smooth ambient diffusion
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        # Layouts - Generous margins around self.card to allow drop shadow to disperse completely without clipping
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(32, 28, 32, 40)
        self.main_layout.addWidget(self.card)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 10, 14, 10)
        self.card_layout.setSpacing(8)

        # --- Top Header Row ---
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(8)

        self.lbl_icon = QLabel("🍅")
        font_emoji = QFont("Segoe UI Emoji", 14)
        self.lbl_icon.setFont(font_emoji)

        self.lbl_timer = QLabel("25:00")
        self.lbl_timer.setObjectName("pomoTimer")
        font_timer = QFont("Consolas", 15, QFont.Weight.Bold)
        font_timer.setStyleHint(QFont.StyleHint.Monospace)
        self.lbl_timer.setFont(font_timer)
        self.lbl_timer.setAccessibleName(tr("aria_pomo_timer", "Contagem regressiva do tempo de estudo"))

        self.lbl_badge = QLabel("PRONTO")
        self.lbl_badge.setObjectName("pomoBadge")
        font_badge = QFont("Segoe UI", 8, QFont.Weight.Bold)
        self.lbl_badge.setFont(font_badge)
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setAccessibleName(tr("aria_pomo_badge", "Estado atual da sessão do Pomodoro"))

        self.lbl_cycles = QLabel("🍅x0")
        self.lbl_cycles.setObjectName("pomoCycles")
        self.lbl_cycles.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_cycles.setAccessibleName(tr("aria_pomo_cycles", "Contagem de ciclos completos do Pomodoro"))

        # Smart Auto-Advance Countdown Badge
        self.lbl_auto_advance = QLabel("")
        self.lbl_auto_advance.setObjectName("pomoAutoAdvance")
        font_auto = QFont("Consolas", 10, QFont.Weight.Bold)
        font_auto.setStyleHint(QFont.StyleHint.Monospace)
        self.lbl_auto_advance.setFont(font_auto)
        self.lbl_auto_advance.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_auto_advance.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lbl_auto_advance.setVisible(False)

        font_btn_icon = QFont("Segoe UI Emoji", 12, QFont.Weight.Bold)

        # Direct Focus Toggle Button (Always visible on header)
        self.btn_focus_toggle = QPushButton("🎯")
        self.btn_focus_toggle.setObjectName("pomoIconBtn")
        self.btn_focus_toggle.setFont(font_btn_icon)
        self.btn_focus_toggle.setFixedSize(32, 32)
        self.btn_focus_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_focus_toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_focus_toggle.setToolTip(tr("fab_btn_focus_enter_tip", "Entrar no Modo Foco / Tela Cheia (F11)"))
        self.btn_focus_toggle.setAccessibleName(tr("aria_btn_focus", "Alternar modo tela cheia de foco"))
        self.btn_focus_toggle.clicked.connect(self.on_toggle_focus)

        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("pomoIconBtn")
        self.btn_play.setFont(font_btn_icon)
        self.btn_play.setFixedSize(32, 32)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_play.setToolTip(tr("fab_btn_play_tip", "Iniciar / Pausar Pomodoro (Alt+P)"))
        self.btn_play.setAccessibleName(tr("aria_btn_play", "Iniciar ou pausar cronômetro Pomodoro"))
        self.btn_play.clicked.connect(self.on_toggle_pause)

        self.btn_expand = QPushButton("⛶")
        self.btn_expand.setObjectName("pomoIconBtn")
        self.btn_expand.setFont(font_btn_icon)
        self.btn_expand.setFixedSize(32, 32)
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_expand.setToolTip(tr("fab_btn_expand_tip", "Expandir / Minimizar painel"))
        self.btn_expand.setAccessibleName(tr("aria_btn_expand", "Expandir ou minimizar painel"))
        self.btn_expand.clicked.connect(self.toggle_expand)

        self.header_layout.addWidget(self.lbl_icon)
        self.header_layout.addWidget(self.lbl_timer)
        self.header_layout.addWidget(self.lbl_badge)
        self.header_layout.addWidget(self.lbl_auto_advance)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.lbl_cycles)
        self.header_layout.addWidget(self.btn_focus_toggle)
        self.header_layout.addWidget(self.btn_play)
        self.header_layout.addWidget(self.btn_expand)

        self.card_layout.addLayout(self.header_layout)

        # --- Expanded Section ---
        self.expanded_container = QWidget()
        self.expanded_layout = QVBoxLayout(self.expanded_container)
        self.expanded_layout.setContentsMargins(0, 6, 0, 0)
        self.expanded_layout.setSpacing(8)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.12);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #0284c7);
                border-radius: 3px;
            }
        """)
        self.expanded_layout.addWidget(self.progress_bar)

        # Stats Row
        self.stats_layout = QHBoxLayout()
        self.lbl_rem_cards = QLabel("Restantes: 0")
        self.lbl_rem_cards.setObjectName("pomoMetaLabel")
        self.lbl_rem_cards.setFont(QFont("Segoe UI", 9))

        self.lbl_eta = QLabel("ETA: 0m")
        self.lbl_eta.setObjectName("pomoMetaLabel")
        self.lbl_eta.setFont(QFont("Segoe UI", 9))

        self.stats_layout.addWidget(self.lbl_rem_cards)
        self.stats_layout.addStretch(1)
        self.stats_layout.addWidget(self.lbl_eta)
        self.expanded_layout.addLayout(self.stats_layout)

        # Actions Buttons Bar
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(6)

        self.btn_focus = QPushButton(tr("fab_btn_focus_enter", "🎯 Modo Foco"))
        self.btn_focus.setObjectName("pomoFocusBtn")
        self.btn_focus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_focus.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_focus.setToolTip(tr("fab_btn_focus_tip", "Ativar modo tela cheia e imersão nos estudos"))
        self.btn_focus.setAccessibleName(tr("aria_btn_focus", "Alternar modo tela cheia de foco"))
        self.btn_focus.clicked.connect(self.on_toggle_focus)

        self.btn_skip = QPushButton(tr("fab_btn_skip", "⏭️ Pular"))
        self.btn_skip.setObjectName("pomoActionBtn")
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_skip.setToolTip(tr("fab_btn_skip_tip", "Pular para intervalo ou próximo bloco de foco (Alt+S)"))
        self.btn_skip.setAccessibleName(tr("aria_btn_skip", "Pular fase atual do Pomodoro"))
        self.btn_skip.clicked.connect(self.on_skip_break)

        self.btn_reset = QPushButton(tr("fab_btn_reset", "🔄 Reset"))
        self.btn_reset.setObjectName("pomoActionBtn")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_reset.setToolTip(tr("fab_btn_reset_tip", "Reiniciar contagem da fase atual (Alt+R)"))
        self.btn_reset.setAccessibleName(tr("aria_btn_reset", "Reiniciar cronômetro da fase atual"))
        self.btn_reset.clicked.connect(self.on_reset_phase)

        self.btn_cfg = QPushButton(tr("fab_btn_config", "⚙️ Config"))
        self.btn_cfg.setObjectName("pomoActionBtn")
        self.btn_cfg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cfg.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_cfg.setToolTip(tr("fab_btn_cfg_tip", "Abrir configurações do Pomodoro"))
        self.btn_cfg.setAccessibleName(tr("aria_btn_config", "Abrir preferências do Pomodoro"))
        self.btn_cfg.clicked.connect(self.on_open_config)

        self.actions_layout.addWidget(self.btn_focus)
        self.actions_layout.addWidget(self.btn_skip)
        self.actions_layout.addWidget(self.btn_reset)
        self.actions_layout.addWidget(self.btn_cfg)

        self.expanded_layout.addLayout(self.actions_layout)
        self.expanded_container.setVisible(False)
        self.card_layout.addWidget(self.expanded_container)

        self._apply_stylesheet()

    def _is_light_color(self, hex_code: str) -> bool:
        """Determines if a hex color is light based on perceived relative luminance."""
        try:
            h = hex_code.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            return lum > 0.55
        except Exception:
            return False

    def _apply_stylesheet(self):
        try:
            theme_cfg = get_module_config("theme")
            colors = get_active_theme_colors(theme_cfg)
        except Exception:
            colors = {
                "bg_card": "#121316",
                "border_color": "#27272a",
                "accent": "#38bdf8",
                "text_primary": "#f8fafc",
                "text_secondary": "#94a3b8",
            }

        bg_card = colors.get("bg_card", "#121316")
        border_color = colors.get("border_color", "#27272a")
        accent = colors.get("accent", "#38bdf8")
        text_primary = colors.get("text_primary", "#f8fafc")
        text_secondary = colors.get("text_secondary", "#94a3b8")

        is_light = self._is_light_color(bg_card)
        self._is_light = is_light

        # Enforce high contrast text against card background
        if is_light:
            if self._is_light_color(text_primary):
                text_primary = "#0f172a"
            if self._is_light_color(text_secondary):
                text_secondary = "#475569"
            icon_btn_bg = "rgba(0, 0, 0, 0.05)"
            icon_btn_hover = "rgba(0, 0, 0, 0.10)"
            icon_btn_border = "rgba(0, 0, 0, 0.16)"
            focus_btn_bg = "rgba(147, 51, 234, 0.12)"
            focus_btn_hover = "rgba(147, 51, 234, 0.22)"
            focus_btn_border = "rgba(147, 51, 234, 0.42)"
            focus_btn_color = "#6b21a8"
            prog_bg = "rgba(0, 0, 0, 0.08)"
        else:
            if not self._is_light_color(text_primary):
                text_primary = "#f8fafc"
            if not self._is_light_color(text_secondary):
                text_secondary = "#94a3b8"
            icon_btn_bg = "rgba(255, 255, 255, 0.08)"
            icon_btn_hover = "rgba(255, 255, 255, 0.22)"
            icon_btn_border = "rgba(255, 255, 255, 0.18)"
            focus_btn_bg = "rgba(168, 85, 247, 0.22)"
            focus_btn_hover = "rgba(168, 85, 247, 0.42)"
            focus_btn_border = "rgba(168, 85, 247, 0.5)"
            focus_btn_color = "#f8fafc"
            prog_bg = "rgba(255, 255, 255, 0.12)"

        try:
            r = int(bg_card[1:3], 16)
            g = int(bg_card[3:5], 16)
            b = int(bg_card[5:7], 16)
            card_rgba = f"rgba({r}, {g}, {b}, 0.96)"
        except Exception:
            card_rgba = "rgba(15, 17, 24, 0.95)"

        try:
            ar = int(accent[1:3], 16)
            ag = int(accent[3:5], 16)
            ab = int(accent[5:7], 16)
            alpha_btn = 0.14 if is_light else 0.18
            alpha_hover = 0.26 if is_light else 0.38
            alpha_border = 0.45 if is_light else 0.55
            action_btn_bg = f"rgba({ar}, {ag}, {ab}, {alpha_btn})"
            action_btn_hover = f"rgba({ar}, {ag}, {ab}, {alpha_hover})"
            action_btn_border = f"rgba({ar}, {ag}, {ab}, {alpha_border})"
        except Exception:
            action_btn_bg = "rgba(56, 189, 248, 0.16)"
            action_btn_hover = "rgba(56, 189, 248, 0.35)"
            action_btn_border = "rgba(56, 189, 248, 0.4)"

        self.setStyleSheet(f"""
            #pomoCard {{
                background-color: {card_rgba};
                border: 1.5px solid {border_color};
                border-radius: 18px;
            }}
            #pomoCard QLabel {{
                color: {text_primary};
            }}
            #pomoTimer {{
                color: {text_primary};
                font-weight: 800;
                font-size: 15px;
                font-family: Consolas, monospace;
            }}
            #pomoBadge {{
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            #pomoAutoAdvance {{
                padding: 2px 7px;
                border-radius: 9px;
                font-size: 11px;
                font-weight: bold;
                font-family: Consolas, monospace;
            }}
            #pomoCycles {{
                color: {text_secondary};
                font-size: 9px;
                font-weight: bold;
            }}
            #pomoMetaLabel {{
                color: {text_secondary};
                font-size: 11px;
            }}
            #pomoIconBtn {{
                background-color: {icon_btn_bg};
                border: 1px solid {icon_btn_border};
                border-radius: 8px;
                color: {text_primary};
                font-family: "Segoe UI Emoji", "Segoe UI Symbol", "Segoe UI", Arial, sans-serif;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
            }}
            #pomoIconBtn:hover {{
                background-color: {icon_btn_hover};
            }}
            #pomoActionBtn {{
                background-color: {action_btn_bg};
                border: 1px solid {action_btn_border};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: bold;
                color: {text_primary};
            }}
            #pomoActionBtn:hover {{
                background-color: {action_btn_hover};
                border-color: {accent};
            }}
            #pomoFocusBtn {{
                background-color: {focus_btn_bg};
                border: 1px solid {focus_btn_border};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: bold;
                color: {focus_btn_color};
            }}
            #pomoFocusBtn:hover {{
                background-color: {focus_btn_hover};
                border-color: #c084fc;
            }}
            QProgressBar {{
                background-color: {prog_bg};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 #0284c7);
                border-radius: 3px;
            }}
        """)

    def refresh_theme(self):
        """Re-applies stylesheet using current theme colors and updates text."""
        self._apply_stylesheet()
        self.btn_skip.setText(tr("fab_btn_skip_break", "⏩ Intervalo"))
        self.btn_reset.setText(tr("fab_btn_reset", "🔄 Reset"))
        self.btn_cfg.setText(tr("fab_btn_config", "⚙️ Config"))
        self.update_display()

    def _setup_events(self):
        if mw:
            mw.installEventFilter(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is on the visible card; if in the transparent shadow margin, ignore so clicks pass to Anki
            pt = event.position().toPoint() if hasattr(event, "position") and hasattr(event.position(), "toPoint") else getattr(event, "pos", lambda: QPoint(0, 0))()
            if hasattr(self.card, "geometry") and callable(getattr(self.card.geometry(), "contains", None)):
                if not self.card.geometry().contains(pt):
                    event.ignore()
                    return

            if hasattr(event, "globalPosition") and hasattr(event.globalPosition(), "toPoint"):
                self._drag_pos = event.globalPosition().toPoint() - self.pos()
            elif hasattr(event, "globalPos"):
                self._drag_pos = event.globalPos() - self.pos()
            else:
                self._drag_pos = None
            event.accept()
        else:
            super().mousePressEvent(event)

    def enterEvent(self, event):
        """Restores cursor if it was hidden by FocusGuard when entering the FAB."""
        try:
            from .hooks import get_focus_guard
            fg = get_focus_guard()
            if fg and hasattr(fg, "_restore_cursor"):
                fg._restore_cursor()
        except Exception:
            pass
        self.raise_()
        super().enterEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if hasattr(event, "globalPosition") and hasattr(event.globalPosition(), "toPoint"):
                cur_global = event.globalPosition().toPoint()
            elif hasattr(event, "globalPos"):
                cur_global = event.globalPos()
            else:
                cur_global = self.pos()
            new_pos = cur_global - self._drag_pos
            if mw:
                try:
                    mw_geo = mw.geometry()
                    mw_x = mw_geo.x()
                    mw_y = mw_geo.y()
                    mw_w = mw_geo.width()
                    mw_h = mw_geo.height()
                except Exception:
                    mw_x, mw_y = 0, 0
                    mw_w = getattr(mw, "width", lambda: 800)()
                    mw_h = getattr(mw, "height", lambda: 600)()

                rel_x = new_pos.x() - mw_x
                rel_y = new_pos.y() - mw_y
                clamped_rel_x = max(0, min(max(0, mw_w - self.width()), rel_x))
                clamped_rel_y = max(0, min(max(0, mw_h - self.height()), rel_y))
                self._custom_pos = QPoint(clamped_rel_x, clamped_rel_y)
                self.move(mw_x + clamped_rel_x, mw_y + clamped_rel_y)
            else:
                self._custom_pos = new_pos
                self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            if self._custom_pos is not None:
                try:
                    from ...utils.config_manager import write_module_config
                except (ImportError, ValueError):
                    from utils.config_manager import write_module_config
                config = get_module_config("pomodoro")
                config["fab_position"] = {"x": self._custom_pos.x(), "y": self._custom_pos.y()}
                write_module_config("pomodoro", config)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.position().toPoint() if hasattr(event, "position") and hasattr(event.position(), "toPoint") else getattr(event, "pos", lambda: QPoint(0, 0))()
            if hasattr(self.card, "geometry") and callable(getattr(self.card.geometry(), "contains", None)):
                if not self.card.geometry().contains(pt):
                    event.ignore()
                    return

            # Double-click resets FAB to default bottom-right position!
            self._custom_pos = None
            try:
                from ...utils.config_manager import write_module_config
            except (ImportError, ValueError):
                from utils.config_manager import write_module_config
            config = get_module_config("pomodoro")
            config.pop("fab_position", None)
            write_module_config("pomodoro", config)
            self.reposition()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def eventFilter(self, obj, event):
        if mw and obj == mw and event:
            try:
                ev_type = event.type() if hasattr(event, "type") and callable(event.type) else event
                if _is_event_type(ev_type, "Resize", 14) or _is_event_type(ev_type, "Move", 13):
                    self.reposition()
                elif _is_event_type(ev_type, "WindowStateChange", 105):
                    is_min = mw.isMinimized() if hasattr(mw, "isMinimized") and callable(mw.isMinimized) else False
                    if is_min:
                        self.hide()
                    else:
                        config = get_module_config("pomodoro")
                        if config.get("enabled", True):
                            if not self.isVisible():
                                self.show()
                            self.reposition()
                elif _is_event_type(ev_type, "Hide", 18):
                    self.hide()
                elif _is_event_type(ev_type, "Show", 17):
                    config = get_module_config("pomodoro")
                    if config.get("enabled", True):
                        if not self.isVisible():
                            self.show()
                        self.reposition()
            except Exception:
                pass
        try:
            return super().eventFilter(obj, event)
        except Exception:
            return False

    def reposition(self):
        if not mw:
            return
        is_min = mw.isMinimized() if hasattr(mw, "isMinimized") and callable(mw.isMinimized) else False
        is_vis = mw.isVisible() if hasattr(mw, "isVisible") and callable(mw.isVisible) else True
        if is_min or not is_vis:
            return

        self.adjustSize()
        w = self.width()
        h = self.height()
        try:
            mw_geo = mw.geometry()
            mw_x = mw_geo.x()
            mw_y = mw_geo.y()
            parent_w = mw_geo.width()
            parent_h = mw_geo.height()
        except Exception:
            mw_x, mw_y = 0, 0
            parent_w = getattr(mw, "width", lambda: 800)()
            parent_h = getattr(mw, "height", lambda: 600)()

        if self._custom_pos is not None:
            # Keep custom position clamped within current parent bounds
            clamped_x = max(0, min(max(0, parent_w - w), self._custom_pos.x()))
            clamped_y = max(0, min(max(0, parent_h - h), self._custom_pos.y()))
            self.move(mw_x + clamped_x, mw_y + clamped_y)
        else:
            # Position at bottom right taking expanded margins into account so shadow remains unclipped
            target_x = max(0, parent_w - w - 8)
            target_y = max(0, parent_h - h - 12)
            self.move(mw_x + target_x, mw_y + target_y)

        # Only raise within Anki's window hierarchy if Anki or the FAB is the active window
        is_active = mw.isActiveWindow() if hasattr(mw, "isActiveWindow") and callable(mw.isActiveWindow) else True
        fab_active = self.isActiveWindow() if hasattr(self, "isActiveWindow") and callable(self.isActiveWindow) else False
        if is_active or fab_active:
            self.raise_()

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.expanded_container.setVisible(self.is_expanded)
        self.btn_expand.setText("➖" if self.is_expanded else "⛶")
        self.reposition()

    def _update_auto_advance_display(self):
        """Updates live countdown badge for Smart Auto-Advance on the FAB."""
        try:
            from .auto_advance import get_auto_advance_manager
            mgr = get_auto_advance_manager(self.engine)
            info = mgr.get_countdown_info()
        except Exception:
            info = {"active": False}

        config = get_module_config("pomodoro")
        auto_adv_enabled = bool(config.get("auto_advance_enabled", False))
        in_review = bool(mw and hasattr(mw, "state") and mw.state == "review")

        if not info.get("active", False):
            if hasattr(self, "lbl_auto_advance") and self.lbl_auto_advance.isVisible():
                self.lbl_auto_advance.setVisible(False)
                self.reposition()
            if not (auto_adv_enabled and in_review):
                if hasattr(self, "_auto_advance_timer") and self._auto_advance_timer and self._auto_advance_timer.isActive():
                    self._auto_advance_timer.stop()
            return

        side = info.get("side", "question")
        rem = info.get("remaining_seconds", 0)
        is_light = getattr(self, "_is_light", False)

        if side == "question":
            self.lbl_auto_advance.setText(f"⏱️ {rem}s")
            self.lbl_auto_advance.setToolTip(tr("pomo_auto_adv_q_tip", "Passagem Automática: {sec}s para mostrar resposta", sec=rem))
            if is_light:
                self.lbl_auto_advance.setStyleSheet(
                    "background: rgba(2, 132, 199, 0.15); color: #0284c7; "
                    "border: 1.5px solid rgba(2, 132, 199, 0.45); border-radius: 9px; padding: 2px 7px; font-weight: bold;"
                )
            else:
                self.lbl_auto_advance.setStyleSheet(
                    "background: rgba(56, 189, 248, 0.22); color: #38bdf8; "
                    "border: 1px solid rgba(56, 189, 248, 0.50); border-radius: 9px; padding: 2px 7px; font-weight: bold;"
                )
        else:
            # Answer countdown to Again
            self.lbl_auto_advance.setText(f"⚠️ {rem}s")
            self.lbl_auto_advance.setToolTip(tr("pomo_auto_adv_a_tip", "Passagem Automática: {sec}s para pontuar 'Errei' e avançar", sec=rem))
            if is_light:
                self.lbl_auto_advance.setStyleSheet(
                    "background: rgba(220, 38, 38, 0.15); color: #dc2626; "
                    "border: 1.5px solid rgba(220, 38, 38, 0.45); border-radius: 9px; padding: 2px 7px; font-weight: bold;"
                )
            else:
                self.lbl_auto_advance.setStyleSheet(
                    "background: rgba(239, 68, 68, 0.25); color: #f87171; "
                    "border: 1px solid rgba(239, 68, 68, 0.50); border-radius: 9px; padding: 2px 7px; font-weight: bold;"
                )

        if hasattr(self, "lbl_auto_advance") and not self.lbl_auto_advance.isVisible():
            self.lbl_auto_advance.setVisible(True)
            self.reposition()

        if hasattr(self, "_auto_advance_timer") and self._auto_advance_timer and not self._auto_advance_timer.isActive():
            self._auto_advance_timer.start(200)

    def update_display(self):
        """Refreshes all timer numbers, colors, badges and remaining count directly from Python."""
        formatted_time = self.engine.get_formatted_time()
        rem_sec = self.engine.remaining_seconds
        total_sec = max(1, self.engine.total_phase_seconds)
        progress_pct = max(0, min(100, int(((total_sec - rem_sec) / total_sec) * 100)))

        self.lbl_timer.setText(formatted_time)
        self.progress_bar.setValue(progress_pct)
        self.lbl_cycles.setText(f"🍅x{self.engine.completed_cycles}")

        is_light = getattr(self, "_is_light", False)

        if not self.engine.is_started or not self.engine.is_running:
            state_label = tr("fab_badge_paused", "PAUSADO") if self.engine.is_started else tr("fab_badge_ready", "PRONTO")
            self.lbl_icon.setText("⏸" if self.engine.is_started else "🍅")
            self.btn_play.setText("▶")
            self.lbl_badge.setText(state_label)
            if is_light:
                self.lbl_badge.setStyleSheet("background: rgba(217, 119, 6, 0.16); color: #b45309; border: 1.5px solid rgba(217, 119, 6, 0.45); font-weight: bold; border-radius: 10px; padding: 2px 8px;")
            else:
                self.lbl_badge.setStyleSheet("background: rgba(234, 179, 8, 0.25); color: #fde047; border: 1px solid rgba(234, 179, 8, 0.4); font-weight: bold; border-radius: 10px; padding: 2px 8px;")
        elif self.engine.state == PomodoroState.SOFT_BREAK:
            self.lbl_icon.setText("⏸")
            self.btn_play.setText("⏸")
            self.lbl_badge.setText(tr("fab_badge_soft_break", "P. SUAVE"))
            if is_light:
                self.lbl_badge.setStyleSheet("background: rgba(22, 163, 74, 0.16); color: #15803d; border: 1.5px solid rgba(22, 163, 74, 0.45); font-weight: bold; border-radius: 10px; padding: 2px 8px;")
            else:
                self.lbl_badge.setStyleSheet("background: rgba(34, 197, 94, 0.25); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.4); font-weight: bold; border-radius: 10px; padding: 2px 8px;")
        elif self.engine.state in (PomodoroState.BREAK, PomodoroState.LONG_BREAK):
            self.lbl_icon.setText("☕")
            self.btn_play.setText("⏸")
            self.lbl_badge.setText(tr("fab_badge_break", "INTERVALO"))
            if is_light:
                self.lbl_badge.setStyleSheet("background: rgba(22, 163, 74, 0.16); color: #15803d; border: 1.5px solid rgba(22, 163, 74, 0.45); font-weight: bold; border-radius: 10px; padding: 2px 8px;")
            else:
                self.lbl_badge.setStyleSheet("background: rgba(34, 197, 94, 0.25); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.4); font-weight: bold; border-radius: 10px; padding: 2px 8px;")
        else:
            self.lbl_icon.setText("🍅")
            self.btn_play.setText("⏸")
            self.lbl_badge.setText(tr("fab_badge_focus", "FOCO"))
            if is_light:
                self.lbl_badge.setStyleSheet("background: rgba(220, 38, 38, 0.16); color: #b91c1c; border: 1.5px solid rgba(220, 38, 38, 0.45); font-weight: bold; border-radius: 10px; padding: 2px 8px;")
            else:
                self.lbl_badge.setStyleSheet("background: rgba(239, 68, 68, 0.25); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); font-weight: bold; border-radius: 10px; padding: 2px 8px;")

        is_fs = mw.isFullScreen() if mw else False
        if hasattr(self, "btn_focus_toggle"):
            self.btn_focus_toggle.setText("🗗" if is_fs else "🎯")
            self.btn_focus_toggle.setToolTip(
                tr("fab_btn_focus_exit_tip", "Sair do Modo Foco / Tela Cheia (F11)")
                if is_fs else
                tr("fab_btn_focus_enter_tip", "Entrar no Modo Foco / Tela Cheia (F11)")
            )

        self.btn_focus.setText(tr("fab_btn_focus_exit", "🗗 Sair Foco") if is_fs else tr("fab_btn_focus_enter", "🎯 Modo Foco"))
        self.btn_focus.setToolTip(
            tr("fab_btn_focus_exit_tip", "Sair do Modo Foco / Tela Cheia (F11)")
            if is_fs else
            tr("fab_btn_focus_enter_tip", "Ativar modo tela cheia e imersão nos estudos")
        )

        self._update_auto_advance_display()

        # Update ETA and remaining cards
        rem_cards = 0
        if mw and mw.col:
            try:
                from ..dashboard.stats_engine import compute_dashboard_stats
                cur_did = mw.col.decks.get_current_id() if mw.state != "deckBrowser" else None
                stats = compute_dashboard_stats(mw.col, cur_did)
                rem_cards = stats.remaining.total_remaining
            except Exception:
                pass
        self.lbl_rem_cards.setText(tr("fab_remaining_cards", "Restantes: <b>{count}</b>", count=rem_cards))
        self.lbl_rem_cards.setAccessibleName(tr("aria_pomo_remaining", "Cartões restantes na fila de estudos de hoje"))
        eta_data = self.engine.fatigue_tracker.compute_eta(rem_cards)
        self.lbl_eta.setText(tr("fab_eta", "ETA: <b>{eta}</b>", eta=eta_data.get('formatted_eta', '0m')))
        self.lbl_eta.setAccessibleName(tr("aria_pomo_eta", "Tempo estimado de conclusão baseado no ritmo de estudo"))

        self.reposition()

    # --- Direct Qt Action Handlers ---

    def on_toggle_pause(self):
        from .hooks import log_runtime_event
        log_runtime_event(f"NATIVE_QT_CLICK: toggle_pause (was_running={self.engine.is_running})")
        self.engine.toggle_pause()
        self.update_display()

    def on_skip_break(self):
        from .hooks import log_runtime_event
        log_runtime_event("NATIVE_QT_CLICK: skip_break")
        self.engine.skip_to_break()
        self.update_display()

    def on_reset_phase(self):
        from .hooks import log_runtime_event
        log_runtime_event("NATIVE_QT_CLICK: reset_phase")
        self.engine.reset_current_phase()
        self.update_display()

    def on_toggle_focus(self):
        from .hooks import toggle_focus_fullscreen, log_runtime_event
        log_runtime_event("NATIVE_QT_CLICK: toggle_focus")
        toggle_focus_fullscreen()
        self.update_display()

    def on_open_config(self):
        from .hooks import show_pomodoro_config_dialog, log_runtime_event
        log_runtime_event("NATIVE_QT_CLICK: open_config")
        show_pomodoro_config_dialog()
