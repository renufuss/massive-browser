"""Thumbnail-grid view for managing many browsers at a glance.

Designed for the "100 browsers" case: instead of scanning a long table, the user
sees a wall of small live thumbnails (one per browser) that reflow to the window
width. Clicking a thumbnail opens a large preview window with full details.

Contents:
  * ``FlowLayout``   - a wrapping layout (adapted from the classic Qt example).
  * ``PreviewCard``  - one small clickable tile (thumbnail + name + status).
  * ``PreviewGrid``  - scroll area holding all the cards.
  * ``PreviewDialog``- the enlarged single-browser view.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from browser.models import BrowserInstance
from ui.styles import status_color


class FlowLayout(QLayout):
    """A layout that lays items left-to-right and wraps to the next line."""

    def __init__(self, parent: QWidget | None = None, margin: int = 8, spacing: int = 10) -> None:
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items: list = []

    def addItem(self, item) -> None:  # noqa: N802 (Qt naming)
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x, y, line_height = rect.x(), rect.y(), 0
        spacing = self.spacing()
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + spacing
            if next_x - spacing > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + spacing
                next_x = x + hint.width() + spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()


class PreviewCard(QFrame):
    """A single small, clickable browser tile."""

    clicked = Signal(str)  # instance_id

    def __init__(
        self,
        instance: BrowserInstance,
        tile_w: int = 160,
        tile_h: int = 100,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.instance_id = instance.instance_id
        self._tile_w = tile_w
        self._tile_h = tile_h
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "PreviewCard { border: 1px solid palette(mid); border-radius: 6px; }"
            "PreviewCard:hover { border: 2px solid palette(highlight); }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        self._thumb = QLabel("loading...")
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setFixedSize(tile_w, tile_h)
        self._thumb.setStyleSheet("background: palette(base); color: palette(mid);")

        self._title = QLabel(f"{instance.index}. {instance.name}")
        title_font = self._title.font()
        title_font.setBold(True)
        self._title.setFont(title_font)

        self._subtitle = QLabel(f"{instance.engine.name} - {instance.profile.name}")
        self._subtitle.setStyleSheet("color: palette(mid);")
        self._subtitle.setWordWrap(True)

        self._status = QLabel(instance.status)

        for widget in (self._title, self._subtitle, self._status):
            widget.setMaximumWidth(tile_w)

        layout.addWidget(self._thumb)
        layout.addWidget(self._title)
        layout.addWidget(self._subtitle)
        layout.addWidget(self._status)

        self.set_status(instance.status)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._tile_w + 14, self._tile_h + 78)

    def set_status(self, status: str) -> None:
        self._status.setText(status)
        color = status_color(status)
        self._status.setStyleSheet(
            f"color: {color}; font-weight: 600;" if color else "font-weight: 600;"
        )

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        self._thumb.setPixmap(
            pixmap.scaled(
                self._thumb.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def set_tile_size(self, tile_w: int, tile_h: int) -> None:
        self._tile_w, self._tile_h = tile_w, tile_h
        self._thumb.setFixedSize(tile_w, tile_h)
        for widget in (self._title, self._subtitle, self._status):
            widget.setMaximumWidth(tile_w)
        self.updateGeometry()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.instance_id)
        super().mouseReleaseEvent(event)


class PreviewGrid(QScrollArea):
    """Scrollable wall of :class:`PreviewCard` tiles."""

    card_clicked = Signal(str)  # instance_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._inner = QWidget()
        self._flow = FlowLayout(self._inner)
        self.setWidget(self._inner)
        self._cards: dict[str, PreviewCard] = {}
        self._tile = (160, 100)

    def clear(self) -> None:
        while self._flow.count():
            item = self._flow.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

    def add_card(self, instance: BrowserInstance) -> None:
        card = PreviewCard(instance, self._tile[0], self._tile[1])
        card.clicked.connect(self.card_clicked)
        self._cards[instance.instance_id] = card
        self._flow.addWidget(card)

    def set_status(self, instance_id: str, status: str) -> None:
        card = self._cards.get(instance_id)
        if card is not None:
            card.set_status(status)

    def set_thumbnail(self, instance_id: str, pixmap: QPixmap) -> None:
        card = self._cards.get(instance_id)
        if card is not None:
            card.set_thumbnail(pixmap)

    def set_tile_size(self, tile_w: int, tile_h: int) -> None:
        self._tile = (tile_w, tile_h)
        for card in self._cards.values():
            card.set_tile_size(tile_w, tile_h)
        self._inner.adjustSize()


class PreviewDialog(QDialog):
    """Enlarged single-browser preview with details and a refresh button."""

    refresh_requested = Signal(str)  # instance_id
    show_window_requested = Signal(str)  # instance_id

    def __init__(self, instance: BrowserInstance, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.instance_id = instance.instance_id
        self.setWindowTitle(f"{instance.name} - preview")
        self.resize(900, 640)

        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>{instance.name}</b> &nbsp; | &nbsp; {instance.engine.name} &nbsp; | "
            f"&nbsp; {instance.profile.name} &nbsp; | &nbsp; id {instance.instance_id} &nbsp; | "
            f"&nbsp; {instance.profile.viewport_width}x{instance.profile.viewport_height} "
            f"&nbsp; | &nbsp; {instance.locale} / {instance.timezone}"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)

        self._image = QLabel("Capturing preview...")
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image.setMinimumSize(640, 400)
        self._image.setStyleSheet("background: palette(base); color: palette(mid);")
        self._image.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setWidget(self._image)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        buttons = QHBoxLayout()
        show_btn = QPushButton("Show browser window")
        refresh_btn = QPushButton("Refresh")
        close_btn = QPushButton("Close")
        show_btn.clicked.connect(lambda: self.show_window_requested.emit(self.instance_id))
        refresh_btn.clicked.connect(lambda: self.refresh_requested.emit(self.instance_id))
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(show_btn)
        buttons.addWidget(refresh_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)

        layout.addWidget(info)
        layout.addWidget(scroll, stretch=1)
        layout.addLayout(buttons)

    def set_image(self, pixmap: QPixmap) -> None:
        self._image.setPixmap(pixmap)
        self._image.resize(pixmap.size())
