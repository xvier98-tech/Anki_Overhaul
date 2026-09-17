# -*- coding: utf-8 -*-
"""
UI Helpers and custom widget classes for Obsidian Suite.
Provides wheel-safe input widgets that ignore scroll-wheel changes unless explicitly focused/selected.
"""

try:
    from PyQt6.QtWidgets import QSlider, QComboBox, QSpinBox
    from PyQt6.QtCore import Qt
except ImportError:
    class _DummyWidget:
        def __init__(self, *args, **kwargs):
            self._items = []
            self._cur_idx = 0
            self._cur_data = ""
            self._val = 0
        def __getattr__(self, name):
            return _DummyWidget()
        def __call__(self, *args, **kwargs):
            return self
        def setFocusPolicy(self, *a): pass
        def hasFocus(self): return False
        def setValue(self, v): self._val = v
        def value(self): return self._val
        def text(self): return ""
        def addItem(self, text, data=None):
            self._items.append((text, data))
            if len(self._items) == 1:
                self._cur_data = data
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
        def blockSignals(self, b): pass
    QSlider = _DummyWidget
    QComboBox = _DummyWidget
    QSpinBox = _DummyWidget
    Qt = _DummyWidget()


class FocusWheelSlider(QSlider):
    """QSlider that ignores mouse wheel events unless explicitly clicked / focused."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(Qt, 'FocusPolicy'):
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class FocusWheelComboBox(QComboBox):
    """QComboBox that ignores mouse wheel events unless explicitly clicked / focused."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(Qt, 'FocusPolicy'):
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)


class FocusWheelSpinBox(QSpinBox):
    """QSpinBox that ignores mouse wheel events unless explicitly clicked / focused."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(Qt, 'FocusPolicy'):
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super().wheelEvent(event)
