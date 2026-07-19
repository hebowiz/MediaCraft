from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from mediacraft.ui.control_bar import ControlBar


class FullscreenOverlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        super().__init__(parent, flags)
        self.setObjectName("fullscreenOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("#fullscreenOverlay { background-color: transparent; }")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._control_bar: ControlBar | None = None

    def attach_control_bar(self, control_bar: ControlBar) -> None:
        if self._control_bar is control_bar:
            return
        self._control_bar = control_bar
        self._layout.addWidget(control_bar)
        control_bar.setObjectName("fullscreenOverlayControls")
        control_bar.setStyleSheet(
            """
            #fullscreenOverlayControls,
            #fullscreenOverlayControls QLabel,
            #fullscreenOverlayControls QSlider {
                background-color: transparent;
            }
            """
        )

    def detach_control_bar(self) -> ControlBar | None:
        control_bar = self._control_bar
        if control_bar is None:
            return None
        self._layout.removeWidget(control_bar)
        control_bar.setObjectName("")
        control_bar.setStyleSheet("")
        self._control_bar = None
        return control_bar

    def update_position(self, host: QWidget) -> None:
        if self._control_bar is None:
            return

        host_origin = host.mapToGlobal(QPoint(0, 0))
        overlay_width = host.width()
        overlay_height = self._control_bar.sizeHint().height()
        y = host_origin.y() + host.height() - overlay_height
        self.setGeometry(host_origin.x(), y, overlay_width, overlay_height)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(18, 20, 24, 190))
        painter.end()
        super().paintEvent(event)
