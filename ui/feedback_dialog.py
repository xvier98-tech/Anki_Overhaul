# -*- coding: utf-8 -*-
"""
Visual Feedback Dialogs for Priority Sequencer:
1. ReorderProgressDialog: Live progress, stages and animation during execution.
2. ReorderSummaryDialog: Rich report upon completion with metrics and DNA Proofreading audit.
"""

from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QFrame,
        QWidget,
        QApplication,
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont, QColor
    from aqt import mw
except ImportError:
    QDialog = object
    QWidget = object
    mw = None

try:
    from ..modules.theme_manager.engine import get_current_theme_colors, get_qt_dialog_stylesheet
except Exception:
    try:
        from modules.theme_manager.engine import get_current_theme_colors, get_qt_dialog_stylesheet
    except Exception:
        get_current_theme_colors = None
        get_qt_dialog_stylesheet = None

try:
    from ..core.models import ReorderResult, IntegrityReport
except Exception:
    try:
        from core.models import ReorderResult, IntegrityReport
    except Exception:
        from modules.priority_sequencer.models import ReorderResult, IntegrityReport


class ReorderProgressDialog(QDialog):
    """Modern visual progress dialog displayed while reordering cards."""

    STAGES = [
        ("🔍", "Mapeando baralhos e hierarquia de herança..."),
        ("📦", "Agrupando cartões em blocos fechados contíguos..."),
        ("💾", "Gravando nova sequência no banco de dados SQLite..."),
        ("🧬", "Verificação de fidelidade e autocura (DNA Proofreading)..."),
    ]

    def __init__(self, parent=None, total_cards: int = 0):
        super().__init__(parent)
        self.setWindowTitle("⚡ Reordenamento de Cartões por Prioridade")
        self.setFixedWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.total_cards = total_cards
        self.current_stage = 0
        self._setup_ui()
        self._apply_theme()

    def _apply_theme(self):
        if get_current_theme_colors and get_qt_dialog_stylesheet:
            try:
                colors = get_current_theme_colors()
                self.setStyleSheet(get_qt_dialog_stylesheet(colors))
            except Exception:
                pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header_layout = QHBoxLayout()
        lbl_icon = QLabel("⚡")
        lbl_icon.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(lbl_icon)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel("<b>Reordenando Novos Cartões</b>")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_vbox.addWidget(lbl_title)

        lbl_subtitle = QLabel(
            f"Garantindo estudo em blocos fechados contíguos • {self.total_cards} cartões novos"
            if self.total_cards > 0
            else "Garantindo estudo em blocos fechados contíguos"
        )
        lbl_subtitle.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_vbox.addWidget(lbl_subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                height: 18px;
                font-size: 11px;
                font-weight: bold;
                background-color: #0f172a;
                color: #f8fafc;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Stage indicator frame
        stage_frame = QFrame()
        stage_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 41, 59, 0.5);
                border: 1px solid rgba(51, 65, 85, 0.7);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        stage_layout = QVBoxLayout(stage_frame)
        stage_layout.setSpacing(6)

        self.stage_labels = []
        for idx, (icon, text) in enumerate(self.STAGES):
            lbl = QLabel(f"{icon}  Etapa {idx + 1}/4: {text}")
            lbl.setStyleSheet("color: #64748b; font-size: 12px;")
            stage_layout.addWidget(lbl)
            self.stage_labels.append(lbl)

        layout.addWidget(stage_frame)

        self.lbl_status = QLabel("Iniciando processo em segundo plano...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #38bdf8; font-size: 11px; font-style: italic;")
        layout.addWidget(self.lbl_status)

    def set_stage(self, stage_idx: int, custom_msg: Optional[str] = None):
        """Updates the active stage and highlights it visually."""
        self.current_stage = stage_idx
        for idx, lbl in enumerate(self.stage_labels):
            icon, text = self.STAGES[idx]
            if idx < stage_idx:
                lbl.setText(f"✓  Etapa {idx + 1}/4: {text}")
                lbl.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
            elif idx == stage_idx:
                lbl.setText(f"▶  Etapa {idx + 1}/4: {text}")
                lbl.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: bold;")
            else:
                lbl.setText(f"{icon}  Etapa {idx + 1}/4: {text}")
                lbl.setStyleSheet("color: #64748b; font-size: 12px;")

        pct_map = {0: 15, 1: 40, 2: 75, 3: 95}
        self.progress_bar.setValue(pct_map.get(stage_idx, 50))
        if custom_msg:
            self.lbl_status.setText(custom_msg)

        if QApplication and QApplication.instance():
            QApplication.instance().processEvents()


class ReorderSummaryDialog(QDialog):
    """Rich summary modal displayed after reordering with DNA Proofreading metrics."""

    def __init__(self, parent, result: ReorderResult, total_new: int = 0):
        super().__init__(parent)
        self.result = result
        self.total_new = total_new
        self.setWindowTitle("Resultado da Reordenação de Cartões")
        self.setFixedWidth(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._setup_ui()
        self._apply_theme()

    def _apply_theme(self):
        if get_current_theme_colors and get_qt_dialog_stylesheet:
            try:
                colors = get_current_theme_colors()
                self.setStyleSheet(get_qt_dialog_stylesheet(colors))
            except Exception:
                pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 1. Header Banner
        header_frame = QFrame()
        is_success = self.result.success
        border_color = "#10b981" if is_success else "#ef4444"
        bg_color = "rgba(16, 185, 129, 0.12)" if is_success else "rgba(239, 68, 68, 0.12)"

        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1.5px solid {border_color};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        h_layout = QHBoxLayout(header_frame)
        h_icon = QLabel("🎉" if is_success else "⚠️")
        h_icon.setStyleSheet("font-size: 32px;")
        h_layout.addWidget(h_icon)

        h_vbox = QVBoxLayout()
        title_text = "Reordenação Concluída com Sucesso!" if is_success else "Aviso na Reordenação"
        lbl_h_title = QLabel(f"<b>{title_text}</b>")
        lbl_h_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        h_vbox.addWidget(lbl_h_title)

        if is_success:
            if self.result.cards_reordered == 0:
                sub_text = f"Todos os {self.total_new} cartões novos já estavam na sequência correta de prioridades."
            else:
                sub_text = f"Sequência atualizada e sincronizada em blocos fechados contíguos."
        else:
            sub_text = f"Erro: {self.result.error_message}"

        lbl_h_sub = QLabel(sub_text)
        lbl_h_sub.setWordWrap(True)
        lbl_h_sub.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        h_vbox.addWidget(lbl_h_sub)
        h_layout.addLayout(h_vbox)
        layout.addWidget(header_frame)

        # 2. Key Metrics Grid
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 41, 59, 0.4);
                border: 1px solid rgba(51, 65, 85, 0.6);
                border-radius: 8px;
            }
        """)
        m_layout = QHBoxLayout(metrics_frame)
        m_layout.setContentsMargins(16, 12, 16, 12)

        def add_metric(icon: str, val: str, label: str):
            box = QVBoxLayout()
            box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            top = QLabel(f"{icon} {val}")
            top.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
            top.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box.addWidget(top)
            box.addWidget(lbl)
            m_layout.addLayout(box)

        add_metric("🃏", str(self.result.cards_reordered), "Cartões Reordenados")
        add_metric("📂", str(self.result.decks_affected), "Baralhos Estruturados")
        add_metric("⏱️", f"{self.result.elapsed_seconds:.2f}s", "Tempo Decorrido")
        layout.addWidget(metrics_frame)

        # 3. DNA Proofreading Verification Section
        proof_frame = QFrame()
        proof_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.6);
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        proof_layout = QVBoxLayout(proof_frame)
        proof_layout.setSpacing(8)

        p_header = QHBoxLayout()
        lbl_proof_icon = QLabel("🧬")
        lbl_proof_icon.setStyleSheet("font-size: 18px;")
        p_header.addWidget(lbl_proof_icon)

        lbl_proof_title = QLabel("<b>Mecanismo de Verificação DNA Proofreading</b>")
        lbl_proof_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8;")
        p_header.addWidget(lbl_proof_title)
        p_header.addStretch()

        rep = self.result.integrity_report or IntegrityReport()
        lbl_badge = QLabel(f" {rep.status_badge} ")
        badge_bg = "rgba(16, 185, 129, 0.2)" if rep.is_flawless else "rgba(245, 158, 11, 0.2)"
        badge_border = "#10b981" if rep.is_flawless else "#f59e0b"
        badge_color = "#34d399" if rep.is_flawless else "#fbbf24"
        lbl_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            border: 1px solid {badge_border};
            color: {badge_color};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        p_header.addWidget(lbl_badge)
        proof_layout.addLayout(p_header)

        # Verification items
        def add_check_item(name: str, passed: bool, detail: str):
            item_layout = QHBoxLayout()
            icon = QLabel("✓" if passed else "⚠")
            icon.setStyleSheet("color: #10b981; font-weight: bold;" if passed else "color: #f59e0b; font-weight: bold;")
            item_layout.addWidget(icon)
            text_lbl = QLabel(f"<b>{name}:</b> {detail}")
            text_lbl.setStyleSheet("font-size: 11px; color: #cbd5e1;")
            item_layout.addWidget(text_lbl)
            item_layout.addStretch()
            proof_layout.addLayout(item_layout)

        add_check_item(
            "Blocos Fechados Contíguos",
            rep.block_contiguity_valid,
            "100% contíguos (zero entrelaçamento entre baralhos)",
        )
        add_check_item(
            "Monotonicidade de Prioridade",
            rep.monotonicity_valid,
            "Hierarquia rigorosamente respeitada (maior prioridade estuda primeiro)",
        )
        add_check_item(
            "Sequência de Due sem Colisão",
            rep.no_due_collisions,
            f"{rep.total_cards_checked} cartões numerados ordenadamente",
        )

        if rep.auto_repaired:
            rep_lbl = QLabel(f"🧬 <i>Autocura ativada com sucesso: {rep.repaired_count} cartões reajustados atomicamente.</i>")
            rep_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
            proof_layout.addWidget(rep_lbl)

        layout.addWidget(proof_frame)

        # 4. Action Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton("Entendido")
        self.btn_ok.setFixedWidth(120)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #38bdf8;
                color: #0f172a;
            }
        """)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)
