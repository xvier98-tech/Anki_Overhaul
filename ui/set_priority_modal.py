# -*- coding: utf-8 -*-
"""
Quick modal dialog to set or clear priority for a single deck.
"""

from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QSpinBox,
        QPushButton,
        QRadioButton,
        QButtonGroup,
        QGroupBox,
    )
    from PyQt6.QtCore import Qt
    from aqt import mw
except ImportError:
    # Standalone mock for testing environment without PyQt6
    QDialog = object
    mw = None

from ..utils.config_manager import get_deck_priorities, set_deck_priority, get_config
from ..core.hierarchy import build_deck_tree
from ..core.reorder import run_reorder_with_ui


class SetPriorityModal(QDialog):
    """Dialog for editing priority of a single deck."""

    def __init__(self, parent, deck_id: int, on_saved=None):
        super().__init__(parent)
        self.deck_id = deck_id
        self.on_saved = on_saved
        self.setWindowTitle("Definir Prioridade do Baralho")
        self.setMinimumWidth(380)

        self._setup_data()
        self._setup_ui()

    def _setup_data(self):
        self.deck_name = "Baralho Desconhecido"
        self.current_manual_priority: Optional[int] = None
        self.effective_priority: int = 100

        if mw and mw.col:
            raw_deck = mw.col.decks.get(self.deck_id)
            if raw_deck:
                self.deck_name = raw_deck.get("name", self.deck_name)

            priorities = get_deck_priorities()
            self.current_manual_priority = priorities.get(self.deck_id)

            config = get_config()
            def_prio = int(config.get("default_priority", 100))
            deck_tree = build_deck_tree(mw.col.decks.all(), priorities, def_prio)
            node = deck_tree.get(self.deck_id)
            if node:
                self.effective_priority = node.effective_priority

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Deck Title Label
        title_label = QLabel(f"<b>Baralho:</b> {self.deck_name}")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Status info
        if self.current_manual_priority is not None:
            status_text = f"Prioridade manual atual: <b>{self.current_manual_priority}</b>"
        else:
            status_text = f"Prioridade herdada atual: <b>{self.effective_priority}</b> (Herança automática)"
        status_label = QLabel(status_text)
        layout.addWidget(status_label)

        # Group box for priority choice
        group = QGroupBox("Configuração de Prioridade")
        group_layout = QVBoxLayout(group)

        self.btn_group = QButtonGroup(self)

        # Radio Manual
        self.radio_manual = QRadioButton("Definir prioridade manual:")
        self.btn_group.addButton(self.radio_manual)
        group_layout.addWidget(self.radio_manual)

        # SpinBox for numeric priority
        spin_layout = QHBoxLayout()
        spin_layout.setContentsMargins(20, 0, 0, 0)
        self.spin_priority = QSpinBox()
        self.spin_priority.setRange(1, 99999)
        self.spin_priority.setValue(
            self.current_manual_priority
            if self.current_manual_priority is not None
            else self.effective_priority
        )
        spin_layout.addWidget(self.spin_priority)
        hint_label = QLabel("<small>(1 = Maior prioridade / Estuda primeiro)</small>")
        spin_layout.addWidget(hint_label)
        spin_layout.addStretch()
        group_layout.addLayout(spin_layout)

        # Radio Inherit
        self.radio_inherit = QRadioButton("Herdar prioridade do baralho-pai (Remover manual)")
        self.btn_group.addButton(self.radio_inherit)
        group_layout.addWidget(self.radio_inherit)

        if self.current_manual_priority is not None:
            self.radio_manual.setChecked(True)
        else:
            self.radio_inherit.setChecked(True)

        self.radio_manual.toggled.connect(self._on_radio_toggled)
        self._on_radio_toggled()

        layout.addWidget(group)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Salvar")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save_only)

        self.btn_save_and_reorder = QPushButton("Salvar e Reordenar")
        self.btn_save_and_reorder.clicked.connect(self._save_and_reorder)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_save_and_reorder)
        layout.addLayout(btn_layout)

    def _on_radio_toggled(self):
        self.spin_priority.setEnabled(self.radio_manual.isChecked())

    def _apply_changes(self):
        if self.radio_manual.isChecked():
            val = self.spin_priority.value()
            set_deck_priority(self.deck_id, val)
        else:
            set_deck_priority(self.deck_id, None)

        if self.on_saved:
            self.on_saved()

    def _save_only(self):
        self._apply_changes()
        self.accept()
        run_reorder_with_ui(parent_widget=self.parent(), interactive=False)

    def _save_and_reorder(self):
        self._apply_changes()
        self.accept()
        run_reorder_with_ui(parent_widget=self.parent(), interactive=True)
