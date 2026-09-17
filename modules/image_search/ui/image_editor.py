# -*- coding: utf-8 -*-
"""
Image Annotation & Crop Editor Dialog for Obsidian Addon Suite.
Allows users to annotate images with arrows, circles, and perform rectangular crops
before inserting them into Anki cards, while maintaining the pristine original image
in the recent history.
"""

from typing import Optional, List, Tuple
import math

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QScrollArea,
        QWidget,
        QComboBox,
        QButtonGroup,
        QFrame,
        QSizePolicy,
    )
    from PyQt6.QtGui import (
        QPixmap,
        QPainter,
        QPen,
        QBrush,
        QColor,
        QPolygonF,
        QCursor,
        QKeySequence,
        QShortcut,
    )
    from PyQt6.QtCore import Qt, QPointF, QRectF, QByteArray, QBuffer, QIODevice
except ImportError:
    QDialog = object
    QVBoxLayout = object
    QHBoxLayout = object
    QPushButton = object
    QLabel = object
    QScrollArea = object
    QWidget = object
    QComboBox = object
    QButtonGroup = object
    QFrame = object
    QSizePolicy = object
    QPixmap = None
    QPainter = None
    QPen = None
    QBrush = None
    QColor = None
    QPolygonF = None
    QCursor = None
    QKeySequence = None
    QShortcut = None
    Qt = None
    QPointF = None
    QRectF = None
    QByteArray = None
    QBuffer = None
    QIODevice = None

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


def calculate_arrowhead_points(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    arrow_size: float = 22.0,
    angle_deg: float = 28.0,
) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    """
    Calculates the 3 vertex coordinates of a sharp arrowhead pointing at (end_x, end_y).
    Returns ((end_x, end_y), (p1_x, p1_y), (p2_x, p2_y)).
    Pure mathematical function, completely headless testable.
    """
    angle = math.atan2(end_y - start_y, end_x - start_x)
    rad = math.radians(angle_deg)
    
    p1_x = end_x - arrow_size * math.cos(angle - rad)
    p1_y = end_y - arrow_size * math.sin(angle - rad)
    
    p2_x = end_x - arrow_size * math.cos(angle + rad)
    p2_y = end_y - arrow_size * math.sin(angle + rad)
    
    return ((end_x, end_y), (p1_x, p1_y), (p2_x, p2_y))


def normalize_rect_coords(
    x1: float, y1: float, x2: float, y2: float
) -> Tuple[float, float, float, float]:
    """
    Normalizes two arbitrary corner points into (left, top, width, height).
    Pure mathematical function, completely headless testable.
    """
    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    return (left, top, width, height)


class ImageAnnotationCanvas(QWidget):
    """
    Canvas widget that renders the image in native high resolution while mapping
    user mouse gestures (arrows, circles, crops) directly onto pixel coordinates.
    """

    def __init__(self, pixmap: QPixmap, parent=None):
        if QWidget is not object:
            super().__init__(parent)
        self._original_pixmap: QPixmap = pixmap
        self._current_pixmap: QPixmap = pixmap.copy() if (pixmap and not pixmap.isNull()) else None
        self._history: List[QPixmap] = []
        
        # Tool modes: 'arrow', 'circle', 'crop'
        self.current_tool: str = "arrow"
        self.current_color: str = "#ef4444"  # Default clinical red
        self.stroke_width: int = 4
        
        # Dragging state
        self._is_drawing: bool = False
        self._start_pos: Optional[Tuple[float, float]] = None
        self._current_pos: Optional[Tuple[float, float]] = None
        
        # Crop selection in image coordinate space (left, top, width, height)
        self.active_crop_rect: Optional[Tuple[float, float, float, float]] = None

        if QWidget is not object and self._current_pixmap:
            self.setMinimumSize(self._current_pixmap.size())
            self.resize(self._current_pixmap.size())
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def set_tool(self, tool_name: str):
        self.current_tool = tool_name
        self.active_crop_rect = None
        if self._current_pixmap:
            self.update()

    def set_color(self, hex_color: str):
        self.current_color = hex_color

    def set_stroke_width(self, width: int):
        self.stroke_width = max(1, width)

    def undo(self) -> bool:
        """Reverts the last drawn action or crop."""
        if self._history and self._history:
            self._current_pixmap = self._history.pop()
            self.active_crop_rect = None
            if QWidget is not object:
                self.resize(self._current_pixmap.size())
                self.setMinimumSize(self._current_pixmap.size())
                self.update()
            return True
        return False

    def reset(self):
        """Restores the pristine original image."""
        if self._original_pixmap and not self._original_pixmap.isNull():
            if self._current_pixmap:
                self._history.append(self._current_pixmap.copy())
            self._current_pixmap = self._original_pixmap.copy()
            self.active_crop_rect = None
            if QWidget is not object:
                self.resize(self._current_pixmap.size())
                self.setMinimumSize(self._current_pixmap.size())
                self.update()

    def apply_crop(self) -> bool:
        """Crops the current pixmap to the active crop rectangle."""
        if not self.active_crop_rect or not self._current_pixmap:
            return False
        
        left, top, width, height = self.active_crop_rect
        if width < 5 or height < 5:
            self.active_crop_rect = None
            self.update()
            return False
        
        # Save undo snapshot
        self._history.append(self._current_pixmap.copy())
        
        # Execute crop on native pixmap
        cropped = self._current_pixmap.copy(int(left), int(top), int(width), int(height))
        self._current_pixmap = cropped
        self.active_crop_rect = None
        
        if QWidget is not object:
            self.resize(self._current_pixmap.size())
            self.setMinimumSize(self._current_pixmap.size())
            self.update()
        return True

    def get_final_image_bytes(self, format_name: str = "JPG", quality: int = 92) -> bytes:
        """Exports the annotated/cropped pixmap to raw image bytes."""
        if not self._current_pixmap or self._current_pixmap.isNull():
            return b""
        if QBuffer is None or QByteArray is None:
            return b""
        
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        self._current_pixmap.save(buf, format_name, quality)
        return bytes(ba.data())

    # --- Mouse Event Handlers ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._current_pixmap:
            self._is_drawing = True
            pos = event.position() if hasattr(event, "position") else event.pos()
            self._start_pos = (pos.x(), pos.y())
            self._current_pos = (pos.x(), pos.y())
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_drawing and self._start_pos:
            pos = event.position() if hasattr(event, "position") else event.pos()
            self._current_pos = (pos.x(), pos.y())
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_drawing:
            self._is_drawing = False
            pos = event.position() if hasattr(event, "position") else event.pos()
            self._current_pos = (pos.x(), pos.y())
            
            if self._start_pos and self._current_pos:
                x1, y1 = self._start_pos
                x2, y2 = self._current_pos
                dist = math.hypot(x2 - x1, y2 - y1)
                
                if dist >= 4:
                    if self.current_tool == "crop":
                        # Store normalized crop rectangle
                        self.active_crop_rect = normalize_rect_coords(x1, y1, x2, y2)
                        self.update()
                    else:
                        # Commit annotation onto the active pixmap
                        self._commit_annotation(x1, y1, x2, y2)
                else:
                    self.update()
            
            self._start_pos = None
            self._current_pos = None
        super().mouseReleaseEvent(event)

    def _commit_annotation(self, x1: float, y1: float, x2: float, y2: float):
        """Bakes the arrow or circle directly into the current pixmap with smooth anti-aliasing."""
        if not self._current_pixmap:
            return
        
        # Save state for undo
        self._history.append(self._current_pixmap.copy())
        
        painter = QPainter(self._current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        pen_color = QColor(self.current_color)
        pen = QPen(pen_color, self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        if self.current_tool == "arrow":
            # Draw line body
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            
            # Draw solid arrowhead
            arrow_size = max(16.0, self.stroke_width * 4.2)
            tip, p1, p2 = calculate_arrowhead_points(x1, y1, x2, y2, arrow_size=arrow_size, angle_deg=28.0)
            
            poly = QPolygonF([QPointF(*tip), QPointF(*p1), QPointF(*p2)])
            painter.setBrush(QBrush(pen_color))
            painter.drawPolygon(poly)
            
        elif self.current_tool == "circle":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            left, top, width, height = normalize_rect_coords(x1, y1, x2, y2)
            painter.drawEllipse(QRectF(left, top, width, height))
            
        painter.end()
        self.update()

    def paintEvent(self, event):
        if not self._current_pixmap or self._current_pixmap.isNull():
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # 1. Draw base image
        painter.drawPixmap(0, 0, self._current_pixmap)
        
        # 2. Draw live preview while dragging
        if self._is_drawing and self._start_pos and self._current_pos:
            x1, y1 = self._start_pos
            x2, y2 = self._current_pos
            
            if self.current_tool in ("arrow", "circle"):
                pen_color = QColor(self.current_color)
                pen = QPen(pen_color, self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                
                if self.current_tool == "arrow":
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                    arrow_size = max(16.0, self.stroke_width * 4.2)
                    tip, p1, p2 = calculate_arrowhead_points(x1, y1, x2, y2, arrow_size=arrow_size, angle_deg=28.0)
                    poly = QPolygonF([QPointF(*tip), QPointF(*p1), QPointF(*p2)])
                    painter.setBrush(QBrush(pen_color))
                    painter.drawPolygon(poly)
                elif self.current_tool == "circle":
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    left, top, width, height = normalize_rect_coords(x1, y1, x2, y2)
                    painter.drawEllipse(QRectF(left, top, width, height))
                    
            elif self.current_tool == "crop":
                left, top, width, height = normalize_rect_coords(x1, y1, x2, y2)
                self._draw_crop_overlay(painter, left, top, width, height)
                
        # 3. Draw established crop rectangle if not actively dragging
        elif self.active_crop_rect and self.current_tool == "crop":
            left, top, width, height = self.active_crop_rect
            self._draw_crop_overlay(painter, left, top, width, height)
            
        painter.end()

    def _draw_crop_overlay(self, painter: QPainter, left: float, top: float, width: float, height: float):
        """Draws semi-transparent dark mask with a dashed border around the crop region."""
        img_w = float(self._current_pixmap.width())
        img_h = float(self._current_pixmap.height())
        
        # Dark mask outside selection
        mask_brush = QBrush(QColor(0, 0, 0, 140))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(mask_brush)
        
        # Top band
        painter.drawRect(QRectF(0, 0, img_w, top))
        # Bottom band
        painter.drawRect(QRectF(0, top + height, img_w, img_h - (top + height)))
        # Left band
        painter.drawRect(QRectF(0, top, left, height))
        # Right band
        painter.drawRect(QRectF(left + width, top, img_w - (left + width), height))
        
        # Dashed border around selection
        border_pen = QPen(QColor("#38bdf8"), 2, Qt.PenStyle.DashLine)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(left, top, width, height))


class ImageEditorDialog(QDialog):
    """
    Dedicated modal dialog providing intuitive visual tools (Arrows, Circles, Rectangular Crop)
    for medical and educational image preparation.
    """

    def __init__(self, parent, pixmap: QPixmap, title: str = ""):
        if QDialog is not object:
            super().__init__(parent)
            if Qt is not None and hasattr(Qt, "WindowModality"):
                self.setWindowModality(Qt.WindowModality.WindowModal)
        self.original_pixmap = pixmap
        self.image_title = title
        self.result_data: Optional[bytes] = None
        self.result_ext: str = ".jpg"
        
        self.canvas: Optional[ImageAnnotationCanvas] = None
        self.btn_apply_crop: Optional[QPushButton] = None
        self.btn_undo: Optional[QPushButton] = None

        if QDialog is not object:
            self.init_ui()

    def init_ui(self):
        self.setWindowTitle(tr("image_search_editor_title", "✏️ Editor de Anotação e Corte de Imagem"))
        self.resize(960, 680)
        self.setMinimumSize(720, 520)

        self.setStyleSheet("""
            QDialog {
                background-color: #121216;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QFrame#toolbar {
                background-color: #1a1a22;
                border-bottom: 1px solid #282834;
                padding: 6px;
            }
            QPushButton {
                background-color: #282834;
                border: 1px solid #383848;
                border-radius: 6px;
                padding: 6px 14px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #38384a;
                border-color: #6366f1;
            }
            QPushButton:checked {
                background-color: #6366f1;
                border-color: #818cf8;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton#btn_primary {
                background-color: #7c3aed;
                border: 1px solid #8b5cf6;
                color: #ffffff;
                font-weight: 600;
                padding: 8px 20px;
                font-size: 14px;
            }
            QPushButton#btn_primary:hover {
                background-color: #6d28d9;
            }
            QComboBox {
                background-color: #282834;
                border: 1px solid #383848;
                border-radius: 6px;
                padding: 4px 10px;
                color: #ffffff;
                font-size: 12px;
            }
            QScrollArea {
                background-color: #0c0c0e;
                border: 1px solid #20202a;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Toolbar ---
        toolbar = QFrame(self)
        toolbar.setObjectName("toolbar")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 8, 12, 8)
        tb_layout.setSpacing(8)

        # Tool group buttons (Arrow, Circle, Crop)
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        self.btn_arrow = QPushButton(tr("image_search_tool_arrow", "🏹 Seta"), toolbar)
        self.btn_arrow.setCheckable(True)
        self.btn_arrow.setChecked(True)
        self.btn_arrow.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_arrow.clicked.connect(lambda: self._select_tool("arrow"))
        self.tool_group.addButton(self.btn_arrow)
        tb_layout.addWidget(self.btn_arrow)

        self.btn_circle = QPushButton(tr("image_search_tool_circle", "⭕ Círculo"), toolbar)
        self.btn_circle.setCheckable(True)
        self.btn_circle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_circle.clicked.connect(lambda: self._select_tool("circle"))
        self.tool_group.addButton(self.btn_circle)
        tb_layout.addWidget(self.btn_circle)

        self.btn_crop = QPushButton(tr("image_search_tool_crop", "✂️ Cortar"), toolbar)
        self.btn_crop.setCheckable(True)
        self.btn_crop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_crop.clicked.connect(lambda: self._select_tool("crop"))
        self.tool_group.addButton(self.btn_crop)
        tb_layout.addWidget(self.btn_crop)

        # Separator
        sep1 = QFrame(toolbar)
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #383848;")
        tb_layout.addWidget(sep1)

        # Color Selector Buttons
        colors = [
            ("#ef4444", "🔴"),  # Red
            ("#eab308", "🟡"),  # Yellow
            ("#22c55e", "🟢"),  # Green
            ("#38bdf8", "🔵"),  # Blue
            ("#ffffff", "⚪"),  # White
        ]
        self.color_group = QButtonGroup(self)
        for hex_code, emoji in colors:
            btn_c = QPushButton(emoji, toolbar)
            btn_c.setFixedSize(30, 30)
            btn_c.setCheckable(True)
            btn_c.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_c.setToolTip(hex_code)
            if hex_code == "#ef4444":
                btn_c.setChecked(True)
            btn_c.clicked.connect(lambda checked, c=hex_code: self._select_color(c))
            self.color_group.addButton(btn_c)
            tb_layout.addWidget(btn_c)

        # Stroke Width Selector
        lbl_width = QLabel(tr("image_search_stroke_width", "Espessura:"), toolbar)
        lbl_width.setStyleSheet("color: #94a3b8; font-size: 12px; margin-left: 6px;")
        tb_layout.addWidget(lbl_width)

        self.width_combo = QComboBox(toolbar)
        self.width_combo.addItem("2 px", 2)
        self.width_combo.addItem("4 px", 4)
        self.width_combo.addItem("6 px", 6)
        self.width_combo.addItem("8 px", 8)
        self.width_combo.setCurrentIndex(1)  # Default 4px
        self.width_combo.currentIndexChanged.connect(self._on_width_changed)
        tb_layout.addWidget(self.width_combo)

        # Separator
        sep2 = QFrame(toolbar)
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #383848;")
        tb_layout.addWidget(sep2)

        # Action Buttons: Apply Crop, Undo, Reset
        self.btn_apply_crop = QPushButton(tr("image_search_apply_crop", "Aplicar Corte"), toolbar)
        self.btn_apply_crop.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_apply_crop.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_apply_crop.clicked.connect(self._apply_crop_clicked)
        tb_layout.addWidget(self.btn_apply_crop)

        self.btn_undo = QPushButton(tr("image_search_undo", "↩️ Desfazer"), toolbar)
        self.btn_undo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_undo.clicked.connect(self._undo_clicked)
        tb_layout.addWidget(self.btn_undo)

        self.btn_reset = QPushButton(tr("image_search_reset", "🔄 Redefinir"), toolbar)
        self.btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_reset.clicked.connect(self._reset_clicked)
        tb_layout.addWidget(self.btn_reset)

        tb_layout.addStretch(1)

        main_layout.addWidget(toolbar)

        # --- Central Scrollable Canvas Area ---
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(False)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.canvas = ImageAnnotationCanvas(self.original_pixmap, parent=scroll_area)
        scroll_area.setWidget(self.canvas)
        main_layout.addWidget(scroll_area, stretch=1)

        # --- Bottom Action Bar ---
        bottom_bar = QFrame(self)
        bottom_bar.setStyleSheet("background-color: #16161c; border-top: 1px solid #282834; padding: 10px 14px;")
        bb_layout = QHBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(14, 8, 14, 8)
        bb_layout.setSpacing(10)

        self.lbl_hint = QLabel(
            tr("image_search_editor_hint", "Selecione uma ferramenta (Seta, Círculo, Cortar) e arraste sobre a imagem. Clique em 'Aplicar Corte' para executar o corte."),
            bottom_bar,
        )
        self.lbl_hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        bb_layout.addWidget(self.lbl_hint, stretch=1)

        self.btn_cancel = QPushButton(tr("cancel", "Cancelar"), bottom_bar)
        self.btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_cancel.clicked.connect(self.reject)
        bb_layout.addWidget(self.btn_cancel)

        self.btn_insert = QPushButton(
            tr("image_search_insert_edited", "⬇️ Inserir Imagem Editada no Card"),
            bottom_bar,
        )
        self.btn_insert.setObjectName("btn_primary")
        self.btn_insert.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_insert.clicked.connect(self._insert_edited_clicked)
        bb_layout.addWidget(self.btn_insert)

        main_layout.addWidget(bottom_bar)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._undo_clicked)
        QShortcut(QKeySequence("Escape"), self, activated=self.reject)

    def _select_tool(self, tool_name: str):
        if self.canvas:
            self.canvas.set_tool(tool_name)

    def _select_color(self, hex_color: str):
        if self.canvas:
            self.canvas.set_color(hex_color)

    def _on_width_changed(self, index: int):
        val = self.width_combo.currentData()
        if val and self.canvas:
            self.canvas.set_stroke_width(int(val))

    def _apply_crop_clicked(self):
        if self.canvas:
            self.canvas.apply_crop()

    def _undo_clicked(self):
        if self.canvas:
            self.canvas.undo()

    def _reset_clicked(self):
        if self.canvas:
            self.canvas.reset()

    def _insert_edited_clicked(self):
        """Exports the edited image bytes and closes dialog with accepted status."""
        if not self.canvas:
            self.reject()
            return
        
        data = self.canvas.get_final_image_bytes("JPG", 92)
        if data and len(data) > 0:
            self.result_data = data
            self.result_ext = ".jpg"
            self.accept()
        else:
            self.reject()

    def exec(self) -> int:
        if QDialog is not object and hasattr(super(), "exec"):
            return super().exec()
        return 1 if (self.result_data and len(self.result_data) > 0) else 0

    def exec_(self) -> int:
        return self.exec()

    def accept(self):
        if QDialog is not object and hasattr(super(), "accept"):
            super().accept()

    def reject(self):
        if QDialog is not object and hasattr(super(), "reject"):
            super().reject()
