# -*- coding: utf-8 -*-
"""
Main Management Dialog for Deck Priorities & Closed Block Sequencer.
"""

from typing import Dict, Optional

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QTreeWidget,
        QTreeWidgetItem,
        QLabel,
        QSpinBox,
        QPushButton,
        QCheckBox,
        QGroupBox,
        QHeaderView,
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QBrush
    from aqt import mw
except ImportError:
    QDialog = object
    mw = None

try:
    from ....utils.config_manager import (
        get_module_config,
        write_module_config,
        get_deck_priorities,
        set_deck_priority,
    )
except (ImportError, ValueError):
    from utils.config_manager import (
        get_module_config,
        write_module_config,
        get_deck_priorities,
        set_deck_priority,
    )
from ..hierarchy import build_deck_tree
from ..reorder import count_new_cards_by_deck, run_reorder_with_ui


class PriorityManagerDialog(QDialog):
    """Main window to manage deck priorities across the entire collection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciador de Prioridades e Estudo em Blocos Fechados")
        self.resize(780, 560)
        self.setMinimumSize(640, 440)

        self._setup_ui()
        self.refresh_deck_tree()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        header_text = (
            "<b>Defina os níveis de prioridade entre baralhos e sub-baralhos.</b><br>"
            "<small style='color: #666;'>O sistema garante o estudo em <b>blocos fechados</b>: "
            "100% dos cartões novos de um baralho são apresentados antes do próximo. "
            "Menor número = maior prioridade (ex: 1 antes de 2).</small>"
        )
        lbl_header = QLabel(header_text)
        lbl_header.setWordWrap(True)
        main_layout.addWidget(lbl_header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "Baralho / Sub-baralho",
            "Prioridade Manual",
            "Prioridade Efetiva",
            "Novos Cartões",
        ])
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.tree)

        editor_group = QGroupBox("Editar Baralho Selecionado")
        editor_layout = QHBoxLayout(editor_group)

        self.lbl_selected_deck = QLabel("<i>Nenhum baralho selecionado</i>")
        editor_layout.addWidget(self.lbl_selected_deck, stretch=1)

        editor_layout.addWidget(QLabel("Nova Prioridade:"))
        self.spin_priority = QSpinBox()
        self.spin_priority.setRange(1, 99999)
        self.spin_priority.setValue(10)
        self.spin_priority.setEnabled(False)
        if hasattr(self.spin_priority, "lineEdit") and callable(self.spin_priority.lineEdit):
            le = self.spin_priority.lineEdit()
            if le and hasattr(le, "returnPressed"):
                le.returnPressed.connect(self._apply_selected_priority)
        editor_layout.addWidget(self.spin_priority)

        self.btn_set_priority = QPushButton("Aplicar Prioridade")
        self.btn_set_priority.setEnabled(False)
        self.btn_set_priority.clicked.connect(self._apply_selected_priority)
        editor_layout.addWidget(self.btn_set_priority)

        self.btn_clear_priority = QPushButton("Limpar (Herdar do Pai)")
        self.btn_clear_priority.setEnabled(False)
        self.btn_clear_priority.clicked.connect(self._clear_selected_priority)
        editor_layout.addWidget(self.btn_clear_priority)

        main_layout.addWidget(editor_group)

        options_group = QGroupBox("Opções de Ordenação e Automação")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(6)

        config = get_module_config("priority_sequencer")

        self.chk_randomize_same = QCheckBox(
            "Desempatar baralhos de mesma prioridade aleatoriamente (mantendo blocos fechados)"
        )
        self.chk_randomize_same.setChecked(config.get("randomize_same_priority_decks", True))
        self.chk_randomize_same.stateChanged.connect(self._save_options)
        options_layout.addWidget(self.chk_randomize_same)

        self.chk_randomize_cards = QCheckBox(
            "Embaralhar cartões dentro do próprio baralho (ao invés de manter ordem de criação)"
        )
        self.chk_randomize_cards.setChecked(config.get("randomize_cards_within_deck", False))
        self.chk_randomize_cards.stateChanged.connect(self._save_options)
        options_layout.addWidget(self.chk_randomize_cards)

        auto_layout = QHBoxLayout()
        self.chk_auto_profile = QCheckBox("Reordenar automaticamente ao abrir o perfil")
        self.chk_auto_profile.setChecked(config.get("auto_reorder_on_profile_open", False))
        self.chk_auto_profile.stateChanged.connect(self._save_options)
        auto_layout.addWidget(self.chk_auto_profile)

        self.chk_auto_sync = QCheckBox("Reordenar automaticamente após sincronizar")
        self.chk_auto_sync.setChecked(config.get("auto_reorder_on_sync", False))
        self.chk_auto_sync.stateChanged.connect(self._save_options)
        auto_layout.addWidget(self.chk_auto_sync)
        options_layout.addLayout(auto_layout)

        main_layout.addWidget(options_group)

        bottom_layout = QHBoxLayout()
        self.lbl_stats = QLabel("Carregando estatísticas...")
        bottom_layout.addWidget(self.lbl_stats)

        bottom_layout.addStretch()

        self.btn_reorder_now = QPushButton("🚀 Reordenar Novos Cartões Agora")
        self.btn_reorder_now.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_reorder_now.clicked.connect(self._reorder_now)
        bottom_layout.addWidget(self.btn_reorder_now)

        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(self.btn_close)

        main_layout.addLayout(bottom_layout)

    def refresh_deck_tree(self):
        prev_did = self._get_selected_deck_id()
        self.tree.clear()
        if not mw or not mw.col:
            return

        raw_decks = mw.col.decks.all()
        priorities = get_deck_priorities()
        config = get_module_config("priority_sequencer")
        def_prio = int(config.get("default_priority", 100))
        new_counts = count_new_cards_by_deck(mw.col)

        self.deck_tree = build_deck_tree(
            raw_decks=raw_decks,
            explicit_priorities=priorities,
            default_priority=def_prio,
            new_card_counts=new_counts,
        )

        total_new_cards = sum(new_counts.values())
        self.lbl_stats.setText(f"Total de cartões novos na coleção: <b>{total_new_cards}</b>")

        items_by_id: Dict[int, QTreeWidgetItem] = {}

        for did, node in self.deck_tree.items():
            item = QTreeWidgetItem()
            parts = node.name.split("::")
            short_name = parts[-1]
            item.setText(0, short_name)
            item.setData(0, Qt.ItemDataRole.UserRole, did)

            if node.is_explicit:
                item.setText(1, str(node.explicit_priority))
                font = item.font(1)
                font.setBold(True)
                item.setFont(1, font)
            else:
                item.setText(1, "— (Herdada)")
                item.setForeground(1, QBrush(QColor(130, 130, 130)))

            item.setText(2, str(node.effective_priority))
            font2 = item.font(2)
            font2.setBold(True)
            item.setFont(2, font2)

            item.setText(3, str(node.new_card_count))
            if node.new_card_count > 0:
                item.setForeground(3, QBrush(QColor(0, 120, 215)))

            items_by_id[did] = item

        for did, node in self.deck_tree.items():
            item = items_by_id[did]
            if node.parent_id is not None and node.parent_id in items_by_id:
                items_by_id[node.parent_id].addChild(item)
            else:
                self.tree.addTopLevelItem(item)

        self.tree.expandAll()
        if prev_did is not None and prev_did in items_by_id:
            target_item = items_by_id[prev_did]
            target_item.setSelected(True)
            self.tree.setCurrentItem(target_item)
            self.tree.scrollToItem(target_item)
        self._on_selection_changed()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.tree.hasFocus():
                did = self._get_selected_deck_id()
                if did is not None:
                    from .set_priority_modal import SetPriorityModal
                    modal = SetPriorityModal(self, did, on_saved=self.refresh_deck_tree)
                    modal.exec()
                    return
        super().keyPressEvent(event)

    def _get_selected_deck_id(self) -> Optional[int]:
        selected = self.tree.selectedItems()
        if not selected:
            return None
        return selected[0].data(0, Qt.ItemDataRole.UserRole)

    def _on_selection_changed(self):
        did = self._get_selected_deck_id()
        if did is None or did not in self.deck_tree:
            self.lbl_selected_deck.setText("<i>Nenhum baralho selecionado</i>")
            self.spin_priority.setEnabled(False)
            self.btn_set_priority.setEnabled(False)
            self.btn_clear_priority.setEnabled(False)
            return

        node = self.deck_tree[did]
        self.lbl_selected_deck.setText(f"<b>{node.name}</b>")
        self.spin_priority.setEnabled(True)
        self.btn_set_priority.setEnabled(True)
        self.spin_priority.setValue(node.effective_priority)
        self.btn_clear_priority.setEnabled(node.is_explicit)

    def _on_item_double_clicked(self, item, column):
        did = item.data(0, Qt.ItemDataRole.UserRole)
        if did is not None:
            from .set_priority_modal import SetPriorityModal
            modal = SetPriorityModal(self, did, on_saved=self.refresh_deck_tree)
            modal.exec()

    def _apply_selected_priority(self):
        did = self._get_selected_deck_id()
        if did is not None:
            val = self.spin_priority.value()
            set_deck_priority(did, val)
            self.refresh_deck_tree()
            run_reorder_with_ui(parent_widget=self, interactive=False)

    def _clear_selected_priority(self):
        did = self._get_selected_deck_id()
        if did is not None:
            set_deck_priority(did, None)
            self.refresh_deck_tree()
            run_reorder_with_ui(parent_widget=self, interactive=False)

    def _save_options(self):
        config = get_module_config("priority_sequencer")
        config["randomize_same_priority_decks"] = self.chk_randomize_same.isChecked()
        config["randomize_cards_within_deck"] = self.chk_randomize_cards.isChecked()
        config["auto_reorder_on_profile_open"] = self.chk_auto_profile.isChecked()
        config["auto_reorder_on_sync"] = self.chk_auto_sync.isChecked()
        write_module_config("priority_sequencer", config)

    def _reorder_now(self):
        self._save_options()
        run_reorder_with_ui(parent_widget=self, on_complete=lambda _: self.refresh_deck_tree())


# Alias for backward compatibility
DeckPriorityManagerDialog = PriorityManagerDialog

