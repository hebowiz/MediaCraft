from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class ToastNotification(QWidget):
    def __init__(self, parent: QWidget) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(parent, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                background-color: rgba(18, 20, 24, 220);
                border: 1px solid rgba(255, 255, 255, 55);
                border-radius: 7px;
                padding: 9px 16px;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(
        self,
        message: str,
        host: QWidget,
        *,
        duration_ms: int = 2500,
        bottom_margin: int = 24,
    ) -> None:
        self.label.setText(message)
        self.adjustSize()
        host_origin = host.mapToGlobal(QPoint(0, 0))
        x = host_origin.x() + max(0, (host.width() - self.width()) // 2)
        y = host_origin.y() + max(0, host.height() - self.height() - bottom_margin)
        self.move(x, y)
        self.show()
        self.raise_()
        self._timer.start(duration_ms)

    def stop(self) -> None:
        self._timer.stop()
        self.hide()
