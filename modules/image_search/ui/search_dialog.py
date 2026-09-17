# -*- coding: utf-8 -*-
"""
Main Dialog for searching, previewing with partial zoom, downloading,
and inserting web images into Anki's card editor at the current cursor position.
"""

from typing import Optional, List
import threading
import os
import re
import time

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLineEdit,
        QPushButton,
        QComboBox,
        QLabel,
        QScrollArea,
        QWidget,
        QGridLayout,
        QStackedWidget,
        QTabWidget,
        QProgressBar,
        QSizePolicy,
        QFrame,
    )
    from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QCursor, QDesktopServices
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl
    from aqt import mw
except ImportError:
    QDialog = object
    QVBoxLayout = object
    QHBoxLayout = object
    QLineEdit = object
    QPushButton = object
    QComboBox = object
    QLabel = object
    QScrollArea = object
    QWidget = object
    QGridLayout = object
    QStackedWidget = object
    QTabWidget = object
    QProgressBar = object
    QSizePolicy = object
    QFrame = object
    QPixmap = None
    QKeySequence = None
    QShortcut = None
    QCursor = None
    QDesktopServices = None
    Qt = None
    pyqtSignal = lambda *args: None
    QObject = object
    QUrl = None
try:
    from ....utils.i18n import tr
    from ....utils.config_manager import get_module_config
except (ImportError, ValueError):
    try:
        from ...utils.i18n import tr
        from ...utils.config_manager import get_module_config
    except (ImportError, ValueError):
        try:
            from utils.i18n import tr
            from utils.config_manager import get_module_config
        except ImportError:
            tr = lambda k, d=None, **kw: d or k
            def get_module_config(mod_name: str):
                return {}

from ..search_engine import (
    ImageResultItem,
    search_images,
    download_image_bytes,
    DEFAULT_HEADERS,
)
from .image_card import ImageCardWidget
try:
    from .image_editor import ImageEditorDialog
except (ImportError, ValueError):
    try:
        from modules.image_search.ui.image_editor import ImageEditorDialog
    except ImportError:
        ImageEditorDialog = None
try:
    from ..recent_manager import get_recent_images, add_recent_image, MAX_RECENT_IMAGES
except (ImportError, ValueError):
    try:
        from modules.image_search.recent_manager import get_recent_images, add_recent_image, MAX_RECENT_IMAGES
    except ImportError:
        def get_recent_images(max_items=15): return []
        def add_recent_image(item): pass
        MAX_RECENT_IMAGES = 15


def _log_recent_debug(msg: str) -> None:
    try:
        addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_path = os.path.join(addon_dir, "runtime_debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [IMAGE_SEARCH_RECENT] {msg}\n")
    except Exception:
        pass


class _SearchWorkerSignals(QObject):
    results_ready = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    more_results_ready = pyqtSignal(list, int)


class _DownloadWorkerSignals(QObject):
    download_done = pyqtSignal(bytes, str)
    download_failed = pyqtSignal(str)


class ImageSearchDialog(QDialog):
    """
    Search and insert dialog for web images in Anki Card Editor.
    """

    def __init__(
        self,
        parent,
        editor,
        initial_query: str = "",
        saved_field_index: Optional[int] = None,
    ):
        if QDialog is not object:
            super().__init__(parent)
            if Qt is not None and hasattr(Qt, "WindowModality"):
                self.setWindowModality(Qt.WindowModality.WindowModal)
        self.editor = editor
        self.initial_query = initial_query.strip()
        self.saved_field_index = saved_field_index
        self.current_results: List[ImageResultItem] = []
        self.current_preview_item: Optional[ImageResultItem] = None

        self._current_page: int = 1
        self._is_loading_more: bool = False
        self._has_more_results: bool = True
        self._seen_urls: set = set()
        self._current_inserting_item: Optional[ImageResultItem] = None
        self._recent_items: List[ImageResultItem] = []

        self.tab_widget: Optional[QTabWidget] = None
        self.tab_search: Optional[QWidget] = None
        self.tab_recent: Optional[QWidget] = None
        self.cards_container: Optional[QWidget] = None
        self.footer_loading_widget: Optional[QWidget] = None
        self.grid_layout: Optional[QGridLayout] = None

        self.recent_cards_container: Optional[QWidget] = None
        self.recent_grid_layout: Optional[QGridLayout] = None
        self.lbl_recent_empty: Optional[QLabel] = None
        self.lbl_recent_hint: Optional[QLabel] = None
        self.recent_scroll_area: Optional[QScrollArea] = None

        self.search_signals = _SearchWorkerSignals()
        self.download_signals = _DownloadWorkerSignals()

        if QDialog is not object:
            self.init_ui()
            if self.initial_query:
                self.search_input.setText(self.initial_query)
                self.do_search()

    def init_ui(self):
        self.setWindowTitle(tr("image_search_title", "🖼️ Buscador e Baixador de Imagens da Web"))
        self.resize(850, 620)
        self.setMinimumSize(640, 480)

        self.setStyleSheet("""
            QDialog {
                background-color: #141418;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLineEdit {
                background-color: #1f1f26;
                border: 1px solid #383844;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #8b5cf6;
                background-color: #262630;
            }
            QPushButton {
                background-color: #282834;
                border: 1px solid #404052;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #38384a;
                border-color: #6366f1;
            }
            QPushButton#btn_primary {
                background-color: #7c3aed;
                border: 1px solid #8b5cf6;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton#btn_primary:hover {
                background-color: #6d28d9;
            }
            QPushButton#btn_primary:disabled {
                background-color: #4c1d95;
                color: #94a3b8;
                border-color: #4c1d95;
            }
            QComboBox {
                background-color: #1f1f26;
                border: 1px solid #383844;
                border-radius: 6px;
                padding: 6px 10px;
                color: #ffffff;
                font-size: 12px;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #282834;
                border-radius: 8px;
                background-color: #141418;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #1a1a22;
                color: #94a3b8;
                border: 1px solid #282834;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 500;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #262634;
                color: #ffffff;
                border-color: #8b5cf6;
                border-bottom: 2px solid #8b5cf6;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #20202a;
                color: #e2e8f0;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # --- Stacked Widget (View 0: Tab Widget [Search | Recent], View 1: Partial Zoom Preview) ---
        self.stacked_widget = QStackedWidget(self)
        main_layout.addWidget(self.stacked_widget, stretch=1)

        # Construct Tab Widget
        self.tab_widget = QTabWidget(self)
        self.stacked_widget.addWidget(self.tab_widget)

        # Tab 0: Search Tab
        self.tab_search = self._create_search_tab()
        self.tab_widget.addTab(self.tab_search, tr("image_search_tab_search", "🔍 Pesquisa"))

        # Tab 1: Recent Tab
        self.tab_recent = self._create_recent_tab()
        initial_recent_count = len(get_recent_images(MAX_RECENT_IMAGES, force_reload=True))
        self.tab_widget.addTab(self.tab_recent, f"{tr('image_search_tab_recent', '🕒 Recentes')} ({initial_recent_count})")

        # View 1: Zoom Preview
        self.view_zoom = self._create_zoom_view()
        self.stacked_widget.addWidget(self.view_zoom)

        # Tab switch listener
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Populate recent tab initial content
        self._refresh_recent_tab()

        # Connect worker signals
        self.search_signals.results_ready.connect(self._on_search_results_ready)
        self.search_signals.search_failed.connect(self._on_search_failed)
        self.search_signals.more_results_ready.connect(self._on_more_results_ready)
        self.download_signals.download_done.connect(self._on_download_success)
        self.download_signals.download_failed.connect(self._on_download_failed)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Escape"), self, activated=self._on_escape_pressed)

    def _create_search_tab(self) -> QWidget:
        """Constructs the search tab containing search bar, status, and scrollable results grid."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        # --- Top Search Bar ---
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.search_input = QLineEdit(container)
        self.search_input.setPlaceholderText(
            tr("image_search_placeholder", "Digite o termo para buscar imagens e pressione Enter...")
        )
        self.search_input.returnPressed.connect(self.do_search)
        top_bar.addWidget(self.search_input, stretch=1)

        self.engine_combo = QComboBox(container)
        self.engine_combo.addItem(tr("image_search_engine_all", "✨ Todas as Fontes (Google + Wikipédia)"), "all")
        self.engine_combo.addItem(tr("image_search_engine_google", "🌐 Google Imagens (Web)"), "google")
        self.engine_combo.addItem(tr("image_search_engine_wikimedia", "🏛️ Wikimedia Commons"), "wikimedia")
        self.engine_combo.addItem(tr("image_search_engine_wikipedia", "📖 Wikipédia Artigos"), "wikipedia")

        try:
            cfg = get_module_config("image_search")
            default_engine = (cfg.get("default_engine") or "all").lower() if cfg else "all"
            if default_engine in ("web", "bing"):
                default_engine = "google"
            if hasattr(self.engine_combo, "findData"):
                idx = self.engine_combo.findData(default_engine)
                if idx >= 0:
                    self.engine_combo.setCurrentIndex(idx)
        except Exception:
            pass

        top_bar.addWidget(self.engine_combo)

        self.btn_search = QPushButton(tr("image_search_btn_search", "Buscar"), container)
        self.btn_search.setObjectName("btn_primary")
        self.btn_search.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_search.clicked.connect(self.do_search)
        top_bar.addWidget(self.btn_search)

        layout.addLayout(top_bar)

        # --- Status / Progress Bar ---
        self.lbl_status = QLabel(
            tr("image_search_zoom_hint", "Clique em uma imagem para zoom e pré-visualização. Clique duplo para inserir direto."),
            container,
        )
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar(container)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #1f1f26;
            }
            QProgressBar::chunk {
                background-color: #7c3aed;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # --- Results Grid ---
        self.view_grid = self._create_grid_view()
        layout.addWidget(self.view_grid, stretch=1)

        return container

    def _create_recent_tab(self) -> QWidget:
        """Constructs the tab displaying the last 15 inserted images."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        self.lbl_recent_hint = QLabel(
            tr("image_search_recent_hint", "Últimas 15 imagens utilizadas. Clique para zoom ou duplo clique para inserir no card."),
            container,
        )
        self.lbl_recent_hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.lbl_recent_hint)

        self.lbl_recent_empty = QLabel(
            tr("image_search_recent_empty", "Nenhuma imagem recente utilizada ainda. As imagens inseridas nos cards aparecerão aqui."),
            container,
        )
        self.lbl_recent_empty.setStyleSheet("color: #64748b; font-size: 13px; padding: 40px;")
        self.lbl_recent_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_recent_empty.hide()
        layout.addWidget(self.lbl_recent_empty)

        self.recent_scroll_area = QScrollArea(container)
        self.recent_scroll_area.setWidgetResizable(True)
        self.recent_scroll_area.setStyleSheet("background-color: transparent; border: none;")

        self.recent_grid_content = QWidget()
        self.recent_grid_layout = QGridLayout(self.recent_grid_content)
        self.recent_grid_layout.setContentsMargins(4, 4, 4, 4)
        self.recent_grid_layout.setSpacing(12)
        self.recent_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Alias for backward compatibility if any test or caller inspects recent_cards_container
        self.recent_cards_container = self.recent_grid_content

        self.recent_scroll_area.setWidget(self.recent_grid_content)
        layout.addWidget(self.recent_scroll_area, stretch=1)

        return container

    def _on_tab_changed(self, index: int):
        """Refreshes recent images when user clicks the Recent tab."""
        _log_recent_debug(f"_on_tab_changed: index={index}")
        if index == 1:
            self._refresh_recent_tab()

    def _refresh_recent_tab(self):
        """Refreshes the recent images grid with the latest items."""
        _log_recent_debug("Entering _refresh_recent_tab")
        if getattr(self, "recent_grid_layout", None) is None:
            _log_recent_debug("recent_grid_layout is None, aborting")
            return

        while True:
            cnt = self.recent_grid_layout.count() if hasattr(self.recent_grid_layout, "count") else 0
            if not cnt or (isinstance(cnt, int) and cnt <= 0):
                break
            item = self.recent_grid_layout.takeAt(0)
            if not item:
                break
            widget = item.widget() if hasattr(item, "widget") else None
            if widget:
                if hasattr(widget, "setParent"):
                    widget.setParent(None)
                if hasattr(widget, "deleteLater"):
                    widget.deleteLater()

        try:
            items = get_recent_images(MAX_RECENT_IMAGES, force_reload=True)
        except Exception as e:
            _log_recent_debug(f"Error loading recent images from disk: {e}")
            items = []

        self._recent_items = items
        count = len(items)
        _log_recent_debug(f"Found {count} recent items")

        if hasattr(self, "tab_widget") and self.tab_widget and hasattr(self.tab_widget, "setTabText"):
            self.tab_widget.setTabText(1, f"{tr('image_search_tab_recent', '🕒 Recentes')} ({count})")

        if not items:
            _log_recent_debug("No recent items, showing lbl_recent_empty and hiding recent_scroll_area")
            if hasattr(self, "lbl_recent_empty") and self.lbl_recent_empty:
                self.lbl_recent_empty.show()
            if hasattr(self, "recent_scroll_area") and self.recent_scroll_area:
                self.recent_scroll_area.hide()
            return

        _log_recent_debug("Items present, hiding lbl_recent_empty and showing recent_scroll_area")
        if hasattr(self, "lbl_recent_empty") and self.lbl_recent_empty:
            self.lbl_recent_empty.hide()
        if hasattr(self, "recent_scroll_area") and self.recent_scroll_area:
            self.recent_scroll_area.show()

        columns = 4
        for idx, item in enumerate(items):
            try:
                card = ImageCardWidget(
                    item=item,
                    on_click=self.show_zoom_preview,
                    on_double_click=self.download_and_insert,
                    on_edit=self.open_editor_for_item,
                    parent=self.recent_grid_content,
                )
                row = idx // columns
                col = idx % columns
                self.recent_grid_layout.addWidget(card, row, col)
                if hasattr(card, "show"):
                    card.show()
            except Exception as e:
                _log_recent_debug(f"Error instantiating ImageCardWidget for item {idx}: {e}")

        _log_recent_debug(f"_refresh_recent_tab successfully populated {count} cards in grid")

    def _create_grid_view(self) -> QWidget:
        """Constructs the scrollable grid container for image cards with infinite scroll."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(container)
        self.scroll_area.setWidgetResizable(True)

        self.grid_content = QWidget()
        content_vlayout = QVBoxLayout(self.grid_content)
        content_vlayout.setContentsMargins(4, 4, 4, 4)
        content_vlayout.setSpacing(8)
        content_vlayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Cards container with 4-column grid layout
        self.cards_container = QWidget(self.grid_content)
        self.grid_layout = QGridLayout(self.cards_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        content_vlayout.addWidget(self.cards_container)

        # Footer loading widget
        self.footer_loading_widget = QWidget(self.grid_content)
        footer_layout = QHBoxLayout(self.footer_loading_widget)
        footer_layout.setContentsMargins(0, 8, 0, 8)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_footer_loading = QLabel(
            tr("image_search_loading_more", "🔄 Carregando mais imagens..."),
            self.footer_loading_widget,
        )
        self.lbl_footer_loading.setStyleSheet(
            "color: #a78bfa; font-weight: 600; font-size: 13px; padding: 12px;"
        )
        self.lbl_footer_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(self.lbl_footer_loading)
        self.footer_loading_widget.hide()
        content_vlayout.addWidget(self.footer_loading_widget)

        self.scroll_area.setWidget(self.grid_content)
        layout.addWidget(self.scroll_area)

        # Connect scroll listener for infinite scroll
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)

        return container

    def _create_zoom_view(self) -> QWidget:
        """Constructs the partial zoom preview page with floating download button."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top zoom navigation bar
        zoom_nav = QHBoxLayout()
        self.btn_back = QPushButton(tr("image_search_back", "◀ Voltar aos Resultados"), container)
        self.btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_back.clicked.connect(self.back_to_grid)
        zoom_nav.addWidget(self.btn_back)

        self.lbl_zoom_title = QLabel("", container)
        self.lbl_zoom_title.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: 500;")
        zoom_nav.addWidget(self.lbl_zoom_title, stretch=1)

        layout.addLayout(zoom_nav)

        # Central Image Preview Area with Frame
        self.preview_frame = QFrame(container)
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: #0f0f13;
                border: 1px solid #2d2d38;
                border-radius: 8px;
            }
        """)
        frame_layout = QVBoxLayout(self.preview_frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)

        self.lbl_zoom_image = QLabel(self.preview_frame)
        self.lbl_zoom_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_zoom_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        frame_layout.addWidget(self.lbl_zoom_image)

        # Bottom Bar inside preview: Metadata + Webpage Button + Floating Download Button
        bottom_bar = QHBoxLayout()
        self.lbl_zoom_meta = QLabel("", self.preview_frame)
        self.lbl_zoom_meta.setStyleSheet("color: #94a3b8; font-size: 12px;")
        bottom_bar.addWidget(self.lbl_zoom_meta, stretch=1)

        self.btn_open_page = QPushButton(
            tr("image_search_btn_open_page", "🌐 Abrir página da imagem"),
            self.preview_frame,
        )
        self.btn_open_page.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_open_page.setMinimumHeight(40)
        self.btn_open_page.setStyleSheet("""
            QPushButton {
                background-color: #282834;
                border: 1px solid #404052;
                border-radius: 8px;
                padding: 8px 16px;
                color: #e2e8f0;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #38384a;
                border-color: #8b5cf6;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1e1e24;
                color: #64748b;
                border-color: #2e2e38;
            }
        """)
        self.btn_open_page.clicked.connect(self._on_open_page_clicked)
        bottom_bar.addWidget(self.btn_open_page)

        # Edit and Insert button (arrows, circles, crop)
        self.btn_edit = QPushButton(
            tr("image_search_btn_edit", "✏️ Editar e Inserir"),
            self.preview_frame,
        )
        self.btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_edit.setMinimumHeight(40)
        self.btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #2e1065;
                border: 1px solid #8b5cf6;
                border-radius: 8px;
                padding: 8px 18px;
                color: #e9d5ff;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3b0764;
                border-color: #a855f7;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1e1e24;
                color: #64748b;
                border-color: #2e2e38;
            }
        """)
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        bottom_bar.addWidget(self.btn_edit)

        # Prominent Download & Insert button in the lower corner
        self.btn_download = QPushButton(
            tr("image_search_download_insert", "⬇️ Baixar e Inserir no Card"),
            self.preview_frame,
        )
        self.btn_download.setObjectName("btn_primary")
        self.btn_download.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_download.setMinimumHeight(40)
        self.btn_download.setStyleSheet("""
            QPushButton#btn_primary {
                background-color: #7c3aed;
                border: 1px solid #9333ea;
                border-radius: 8px;
                padding: 8px 22px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#btn_primary:hover {
                background-color: #6d28d9;
            }
        """)
        self.btn_download.clicked.connect(self._on_download_clicked)
        bottom_bar.addWidget(self.btn_download)

        frame_layout.addLayout(bottom_bar)
        layout.addWidget(self.preview_frame, stretch=1)

        return container

    def do_search(self):
        """Initiates an asynchronous search request."""
        query = self.search_input.text().strip()
        if not query:
            return

        self._current_page = 1
        self._is_loading_more = False
        self._has_more_results = True
        self._seen_urls.clear()
        if hasattr(self, "footer_loading_widget") and self.footer_loading_widget:
            self.footer_loading_widget.hide()

        engine = self.engine_combo.currentData() or "all"
        if engine in ("web", "bing"):
            engine = "google"
        self.lbl_status.setText(tr("image_search_searching", "Buscando imagens..."))
        self.progress_bar.show()
        self.btn_search.setEnabled(False)

        # Clear existing grid
        self._clear_grid()

        def worker():
            try:
                try:
                    results = search_images(query, engine=engine, page=1, max_results=50, safe_search=False)
                except TypeError:
                    results = search_images(query, engine=engine, max_results=50, safe_search=False)
                self.search_signals.results_ready.emit(results)
            except Exception as e:
                self.search_signals.search_failed.emit(str(e))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _clear_grid(self):
        """Removes all items from the grid layout."""
        if getattr(self, "grid_layout", None) is None:
            return
        while True:
            cnt = self.grid_layout.count() if hasattr(self.grid_layout, "count") else 0
            if not cnt or (isinstance(cnt, int) and cnt <= 0):
                break
            item = self.grid_layout.takeAt(0)
            if not item:
                break
            widget = item.widget() if hasattr(item, "widget") else None
            if widget:
                if hasattr(widget, "setParent"):
                    widget.setParent(None)
                if hasattr(widget, "deleteLater"):
                    widget.deleteLater()

    def _on_search_results_ready(self, results: List[ImageResultItem]):
        self.progress_bar.hide()
        self.btn_search.setEnabled(True)
        self.current_results = list(results)
        self._seen_urls = {item.original_url for item in results}

        if not results:
            self._has_more_results = False
            self.lbl_status.setText(tr("image_search_no_results", "Nenhuma imagem encontrada para esta busca."))
            return

        count = len(results)
        self.lbl_status.setText(f"✓ {count} imagens encontradas. " + tr("image_search_zoom_hint", "Clique em uma imagem para zoom."))

        columns = 4  # 4 cards per row
        for idx, item in enumerate(results):
            card = ImageCardWidget(
                item=item,
                on_click=self.show_zoom_preview,
                on_double_click=self.download_and_insert,
                on_edit=self.open_editor_for_item,
                parent=self.cards_container,
            )
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)
            if hasattr(card, "show"):
                card.show()

        if hasattr(self, "scroll_area") and self.scroll_area:
            self.scroll_area.verticalScrollBar().setValue(0)

        if hasattr(self, "tab_widget") and self.tab_widget:
            self.tab_widget.setCurrentIndex(0)

        self.stacked_widget.setCurrentIndex(0)

    def _on_search_failed(self, error_msg: str):
        self.progress_bar.hide()
        self.btn_search.setEnabled(True)
        self._has_more_results = False
        self.lbl_status.setText(tr("image_search_error", "Erro ao buscar imagens. Verifique a conexão com a internet."))

    def _on_scroll_value_changed(self, value: int):
        scroll_bar = self.scroll_area.verticalScrollBar()
        max_val = scroll_bar.maximum()
        if max_val > 0 and value >= (max_val - 140):
            if not self._is_loading_more and self._has_more_results and self.current_results:
                self._load_next_page()

    def _load_next_page(self):
        """Loads next page of image search results when scrolling near bottom."""
        query = self.search_input.text().strip()
        if not query:
            return

        self._is_loading_more = True
        if hasattr(self, "lbl_footer_loading") and self.lbl_footer_loading:
            self.lbl_footer_loading.setText(tr("image_search_loading_more", "🔄 Carregando mais imagens..."))
        if hasattr(self, "footer_loading_widget") and self.footer_loading_widget:
            self.footer_loading_widget.show()

        next_page = self._current_page + 1
        engine = self.engine_combo.currentData() or "all"
        if engine in ("web", "bing"):
            engine = "google"

        def worker():
            try:
                try:
                    results = search_images(query, engine=engine, page=next_page, max_results=40, safe_search=False)
                except TypeError:
                    results = search_images(query, engine=engine, max_results=40, safe_search=False)
                self.search_signals.more_results_ready.emit(results, next_page)
            except Exception:
                self.search_signals.more_results_ready.emit([], next_page)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_more_results_ready(self, new_results: List[ImageResultItem], page: int):
        if hasattr(self, "footer_loading_widget") and self.footer_loading_widget:
            self.footer_loading_widget.hide()
        self._is_loading_more = False

        if not new_results:
            self._has_more_results = False
            return

        columns = 4
        added_count = 0
        for item in new_results:
            if item.original_url in self._seen_urls:
                continue
            self._seen_urls.add(item.original_url)
            card = ImageCardWidget(
                item=item,
                on_click=self.show_zoom_preview,
                on_double_click=self.download_and_insert,
                on_edit=self.open_editor_for_item,
                parent=self.cards_container,
            )
            idx = len(self.current_results)
            row = idx // columns
            col = idx % columns
            self.grid_layout.addWidget(card, row, col)
            if hasattr(card, "show"):
                card.show()
            self.current_results.append(item)
            added_count += 1

        if added_count == 0:
            self._has_more_results = False
            return

        self._current_page = page
        count = len(self.current_results)
        self.lbl_status.setText(f"✓ {count} imagens encontradas. " + tr("image_search_zoom_hint", "Clique em uma imagem para zoom."))

    def show_zoom_preview(self, item: ImageResultItem):
        """Switches to View 1: displays the image zoomed in with metadata and the download button."""
        self.current_preview_item = item
        self.lbl_zoom_title.setText(item.title)
        dims = f"{item.width} × {item.height} px" if item.width and item.height else ""
        source_domain = re.sub(r"^https?://([^/]+).*", r"\1", item.source) if item.source else ""
        self.lbl_zoom_meta.setText(f"{dims}  •  {source_domain}")

        self.lbl_zoom_image.setText("⌛ Carregando imagem...")
        self.btn_download.setEnabled(True)
        self.btn_download.setText(tr("image_search_download_insert", "⬇️ Baixar e Inserir no Card"))
        if hasattr(self, "btn_edit") and self.btn_edit:
            self.btn_edit.setEnabled(True)
            self.btn_edit.setText(tr("image_search_btn_edit", "✏️ Editar e Inserir"))

        source_url = self._resolve_source_url(item)
        if hasattr(self, "btn_open_page") and self.btn_open_page:
            self.btn_open_page.setEnabled(bool(source_url))
            if source_url:
                self.btn_open_page.setToolTip(source_url)
            else:
                self.btn_open_page.setToolTip("")

        self.stacked_widget.setCurrentIndex(1)

        # Load high resolution image in background
        def load_preview_image():
            url = item.original_url or item.thumb_url
            try:
                data, _ = download_image_bytes(url, timeout=10)
                if QPixmap:
                    pixmap = QPixmap()
                    if pixmap.loadFromData(data):
                        scaled = pixmap.scaled(
                            580, 420,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.lbl_zoom_image.setPixmap(scaled)
                        self.lbl_zoom_image.setText("")
                        return
            except Exception:
                pass
            # Fallback to thumbnail if original failed
            try:
                import urllib.request
                req = urllib.request.Request(item.thumb_url, headers=DEFAULT_HEADERS)
                with urllib.request.urlopen(req, timeout=5) as r:
                    thumb_data = r.read()
                if QPixmap:
                    pixmap = QPixmap()
                    if pixmap.loadFromData(thumb_data):
                        scaled = pixmap.scaled(
                            580, 420,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.lbl_zoom_image.setPixmap(scaled)
                        self.lbl_zoom_image.setText("")
            except Exception:
                self.lbl_zoom_image.setText("❌ Falha ao carregar pré-visualização.")

        thread = threading.Thread(target=load_preview_image, daemon=True)
        thread.start()

    def back_to_grid(self):
        """Returns from zoom preview back to search results grid."""
        self.stacked_widget.setCurrentIndex(0)

    def _resolve_source_url(self, item: Optional[ImageResultItem]) -> str:
        if not item:
            return ""
        src = (item.source or "").strip()
        if src.startswith(("http://", "https://")):
            return src
        if "." in src and "/" not in src and " " not in src:
            return f"https://{src}"
        return item.original_url or ""

    def _on_open_page_clicked(self):
        if not self.current_preview_item:
            return
        url_str = self._resolve_source_url(self.current_preview_item)
        if url_str:
            try:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(url_str))
            except Exception as e:
                print(f"[ImageSearch] Erro ao abrir URL no navegador: {e}")

    def _on_download_clicked(self):
        if self.current_preview_item:
            self.download_and_insert(self.current_preview_item)

    def _on_edit_clicked(self):
        if self.current_preview_item:
            self.open_editor_for_item(self.current_preview_item)

    def open_editor_for_item(self, item: ImageResultItem):
        """
        Opens the Image Annotation & Crop Editor for the selected image.
        On approval:
          1. Inserts the EDITED image into Anki's card editor.
          2. Preserves the PRISTINE ORIGINAL image in recent images history.
        """
        if not ImageEditorDialog:
            return

        # Attempt to retrieve current loaded pixmap if available
        pixmap = None
        if (
            hasattr(self, "current_preview_item")
            and self.current_preview_item == item
            and hasattr(self, "lbl_zoom_image")
            and hasattr(self.lbl_zoom_image, "pixmap")
        ):
            pm = self.lbl_zoom_image.pixmap()
            if pm and (not hasattr(pm, "isNull") or not pm.isNull()):
                pixmap = pm

        # If pixmap is not yet in memory, download image bytes
        if not pixmap or (hasattr(pixmap, "isNull") and pixmap.isNull()):
            if hasattr(self, "lbl_status") and self.lbl_status:
                self.lbl_status.setText(tr("image_search_downloading", "Baixando imagem..."))
            data = None
            urls_to_try = [u for u in [item.original_url, item.thumb_url] if u]
            for url in urls_to_try:
                try:
                    data, _ = download_image_bytes(url, timeout=10)
                    if data and len(data) > 0:
                        break
                except Exception:
                    continue
            if data:
                if QPixmap is not None and hasattr(QPixmap, "loadFromData"):
                    pixmap = QPixmap()
                    pixmap.loadFromData(data)
                else:
                    pixmap = data

        if not pixmap or (hasattr(pixmap, "isNull") and pixmap.isNull()):
            if hasattr(self, "lbl_status") and self.lbl_status:
                self.lbl_status.setText(tr("image_search_error", "Erro ao carregar imagem para edição."))
            return

        dialog = ImageEditorDialog(parent=self, pixmap=pixmap, title=item.title)
        exec_fn = getattr(dialog, "exec", None) or getattr(dialog, "exec_", None)
        ret = exec_fn() if exec_fn else 0
        accepted_code = getattr(getattr(QDialog, "DialogCode", None), "Accepted", 1)
        if ret in (1, accepted_code):
            if dialog.result_data and len(dialog.result_data) > 0:
                # 1. PRISTINE ORIGINAL image saved to recent history (MANDATORY RULE)
                try:
                    add_recent_image(item)
                    self._refresh_recent_tab()
                except Exception as e:
                    print(f"[ImageSearch] Error saving pristine recent image: {e}")

                # 2. Insert EDITED image into Anki editor
                query = self.search_input.text().strip() if hasattr(self, "search_input") and self.search_input else ""
                if not query:
                    query = item.title or "image"
                query = f"{query}_edited"

                try:
                    self._insert_into_anki_editor(dialog.result_data, dialog.result_ext, query)
                except Exception as e:
                    print(f"[ImageSearch] Error inserting edited image into card: {e}")

                try:
                    self.accept()
                except Exception:
                    pass

    def download_and_insert(self, item: ImageResultItem):
        """Downloads the full image and inserts it into Anki Card Editor at cursor position."""
        self._current_inserting_item = item
        if hasattr(self, "btn_download") and self.btn_download:
            self.btn_download.setEnabled(False)
            self.btn_download.setText(tr("image_search_downloading", "Baixando imagem..."))
        if hasattr(self, "lbl_status") and self.lbl_status:
            self.lbl_status.setText(tr("image_search_downloading", "Baixando imagem..."))
        if hasattr(self, "lbl_recent_hint") and self.lbl_recent_hint:
            self.lbl_recent_hint.setText("⌛ " + tr("image_search_downloading", "Baixando imagem..."))
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.show()

        def worker():
            data = None
            ext = ".jpg"
            last_err = ""

            # Tier 1: Attempt downloading high-res original_url
            if item.original_url:
                try:
                    data, ext = download_image_bytes(item.original_url, timeout=12)
                except Exception as e:
                    last_err = str(e)
                    print(f"[ImageSearch] Original URL download failed ({e}), falling back to thumbnail...")

            # Tier 2: Fallback to thumb_url if original_url failed or returned empty
            if not data and item.thumb_url and item.thumb_url != item.original_url:
                try:
                    data, ext = download_image_bytes(item.thumb_url, timeout=10)
                except Exception as e:
                    last_err = str(e)
                    print(f"[ImageSearch] Thumbnail download failed: {e}")

            # Tier 3: In-memory cached pixmap fallback (zoom preview)
            if not data:
                try:
                    if hasattr(self, "current_preview_item") and self.current_preview_item == item and hasattr(self, "lbl_zoom_image"):
                        pm = self.lbl_zoom_image.pixmap()
                        if pm and not pm.isNull():
                            from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
                            ba = QByteArray()
                            buf = QBuffer(ba)
                            buf.open(QIODevice.OpenModeFlag.WriteOnly)
                            pm.save(buf, "JPG", 92)
                            data = bytes(ba.data())
                            ext = ".jpg"
                except Exception as e:
                    print(f"[ImageSearch] Pixmap memory extraction failed: {e}")

            if data and len(data) > 0:
                self.download_signals.download_done.emit(data, ext)
            else:
                self.download_signals.download_failed.emit(last_err or "Falha ao baixar imagem")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_download_success(self, data: bytes, ext: str):
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.hide()
        if hasattr(self, "_current_inserting_item") and self._current_inserting_item:
            try:
                add_recent_image(self._current_inserting_item)
                self._refresh_recent_tab()
            except Exception as e:
                print(f"[ImageSearch] Error saving recent image: {e}")

        query = self.search_input.text().strip() if hasattr(self, "search_input") and self.search_input else ""
        if not query and hasattr(self, "_current_inserting_item") and self._current_inserting_item:
            query = getattr(self._current_inserting_item, "title", "")
        query = query or "image"
        self.downloaded_data = (data, ext, query)

        # Execute editor insertion immediately
        try:
            self._insert_into_anki_editor(data, ext, query)
        except Exception as e:
            print(f"[ImageSearch] Error during direct editor insertion: {e}")

        try:
            self.accept()
        except Exception:
            pass

    def _on_download_failed(self, error_msg: str):
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.hide()
        if hasattr(self, "btn_download") and self.btn_download:
            self.btn_download.setEnabled(True)
            self.btn_download.setText(tr("image_search_download_insert", "⬇️ Baixar e Inserir no Card"))
        if hasattr(self, "lbl_status") and self.lbl_status:
            self.lbl_status.setText(tr("image_search_error", "Erro ao baixar a imagem. Tente outra da lista."))
        if hasattr(self, "lbl_recent_hint") and self.lbl_recent_hint:
            self.lbl_recent_hint.setText(tr("image_search_error", "Erro ao baixar a imagem. Tente outra da lista."))

    def _insert_into_anki_editor(self, data: bytes, ext: str, query: str):
        """
        Saves image into Anki's collection media directory and injects HTML tag
        into the active editor field with multi-tier fallbacks.
        """
        self._inserted = True
        try:
            from .. import insert_image_into_editor
        except (ImportError, ValueError):
            from modules.image_search import insert_image_into_editor

        target_idx = self.saved_field_index if self.saved_field_index is not None else getattr(self.editor, "currentField", None)
        insert_image_into_editor(self.editor, data, ext, query, target_idx)

    def _on_escape_pressed(self):
        if self.stacked_widget.currentIndex() == 1:
            self.back_to_grid()
        else:
            self.reject()
