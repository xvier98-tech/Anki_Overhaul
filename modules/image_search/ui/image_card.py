# -*- coding: utf-8 -*-
"""
Card widget displaying an image search result thumbnail with hover effects and click handlers.
"""

from typing import Callable, Optional
import urllib.request
import threading
import re
import ssl

try:
    from PyQt6.QtWidgets import (
        QFrame,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QMenu,
        QSizePolicy,
    )
    from PyQt6.QtGui import QPixmap, QCursor, QDesktopServices
    from PyQt6.QtCore import Qt, pyqtSignal, QObject, QUrl
except ImportError:
    QFrame = object
    QLabel = object
    QVBoxLayout = object
    QHBoxLayout = object
    QPushButton = object
    QMenu = object
    QSizePolicy = object
    QPixmap = None
    QCursor = None
    QDesktopServices = None
    Qt = None
    pyqtSignal = lambda *args: None
    QObject = object
    QUrl = None

try:
    from ....utils.i18n import tr
except (ImportError, ValueError):
    try:
        from ...utils.i18n import tr
    except (ImportError, ValueError):
        try:
            from utils.i18n import tr
        except ImportError:
            tr = lambda k, d=None, **kw: d or k

from ..search_engine import ImageResultItem, DEFAULT_HEADERS


class _ThumbnailLoaderSignals(QObject):
    loaded = pyqtSignal(bytes)
    failed = pyqtSignal()


class ImageCardWidget(QFrame):
    """Card representing an individual image search result with thumbnail and metadata."""

    def __init__(
        self,
        item: ImageResultItem,
        on_click: Optional[Callable[[ImageResultItem], None]] = None,
        on_double_click: Optional[Callable[[ImageResultItem], None]] = None,
        on_edit: Optional[Callable[[ImageResultItem], None]] = None,
        parent=None,
    ):
        if QFrame is not object:
            super().__init__(parent)
        self.item = item
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.on_edit = on_edit
        self.signals = _ThumbnailLoaderSignals()
        self._pixmap_data: Optional[bytes] = None

        if QFrame is not object:
            self.init_ui()
            self.load_thumbnail_async()

    def init_ui(self):
        self.setFixedSize(175, 160)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(f"{self.item.title}\n{self.item.width}x{self.item.height}")

        self.setStyleSheet("""
            ImageCardWidget {
                background-color: #1e1e24;
                border: 1px solid #33333d;
                border-radius: 8px;
            }
            ImageCardWidget:hover {
                border: 2px solid #7c3aed;
                background-color: #262630;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Image preview container
        self.img_label = QLabel(self)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setText("⌛")
        self.img_label.setStyleSheet("""
            QLabel {
                background-color: #141418;
                border-radius: 5px;
                color: #888899;
                font-size: 14px;
            }
        """)
        self.img_label.setFixedHeight(120)
        layout.addWidget(self.img_label)

        # Footer: info line (resolution) + compact source button
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(2, 0, 2, 0)
        footer_layout.setSpacing(4)

        dim_text = f"{self.item.width} × {self.item.height}" if self.item.width and self.item.height else "Web"
        self.lbl_info = QLabel(dim_text, self)
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.lbl_info.setStyleSheet("color: #9999aa; font-size: 11px; font-weight: 500;")
        footer_layout.addWidget(self.lbl_info, stretch=1)

        self.btn_source = QPushButton("🌐", self)
        self.btn_source.setFixedSize(22, 20)
        self.btn_source.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_source.setToolTip(tr("image_search_open_page_tooltip", "Abrir página original da imagem no navegador"))
        self.btn_source.setStyleSheet("""
            QPushButton {
                background-color: #282834;
                border: 1px solid #404052;
                border-radius: 4px;
                color: #e2e8f0;
                font-size: 11px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #38384a;
                border-color: #8b5cf6;
            }
            QPushButton:disabled {
                background-color: #1a1a20;
                color: #555566;
                border-color: #2e2e38;
            }
        """)
        url_str = self._resolve_source_url()
        self.btn_source.setEnabled(bool(url_str))
        self.btn_source.clicked.connect(self._open_source_url)
        footer_layout.addWidget(self.btn_source)

        layout.addLayout(footer_layout)

        self.signals.loaded.connect(self._on_thumbnail_loaded)
        self.signals.failed.connect(self._on_thumbnail_failed)

    def _resolve_source_url(self) -> str:
        if not self.item:
            return ""
        src = (self.item.source or "").strip()
        if src.startswith(("http://", "https://")):
            return src
        if "." in src and "/" not in src and " " not in src:
            return f"https://{src}"
        return self.item.original_url or ""

    def _open_source_url(self):
        url_str = self._resolve_source_url()
        if url_str:
            try:
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(url_str))
            except Exception as e:
                print(f"[ImageSearch] Erro ao abrir URL no navegador: {e}")

    def contextMenuEvent(self, event):
        if QMenu is None or QMenu is object:
            return
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e24;
                color: #e2e8f0;
                border: 1px solid #404052;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #7c3aed;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #64748b;
            }
        """)

        act_open = menu.addAction(tr("image_search_btn_open_page", "🌐 Abrir página da imagem"))
        url_str = self._resolve_source_url()
        act_open.setEnabled(bool(url_str))

        act_download = menu.addAction(tr("image_search_download_insert", "⬇️ Baixar e Inserir no Card"))
        act_edit = menu.addAction(tr("image_search_btn_edit", "✏️ Editar e Inserir"))
        act_zoom = menu.addAction(tr("image_search_view_zoom", "🔍 Visualizar com Zoom"))

        action = menu.exec(event.globalPos())
        if action == act_open:
            self._open_source_url()
        elif action == act_download:
            if self.on_double_click:
                self.on_double_click(self.item)
        elif action == act_edit:
            if self.on_edit:
                self.on_edit(self.item)
            elif self.on_click:
                self.on_click(self.item)
        elif action == act_zoom:
            if self.on_click:
                self.on_click(self.item)

    def load_thumbnail_async(self):
        """Fetches thumbnail in a background thread with resilient multi-tier fallback."""
        def worker():
            data = None
            urls_to_try = [u for u in [self.item.thumb_url, self.item.original_url] if u]
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

            for url in urls_to_try:
                try:
                    headers = dict(DEFAULT_HEADERS)
                    match = re.match(r"^(https?://[^/]+)", url)
                    if match:
                        headers["Referer"] = match.group(1) + "/"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
                        data = resp.read()
                    if data and len(data) > 0:
                        break
                except Exception:
                    continue

            if data and len(data) > 0:
                self.signals.loaded.emit(data)
            else:
                self.signals.failed.emit()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_thumbnail_loaded(self, data: bytes):
        if not QPixmap:
            return
        self._pixmap_data = data
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            scaled = pixmap.scaled(
                163, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.img_label.setPixmap(scaled)
            self.img_label.setText("")
        else:
            self.img_label.setText("⚠️")

    def _on_thumbnail_failed(self):
        self.img_label.setText("❌")

    def mousePressEvent(self, event):
        if self.on_click and event.button() == Qt.MouseButton.LeftButton:
            self.on_click(self.item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.on_double_click and event.button() == Qt.MouseButton.LeftButton:
            self.on_double_click(self.item)
        super().mouseDoubleClickEvent(event)
