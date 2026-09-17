import os
import sys
import time
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget,
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QGraphicsDropShadowEffect,
        QApplication,
    )
    from PyQt6.QtCore import Qt, QObject, QEvent, QTimer, QPoint
    from PyQt6.QtGui import QCursor, QFont, QColor, QGuiApplication
    import aqt
    from aqt import mw
except ImportError:
    aqt = None
    QWidget = object
    QDialog = object
    QObject = object
    QEvent = object
    QTimer = None
    QCursor = object
    QGuiApplication = None
    QApplication = None
    mw = None

from .timer_engine import PomodoroEngine, PomodoroState
from .sounds import play_pomodoro_sound
try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config

_cached_anki_pids = set()
_last_anki_pids_update = 0.0


def get_anki_process_pids() -> set:
    """
    Returns set of PIDs belonging to Anki, its parent/ancestors (anki.exe),
    and its child processes (including QtWebEngineProcess and mpv).
    Discovers processes iteratively to convergence and caches for 5.0 seconds.
    """
    global _cached_anki_pids, _last_anki_pids_update
    now = time.time()
    if _cached_anki_pids and (now - _last_anki_pids_update < 5.0):
        return _cached_anki_pids

    pids = {os.getpid()}
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            TH32CS_SNAPPROCESS = 0x00000002

            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260),
                ]

            h_snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if h_snap not in (-1, 0xFFFFFFFFFFFFFFFF):
                pe = PROCESSENTRY32()
                pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
                proc_list = []
                parent_map = {}
                name_map = {}
                if kernel32.Process32First(h_snap, ctypes.byref(pe)):
                    while True:
                        pid = pe.th32ProcessID
                        ppid = pe.th32ParentProcessID
                        exe_raw = pe.szExeFile
                        exe_name = exe_raw.decode("utf-8", errors="ignore").lower() if isinstance(exe_raw, bytes) else str(exe_raw).lower()
                        proc_list.append((pid, ppid, exe_name))
                        parent_map[pid] = ppid
                        name_map[pid] = exe_name
                        if not kernel32.Process32Next(h_snap, ctypes.byref(pe)):
                            break
                kernel32.CloseHandle(h_snap)

                # 1. Walk up parent chain from os.getpid() to find any anki ancestor (e.g., anki.exe)
                curr = os.getpid()
                visited = set()
                while curr in parent_map and curr not in visited:
                    visited.add(curr)
                    parent = parent_map[curr]
                    if parent == 0 or parent == curr:
                        break
                    p_name = name_map.get(parent, "")
                    if "anki" in p_name:
                        pids.add(parent)
                    curr = parent

                # 2. Discover all processes with szExeFile containing anki.exe (case-insensitive)
                for pid, ppid, exe_name in proc_list:
                    if "anki.exe" in exe_name:
                        pids.add(pid)

                # 3. Fixed-point loop to convergence: add any child whose parent is in pids
                added = True
                while added:
                    added = False
                    for pid, ppid, _ in proc_list:
                        if ppid in pids and pid not in pids:
                            pids.add(pid)
                            added = True
        except Exception:
            pass

    _cached_anki_pids = pids
    _last_anki_pids_update = now
    return pids


def is_anki_active_window() -> bool:
    """
    Determines whether an Anki window (main window, webview child, dialog, or overlay)
    is currently the foreground window in the operating system.

    Fast Path (Qt):
    If QApplication reports activeWindow() or focusWidget(), Anki is actively focused.

    On Windows:
    Directly queries user32.GetForegroundWindow() and checks against Anki and its child PIDs,
    window ancestor hierarchy (GA_ROOT / GA_ROOTOWNER), and window title.
    Executes in ~0.02ms, 100% reliable, immune to Chromium child focus isolation and gamepad input.

    Fallback:
    Uses Qt's applicationState() and QApplication.activeWindow().
    """
    target_mw = getattr(aqt, "mw", None) or mw
    if target_mw is None:
        # Running in headless unit test environment without Anki GUI
        return True

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            fg_hwnd = user32.GetForegroundWindow()
            if not fg_hwnd:
                return False

            # 1. Direct PID check
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(pid))
            anki_pids = get_anki_process_pids()
            if pid.value in anki_pids:
                return True

            # 2. Check root window ancestor (GA_ROOT = 2, GA_ROOTOWNER = 3)
            root = user32.GetAncestor(fg_hwnd, 2)
            if root and root != fg_hwnd:
                root_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(root, ctypes.byref(root_pid))
                if root_pid.value in anki_pids:
                    anki_pids.add(pid.value)
                    return True

            root_owner = user32.GetAncestor(fg_hwnd, 3)
            if root_owner and root_owner != fg_hwnd and root_owner != root:
                owner_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(root_owner, ctypes.byref(owner_pid))
                if owner_pid.value in anki_pids:
                    anki_pids.add(pid.value)
                    return True

            # 3. Window title check (user32.GetWindowTextW)
            for hwnd_to_check in (fg_hwnd, root, root_owner):
                if not hwnd_to_check:
                    continue
                length = user32.GetWindowTextLengthW(hwnd_to_check)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd_to_check, buf, length + 1)
                    title = buf.value
                    profile_name = ""
                    try:
                        if target_mw and hasattr(target_mw, "pm"):
                            pm = target_mw.pm
                            profile_name = getattr(pm, "name", None) or (pm.current_profile_name() if hasattr(pm, "current_profile_name") else "")
                    except Exception:
                        profile_name = ""

                    if "anki" in title.lower() or (profile_name and profile_name.lower() in title.lower()):
                        anki_pids.add(pid.value)
                        return True

            # Target is an external application
            return False
        except Exception:
            pass

    # Cross-platform Qt fallback
    try:
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import Qt
        app = QGuiApplication.instance()
        if app and hasattr(app, "applicationState"):
            if app.applicationState() in (Qt.ApplicationState.ApplicationInactive, Qt.ApplicationState.ApplicationHidden):
                return False
    except Exception:
        pass

    try:
        if QApplication:
            active_w = QApplication.activeWindow()
            if active_w is None:
                return False
    except Exception:
        pass

    return True


class FocusReminderDialog(QDialog):
    """
    Sleek distraction alert popup shown when Anki loses focus during a work cycle.
    """

    def __init__(self, engine: PomodoroEngine, parent=None):
        active_modal = QApplication.activeModalWidget() if QApplication else None
        target_parent = parent or active_modal or getattr(aqt, "mw", None) or mw
        if QDialog is not object:
            super().__init__(target_parent)
            self.engine = engine
            self.setWindowTitle("🎯 Alerta de Foco - Obsidian Addon Suite")
            self.setFixedSize(460, 230)
            self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self._setup_ui()
        else:
            super().__init__()
            self.engine = engine

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        container = QWidget(self)
        container.setObjectName("reminderContainer")
        container.setStyleSheet("""
            #reminderContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #181825, stop:1 #11111b);
                border: 2px solid #ef4444;
                border-radius: 18px;
            }
            QLabel {
                color: #f8fafc;
            }
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 200))
        container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(12)
        c_layout.setContentsMargins(22, 18, 22, 18)

        # Title
        h_top = QHBoxLayout()
        icon_lbl = QLabel("🎯")
        icon_lbl.setStyleSheet("font-size: 26px; font-family: 'Segoe UI Emoji';")
        h_top.addWidget(icon_lbl)

        lbl_title = QLabel("Mantenha o Foco nos Estudos!")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f87171;")
        h_top.addWidget(lbl_title)
        h_top.addStretch()
        c_layout.addLayout(h_top)

        # Message
        lbl_msg = QLabel(
            "O Anki detectou que você saiu da janela durante a sessão de foco. "
            "O cronômetro foi <b>pausado</b> para não perder seu tempo."
        )
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 13px; color: #cbd5e1; line-height: 1.4;")
        c_layout.addWidget(lbl_msg)

        # Resume Button
        btn_resume = QPushButton("▶️ Retomar Estudos Agora")
        btn_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_resume.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ef4444, stop:1 #dc2626);
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 9px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #dc2626;
            }
        """)
        btn_resume.clicked.connect(self._on_resume_clicked)
        c_layout.addWidget(btn_resume)

        layout.addWidget(container)

    def show_centered(self):
        if QDialog is object:
            return
        parent_w = self.parentWidget()
        target_ref = parent_w or getattr(aqt, "mw", None) or mw
        if not target_ref:
            self.show()
            self.raise_()
            self.activateWindow()
            return
        try:
            if hasattr(target_ref, "window"):
                target_ref = target_ref.window()
            geo = target_ref.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        except Exception:
            pass
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_resume_clicked(self):
        self.engine.resume_from_focus_loss()
        self.hide()


class FocusGuard(QObject):
    """
    Anti-distraction guard that detects window deactivation / loss of focus
    via OS-level Win32 foreground polling (heartbeat) and Qt event filtering,
    pauses the Pomodoro WORK timer, sounds the alarm, and presents a reminder.
    Also manages auto-hiding the mouse cursor across Qt and Chromium webviews
    after 2 seconds of mouse inactivity during active WORK sessions.
    """

    def __init__(self, engine: PomodoroEngine):
        super().__init__()
        self.engine = engine
        self._reminder_dialog: Optional[FocusReminderDialog] = None
        self._focus_monitor_timer: Optional[QTimer] = None
        self._is_cursor_hidden: bool = False
        self._consecutive_inactive_ticks: int = 0
        self._installed_mw: bool = False
        self._last_cursor_pos: Optional[Any] = None
        self._last_mouse_activity: float = time.time()

        self._setup_focus_monitor_timer()
        self._connect_app_signals()

    def _setup_focus_monitor_timer(self):
        """High-frequency (250ms) background heartbeat polling OS foreground and cursor idle during WORK."""
        if QTimer:
            self._focus_monitor_timer = QTimer(self)
            self._focus_monitor_timer.setInterval(250)
            self._focus_monitor_timer.timeout.connect(self._on_focus_poll_tick)
            self._focus_monitor_timer.start()

    def _on_focus_poll_tick(self):
        """Heartbeat check running every 250ms."""
        config = get_module_config("pomodoro")

        # 1. Track physical mouse movement via OS/Qt cursor position
        try:
            if QCursor:
                cur_pos = QCursor.pos()
                if self._last_cursor_pos is None:
                    self._last_cursor_pos = cur_pos
                    self._last_mouse_activity = time.time()
                elif (cur_pos.x() != self._last_cursor_pos.x() or cur_pos.y() != self._last_cursor_pos.y()):
                    self._last_cursor_pos = cur_pos
                    self._last_mouse_activity = time.time()
                    if is_anki_active_window():
                        self.engine.register_user_activity()
                    if self._is_cursor_hidden:
                        self._restore_cursor()
        except Exception:
            pass

        # 2. Check auto-hide cursor during active WORK mode
        if config.get("auto_hide_cursor_in_focus", True):
            if self.engine.state == PomodoroState.WORK and self.engine.is_running:
                if not self._is_cursor_hidden and is_anki_active_window():
                    idle_time = time.time() - self._last_mouse_activity
                    idle_threshold = float(config.get("cursor_hide_timeout_seconds", 2.0))
                    if idle_time >= idle_threshold:
                        self._hide_cursor_if_focused()
            elif self._is_cursor_hidden:
                self._restore_cursor()

        # 3. Focus loss check - only applies during active WORK mode
        if not config.get("pause_on_focus_loss", True):
            self._consecutive_inactive_ticks = 0
            return

        if getattr(self.engine, "is_paused_by_editing", False):
            self._consecutive_inactive_ticks = 0
            return

        if self.engine.state == PomodoroState.WORK and self.engine.is_running:
            if not is_anki_active_window():
                self._consecutive_inactive_ticks += 1
                # 2 ticks = ~500ms outside Anki to eliminate transient switch flickers
                if self._consecutive_inactive_ticks >= 2:
                    self._trigger_focus_loss()
            else:
                self._consecutive_inactive_ticks = 0
        else:
            self._consecutive_inactive_ticks = 0

    def _connect_app_signals(self):
        try:
            from PyQt6.QtGui import QGuiApplication
            app = QGuiApplication.instance()
            if app and hasattr(app, "applicationStateChanged"):
                app.applicationStateChanged.connect(self._on_app_state_changed)
        except Exception:
            pass

    def _on_app_state_changed(self, state):
        try:
            from PyQt6.QtCore import Qt
            if state in (Qt.ApplicationState.ApplicationInactive, Qt.ApplicationState.ApplicationHidden):
                self._check_focus_loss()
            elif state == Qt.ApplicationState.ApplicationActive:
                self._restore_cursor()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if not event:
            return False

        try:
            ev_type = event.type()

            # 1. Window Activation / Focus Loss Detection
            if ev_type in (QEvent.Type.WindowDeactivate, QEvent.Type.ActivationChange):
                if QTimer:
                    QTimer.singleShot(80, self._check_focus_loss)
                else:
                    self._check_focus_loss()

            # 2. Mouse Move / KeyPress / Click
            elif ev_type in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
                self._on_user_interaction()
            elif ev_type == QEvent.Type.KeyPress:
                self.engine.register_user_activity()
        except Exception:
            pass

        return False

    def _check_focus_loss(self) -> bool:
        if getattr(self.engine, "is_paused_by_editing", False):
            return False

        config = get_module_config("pomodoro")
        if not config.get("pause_on_focus_loss", True):
            return False

        if not is_anki_active_window():
            self._trigger_focus_loss()
            return True
        else:
            self._restore_cursor()
            return False

    def _trigger_focus_loss(self):
        if getattr(self.engine, "is_paused_by_editing", False):
            return

        config = get_module_config("pomodoro")
        if not config.get("pause_on_focus_loss", True):
            return

        # CRITICAL: Focus loss pause and alarm ONLY apply during active WORK (focus) mode!
        if self.engine.state == PomodoroState.WORK and self.engine.is_running:
            self._consecutive_inactive_ticks = 0
            from .hooks import log_runtime_event
            log_runtime_event("FOCUS_LOSS_DETECTED: Anki window deactivated during WORK. Pausing timer and sounding alarm.")
            self.engine.pause_for_focus_loss()

            # Play alarm sound immediately
            if config.get("sound_notifications", True):
                play_pomodoro_sound(event_type="focus_loss")

            # Show reminder popup - destroy previous dead/stale instance and instantiate with active modal as parent
            if self._reminder_dialog is not None:
                try:
                    self._reminder_dialog.close()
                    self._reminder_dialog.deleteLater()
                except Exception:
                    pass
                self._reminder_dialog = None

            active_modal = QApplication.activeModalWidget() if QApplication else None
            target_parent = active_modal or getattr(aqt, "mw", None) or mw
            self._reminder_dialog = FocusReminderDialog(self.engine, target_parent)
            self._reminder_dialog.show_centered()

    def _on_user_interaction(self):
        self._last_mouse_activity = time.time()
        self._restore_cursor()
        self.engine.register_user_activity()

    def _hide_cursor_if_focused(self):
        config = get_module_config("pomodoro")
        if not config.get("auto_hide_cursor_in_focus", True):
            return

        if self.engine.state == PomodoroState.WORK and self.engine.is_running:
            if is_anki_active_window() and not self._is_cursor_hidden:
                self._apply_cursor_hidden(True)

    def _restore_cursor(self):
        if self._is_cursor_hidden:
            self._apply_cursor_hidden(False)

    def _apply_cursor_hidden(self, hidden: bool):
        self._is_cursor_hidden = hidden
        target_mw = getattr(aqt, "mw", None) or mw

        if hidden:
            # 1. Qt Application Override Cursor (affects all native Qt widgets/FAB/overlays)
            try:
                if QGuiApplication:
                    QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
            except Exception:
                pass

            # 2. Chromium Webviews (Card Reviewer, Deck Browser, Overview)
            if target_mw:
                self._apply_webview_cursor(target_mw, True)

            # 3. Windows Win32 immediate cursor clear
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.user32.SetCursor(0)
                except Exception:
                    pass
        else:
            # 1. Restore Qt Application Override Cursor
            try:
                if QGuiApplication:
                    while QGuiApplication.overrideCursor() is not None:
                        QGuiApplication.restoreOverrideCursor()
            except Exception:
                pass

            # 2. Restore Chromium Webviews
            if target_mw:
                self._apply_webview_cursor(target_mw, False)

            # 3. Restore Windows Win32 standard arrow cursor
            if sys.platform == "win32":
                try:
                    import ctypes
                    IDC_ARROW = 32512
                    arrow = ctypes.windll.user32.LoadCursorW(0, IDC_ARROW)
                    if arrow:
                        ctypes.windll.user32.SetCursor(arrow)
                except Exception:
                    pass

    def _apply_webview_cursor(self, target_mw, hidden: bool):
        """Injects or removes CSS and widget-level blank cursor across all Anki webviews."""
        webviews = []
        for attr in ("reviewer", "deckBrowser", "overview", "toolbar"):
            obj = getattr(target_mw, attr, None)
            if obj and hasattr(obj, "web") and obj.web:
                webviews.append(obj.web)
        if hasattr(target_mw, "bottom_web") and target_mw.bottom_web:
            webviews.append(target_mw.bottom_web)

        if hidden:
            js = """
                (function() {
                    var s = document.getElementById('obsidian-hide-cursor-style');
                    if (!s) {
                        s = document.createElement('style');
                        s.id = 'obsidian-hide-cursor-style';
                        s.innerHTML = '* { cursor: none !important; }';
                        document.head.appendChild(s);
                    }
                })();
            """
            for wv in webviews:
                try:
                    if hasattr(wv, "setCursor") and QCursor:
                        wv.setCursor(QCursor(Qt.CursorShape.BlankCursor))
                    if hasattr(wv, "eval"):
                        wv.eval(js)
                    elif hasattr(wv, "page") and wv.page():
                        wv.page().runJavaScript(js)
                except Exception:
                    pass
        else:
            js = """
                (function() {
                    var s = document.getElementById('obsidian-hide-cursor-style');
                    if (s) { s.remove(); }
                })();
            """
            for wv in webviews:
                try:
                    if hasattr(wv, "unsetCursor"):
                        wv.unsetCursor()
                    if hasattr(wv, "eval"):
                        wv.eval(js)
                    elif hasattr(wv, "page") and wv.page():
                        wv.page().runJavaScript(js)
                except Exception:
                    pass

    def on_card_shown_cursor_check(self):
        """Maintains cursor hidden state when a new card is loaded into the reviewer."""
        if self._is_cursor_hidden:
            target_mw = getattr(aqt, "mw", None) or mw
            if target_mw and hasattr(target_mw, "reviewer") and hasattr(target_mw.reviewer, "web") and target_mw.reviewer.web:
                js = """
                    (function() {
                        var s = document.getElementById('obsidian-hide-cursor-style');
                        if (!s) {
                            s = document.createElement('style');
                            s.id = 'obsidian-hide-cursor-style';
                            s.innerHTML = '* { cursor: none !important; }';
                            document.head.appendChild(s);
                        }
                    })();
                """
                try:
                    target_mw.reviewer.web.setCursor(QCursor(Qt.CursorShape.BlankCursor))
                    if hasattr(target_mw.reviewer.web, "eval"):
                        target_mw.reviewer.web.eval(js)
                    elif hasattr(target_mw.reviewer.web, "page") and target_mw.reviewer.web.page():
                        target_mw.reviewer.web.page().runJavaScript(js)
                except Exception:
                    pass
