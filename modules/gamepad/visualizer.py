# -*- coding: utf-8 -*-
"""
Real-time Gamepad Tester & Visualizer Component for Anki Desktop.
Displays live button states (B0..B17), dual analog stick 2D radar visualizers (AXIS 0..3),
radial deadzone indicator, and continuous reviewer scroll telemetry.
Inspired by hardwaretester.com/gamepad.
"""

import time
import math
from typing import Dict, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QGridLayout,
        QLabel,
        QGroupBox,
        QFrame,
    )
    from PyQt6.QtCore import Qt, QPointF
    from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
except ImportError:
    class QWidget:
        def __init__(self, *args, **kwargs):
            pass
        def setMinimumSize(self, *a): pass
        def setMaximumSize(self, *a): pass
        def setFixedWidth(self, *a): pass
        def setFixedHeight(self, *a): pass
        def setObjectName(self, *a): pass
        def setStyleSheet(self, *a): pass
        def setToolTip(self, *a): pass
        def addWidget(self, *a): pass
        def addLayout(self, *a): pass
        def addStretch(self, *a): pass
        def setContentsMargins(self, *a): pass
        def setSpacing(self, *a): pass
        def update(self): pass

    class QFrame(QWidget): pass
    class QGroupBox(QWidget): pass
    class QLabel(QWidget):
        def __init__(self, *args, **kwargs):
            self.text = args[0] if args else ""
        def setText(self, *a): pass
    class QVBoxLayout(QWidget): pass
    class QHBoxLayout(QWidget): pass
    class QGridLayout(QWidget): pass
    Qt = object


class AnalogStickRadarWidget(QWidget):
    """
    2D Circular Radar widget rendering live stick positions with crosshairs,
    deadzone radius indicator, and normalized deflection coordinates.
    """

    def __init__(self, stick_name: str = "STICK", parent=None):
        super().__init__(parent)
        self.stick_name = stick_name
        self.x_val: float = 0.0
        self.y_val: float = 0.0
        self.deadzone: float = 0.15
        self.setMinimumSize(90, 90)
        self.setMaximumSize(115, 115)

    def set_values(self, x: float, y: float, deadzone: float):
        self.x_val = max(-1.0, min(1.0, x))
        self.y_val = max(-1.0, min(1.0, y))
        self.deadzone = max(0.0, min(1.0, deadzone))
        if hasattr(self, "update"):
            self.update()

    def paintEvent(self, event):
        if not hasattr(self, "width"):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        size = min(w, h) - 12
        cx, cy = w / 2.0, h / 2.0
        radius = size / 2.0

        # 1. Outer Circle Background
        bg_brush = QBrush(QColor(15, 23, 42, 180))  # dark slate semi-transparent
        circle_pen = QPen(QColor(71, 85, 105, 140), 1.5)
        painter.setBrush(bg_brush)
        painter.setPen(circle_pen)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # 2. Deadzone Boundary (Dashed circle)
        if self.deadzone > 0:
            dz_pen = QPen(QColor(239, 68, 68, 120), 1.0, Qt.PenStyle.DashLine)
            painter.setPen(dz_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), radius * self.deadzone, radius * self.deadzone)

        # 3. Crosshairs
        cross_pen = QPen(QColor(100, 116, 139, 120), 1.0)
        painter.setPen(cross_pen)
        painter.drawLine(int(cx - radius), int(cy), int(cx + radius), int(cy))
        painter.drawLine(int(cx), int(cy - radius), int(cx), int(cy + radius))

        # 4. Dot position (Invert Y because screen coordinates +Y is DOWN, stick +Y is UP)
        dot_x = cx + (self.x_val * radius)
        dot_y = cy - (self.y_val * radius)

        mag = math.hypot(self.x_val, self.y_val)
        is_active = mag > self.deadzone

        # Dot color: Cyan if out of deadzone (active), muted gray if idle
        dot_color = QColor(56, 189, 248) if is_active else QColor(148, 163, 184)
        dot_pen = QPen(QColor(255, 255, 255), 1.5) if is_active else QPen(QColor(100, 116, 139), 1.0)

        painter.setPen(dot_pen)
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(QPointF(dot_x, dot_y), 5.5, 5.5)

        painter.end()


class ButtonTelemetryCard(QFrame):
    """
    HD Button indicator card displaying label (e.g. B0 (A)) and float value (0.00 / 1.00),
    with an accent bar that illuminates on activation without 60Hz stylesheet thrashing.
    """

    def __init__(self, btn_id: str, label_hint: str = "", display_title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("btn_card")
        self.btn_id = btn_id
        self.label_hint = label_hint
        self.display_title = display_title if display_title else btn_id
        self.current_val: float = 0.0

        # Expanded HD dimensions: plenty of width and height for full font metrics
        self.card_width = 84
        self.card_height = 54
        self.setFixedWidth(self.card_width)
        self.setFixedHeight(self.card_height)

        self._is_pressed: Optional[bool] = None
        self._last_val_str: str = ""

        self._setup_ui()
        self._update_card_style(False)
        self.set_value(0.0)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 5, 7, 5)
        layout.setSpacing(6)

        # Left vertical accent line
        self.bar = QFrame()
        self.bar.setFixedWidth(3)
        self.bar.setStyleSheet("background: #334155; border-radius: 1px;")
        layout.addWidget(self.bar)

        # Vertical text content: Label on top, Value below
        v_box = QVBoxLayout()
        v_box.setContentsMargins(0, 0, 0, 0)
        v_box.setSpacing(2)

        # 1. Button identifier label (fixed height 18px prevents clipping)
        self.lbl_id = QLabel(self.display_title)
        self.lbl_id.setFixedHeight(18)
        self.lbl_id.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8; font-family: 'Segoe UI', sans-serif;")
        if self.label_hint:
            self.setToolTip(f"{self.btn_id}: {self.label_hint}")

        # 2. Telemetry value label (fixed height 20px in monospace font prevents 0.00 clipping)
        self.lbl_val = QLabel("0.00")
        self.lbl_val.setFixedHeight(20)
        self.lbl_val.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc; font-family: 'Consolas', monospace;")

        v_box.addWidget(self.lbl_id)
        v_box.addWidget(self.lbl_val)
        layout.addLayout(v_box)

    def _update_card_style(self, pressed: bool):
        if pressed:
            self.setStyleSheet("""
                QFrame#btn_card {
                    background: rgba(56, 189, 248, 0.22);
                    border: 1px solid #38bdf8;
                    border-radius: 6px;
                }
            """)
            self.bar.setStyleSheet("background: #38bdf8; border-radius: 1px;")
            self.lbl_id.setStyleSheet("font-size: 11px; font-weight: bold; color: #38bdf8; font-family: 'Segoe UI', sans-serif;")
            self.lbl_val.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8; font-family: 'Consolas', monospace;")
        else:
            self.setStyleSheet("""
                QFrame#btn_card {
                    background: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 6px;
                }
            """)
            self.bar.setStyleSheet("background: #475569; border-radius: 1px;")
            self.lbl_id.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8; font-family: 'Segoe UI', sans-serif;")
            self.lbl_val.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc; font-family: 'Consolas', monospace;")

    def set_value(self, val: float):
        self.current_val = val
        is_pressed = val > 0.05
        str_val = f"{val:.2f}"

        # Performance & stability: only update label text if changed
        if str_val != self._last_val_str:
            self._last_val_str = str_val
            self.lbl_val.setText(str_val)

        # Only update stylesheet on state TRANSITION to eliminate 60Hz style reflow and font tearing
        if is_pressed != self._is_pressed:
            self._is_pressed = is_pressed
            self._update_card_style(is_pressed)


class GamepadTesterWidget(QGroupBox):
    """
    Comprehensive Live Gamepad Tester panel matching the visual architecture of Gamepad Tester.
    """

    BUTTON_SPECS = [
        # (ID, Standard Name, PS Name, Display Tag)
        ("B0", "A", "✕ Cross", "A"),
        ("B1", "B", "◯ Circle", "B"),
        ("B2", "X", "◻ Square", "X"),
        ("B3", "Y", "△ Triangle", "Y"),
        ("B4", "LB", "L1 Bumper", "LB"),
        ("B5", "RB", "R1 Bumper", "RB"),
        ("B6", "LT", "L2 Trigger", "LT"),
        ("B7", "RT", "R2 Trigger", "RT"),
        ("B8", "BACK", "Share / Back", "Back"),
        ("B9", "START", "Options / Start", "Start"),
        ("B10", "L3", "L3 Click", "L3"),
        ("B11", "R3", "R3 Click", "R3"),
        ("B12", "DPAD_UP", "D-Pad Cima", "Up"),
        ("B13", "DPAD_DOWN", "D-Pad Baixo", "Down"),
        ("B14", "DPAD_LEFT", "D-Pad Esquerda", "Left"),
        ("B15", "DPAD_RIGHT", "D-Pad Direita", "Right"),
        ("B16", "GUIDE", "PS / Home / Mode", "Guide"),
        ("B17", "TOUCHPAD", "Touchpad / Capture", "Pad"),
    ]

    def __init__(self, parent=None):
        super().__init__("🎮 Testador em Tempo Real (Gamepad Tester)", parent)
        self.button_cards: Dict[str, ButtonTelemetryCard] = {}
        self._start_time = time.time()
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 1. Telemetry Header Stats
        h_header = QHBoxLayout()
        h_header.setSpacing(18)

        self.lbl_stat_index = self._create_stat_widget("INDEX", "0")
        self.lbl_stat_conn = self._create_stat_widget("CONNECTED", "No")
        self.lbl_stat_mapping = self._create_stat_widget("MAPPING", "Standard")
        self.lbl_stat_timestamp = self._create_stat_widget("TIMESTAMP", "0.00000")
        self.lbl_stat_driver = self._create_stat_widget("DRIVER", "Universal")

        h_header.addLayout(self.lbl_stat_index)
        h_header.addLayout(self.lbl_stat_conn)
        h_header.addLayout(self.lbl_stat_mapping)
        h_header.addLayout(self.lbl_stat_timestamp)
        h_header.addLayout(self.lbl_stat_driver)
        h_header.addStretch()

        main_layout.addLayout(h_header)

        # 2. Buttons Telemetry Grid (2 rows of 9 cards: B0-B8 and B9-B17)
        grp_buttons = QFrame()
        grp_buttons.setStyleSheet("background: rgba(15, 23, 42, 0.2); border-radius: 6px; padding: 4px;")
        grid_buttons = QGridLayout(grp_buttons)
        grid_buttons.setContentsMargins(6, 6, 6, 6)
        grid_buttons.setSpacing(6)

        for i, (b_id, norm_name, ps_name, disp_tag) in enumerate(self.BUTTON_SPECS):
            row = i // 9
            col = i % 9
            disp_title = f"{b_id} · {disp_tag}"
            card = ButtonTelemetryCard(b_id, label_hint=f"{norm_name} ({ps_name})", display_title=disp_title)
            self.button_cards[norm_name] = card
            # also map by b_id for direct lookup
            self.button_cards[b_id] = card
            grid_buttons.addWidget(card, row, col)

        main_layout.addWidget(grp_buttons)

        # 3. Dual Analog Sticks & Axes Section
        h_sticks = QHBoxLayout()
        h_sticks.setSpacing(20)

        # Left Stick Panel
        h_sticks.addWidget(self._build_stick_panel("L STICK", 0, 1, is_left=True))
        # Right Stick Panel
        h_sticks.addWidget(self._build_stick_panel("R STICK", 2, 3, is_left=False))

        main_layout.addLayout(h_sticks)

        # 4. Scroll Telemetry Banner
        self.bar_scroll = QFrame()
        self.bar_scroll.setStyleSheet("""
            QFrame {
                background: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(71, 85, 105, 0.3);
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        h_scroll = QHBoxLayout(self.bar_scroll)
        h_scroll.setContentsMargins(8, 4, 8, 4)

        self.lbl_scroll_icon = QLabel("⚪")
        h_scroll.addWidget(self.lbl_scroll_icon)

        self.lbl_scroll_status = QLabel("Rolagem: Parado (Dentro da Zona Morta)")
        self.lbl_scroll_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8;")
        h_scroll.addWidget(self.lbl_scroll_status)
        h_scroll.addStretch()

        self.lbl_scroll_rate = QLabel("0.0 px/frame")
        self.lbl_scroll_rate.setStyleSheet("font-size: 11px; font-family: monospace; color: #64748b;")
        h_scroll.addWidget(self.lbl_scroll_rate)

        main_layout.addWidget(self.bar_scroll)

    def _create_stat_widget(self, title: str, init_val: str) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(1)
        v.setContentsMargins(0, 0, 0, 0)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748b; letter-spacing: 0.5px;")
        lbl_v = QLabel(init_val)
        lbl_v.setStyleSheet("font-size: 12px; font-weight: bold; color: #e2e8f0; font-family: monospace;")
        v.addWidget(lbl_t)
        v.addWidget(lbl_v)
        v.val_label = lbl_v
        return v

    def _build_stick_panel(self, title: str, axis_h_id: int, axis_v_id: int, is_left: bool) -> QWidget:
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.25);
                border: 1px solid rgba(71, 85, 105, 0.3);
                border-radius: 6px;
            }
        """)
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(12)

        # Axes Text Stats
        v_axes = QVBoxLayout()
        v_axes.setSpacing(4)

        lbl_stick_title = QLabel(title)
        lbl_stick_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8;")
        v_axes.addWidget(lbl_stick_title)

        lbl_ax0_t = QLabel(f"AXIS {axis_h_id}")
        lbl_ax0_t.setStyleSheet("font-size: 9px; font-weight: bold; color: #64748b;")
        lbl_ax0_v = QLabel("0.00000")
        lbl_ax0_v.setStyleSheet("font-size: 11px; font-family: monospace; color: #e2e8f0; font-weight: bold;")
        v_axes.addWidget(lbl_ax0_t)
        v_axes.addWidget(lbl_ax0_v)

        lbl_ax1_t = QLabel(f"AXIS {axis_v_id}")
        lbl_ax1_t.setStyleSheet("font-size: 9px; font-weight: bold; color: #64748b;")
        lbl_ax1_v = QLabel("0.00000")
        lbl_ax1_v.setStyleSheet("font-size: 11px; font-family: monospace; color: #e2e8f0; font-weight: bold;")
        v_axes.addWidget(lbl_ax1_t)
        v_axes.addWidget(lbl_ax1_v)
        v_axes.addStretch()

        h_layout.addLayout(v_axes)

        # 2D Radar Canvas
        radar = AnalogStickRadarWidget(title)
        h_layout.addWidget(radar)

        if is_left:
            self.radar_left = radar
            self.lbl_axis0_val = lbl_ax0_v
            self.lbl_axis1_val = lbl_ax1_v
        else:
            self.radar_right = radar
            self.lbl_axis2_val = lbl_ax0_v
            self.lbl_axis3_val = lbl_ax1_v

        return container

    def update_telemetry(self, t: dict):
        """Called on every 16ms poll cycle to update the visualizer."""
        # 1. Header metrics
        is_conn = t.get("connected", False)
        self.lbl_stat_conn.val_label.setText("Yes" if is_conn else "No")
        self.lbl_stat_conn.val_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; font-family: monospace; color: #4ade80;"
            if is_conn else
            "font-size: 12px; font-weight: bold; font-family: monospace; color: #f87171;"
        )

        dev_name = t.get("device_name", "")
        if "PlayStation" in dev_name or "DirectInput" in dev_name:
            self.lbl_stat_driver.val_label.setText("DirectInput / PS")
        elif "XInput" in dev_name:
            self.lbl_stat_driver.val_label.setText("XInput")
        else:
            self.lbl_stat_driver.val_label.setText("Universal")

        now = (time.time() - self._start_time) * 1000.0
        self.lbl_stat_timestamp.val_label.setText(f"{now:.2f}")

        # 2. Buttons
        active_buttons = t.get("buttons", set())
        lt_val = t.get("left_trigger", 0.0)
        rt_val = t.get("right_trigger", 0.0)

        for b_id, norm_name, *rest in self.BUTTON_SPECS:
            card = self.button_cards.get(norm_name)
            if not card:
                continue

            if norm_name == "LT":
                val = lt_val if lt_val > 0 else (1.0 if "LT" in active_buttons else 0.0)
            elif norm_name == "RT":
                val = rt_val if rt_val > 0 else (1.0 if "RT" in active_buttons else 0.0)
            else:
                is_on = (norm_name in active_buttons or b_id in active_buttons)
                val = 1.0 if is_on else 0.0

            card.set_value(val)

        # 3. Sticks
        lx = t.get("thumb_lx", 0.0)
        ly = t.get("thumb_ly", 0.0)
        rx = t.get("thumb_rx", 0.0)
        ry = t.get("thumb_ry", 0.0)
        deadzone = t.get("deadzone", 0.15)

        self.lbl_axis0_val.setText(f"{lx:+.5f}")
        self.lbl_axis1_val.setText(f"{-ly:+.5f}")
        self.radar_left.set_values(lx, ly, deadzone)

        self.lbl_axis2_val.setText(f"{rx:+.5f}")
        self.lbl_axis3_val.setText(f"{-ry:+.5f}")
        self.radar_right.set_values(rx, ry, deadzone)

        # 4. Scroll Inspector
        scroll_delta = t.get("scroll_delta", 0.0)
        scroll_stick = t.get("scroll_stick", "right")
        stick_str = "R STICK" if scroll_stick == "right" else "L STICK"

        if abs(scroll_delta) > 0.01:
            arrow = "▲ Cima" if scroll_delta < 0 else "▼ Baixo"
            self.lbl_scroll_icon.setText("🟢")
            self.lbl_scroll_status.setText(f"Rolagem Ativa via {stick_str} ({arrow})")
            self.lbl_scroll_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #4ade80;")
            self.lbl_scroll_rate.setText(f"{scroll_delta:+.1f} px/frame")
            self.bar_scroll.setStyleSheet("""
                QFrame {
                    background: rgba(34, 197, 94, 0.12);
                    border: 1px solid rgba(34, 197, 94, 0.4);
                    border-radius: 6px;
                }
            """)
        else:
            self.lbl_scroll_icon.setText("⚪")
            self.lbl_scroll_status.setText(f"Rolagem: Parado (Monitorando {stick_str} | Deadzone: {int(deadzone*100)}%)")
            self.lbl_scroll_status.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8;")
            self.lbl_scroll_rate.setText("0.0 px/frame")
            self.bar_scroll.setStyleSheet("""
                QFrame {
                    background: rgba(30, 41, 59, 0.3);
                    border: 1px solid rgba(71, 85, 105, 0.25);
                    border-radius: 6px;
                }
            """)
