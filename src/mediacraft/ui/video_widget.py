from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout


class VideoWidget(QFrame):
    files_dropped = Signal(list)
    clicked = Signal()
    double_clicked = Signal()
    volume_wheel = Signal(int)
    speed_wheel = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setObjectName("videoWidget")
        self.setMinimumSize(480, 270)

        self._placeholder = QLabel("動画ファイルを開くか、ここへドロップしてください", self)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.addWidget(self._placeholder)

        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(QApplication.doubleClickInterval() + 50)
        self._click_timer.timeout.connect(self.clicked.emit)

    def set_media_loaded(self, loaded: bool) -> None:
        self._placeholder.setVisible(not loaded)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._local_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        files = self._local_files(event.mimeData())
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
        else:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.start()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = int(event.angleDelta().y() / 120)
        if steps:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.speed_wheel.emit(steps)
            else:
                self.volume_wheel.emit(steps)
            event.accept()
            return
        super().wheelEvent(event)

    @staticmethod
    def _local_files(mime_data: QMimeData) -> list[str]:
        if not mime_data.hasUrls():
            return []
        return [
            str(Path(url.toLocalFile()))
            for url in mime_data.urls()
            if url.isLocalFile() and Path(url.toLocalFile()).is_file()
        ]
