from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout

from mediacraft.utils.drop_paths import local_drop_paths


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
        self._windows_media_control = None

    def windows_media_control(self):
        if self._windows_media_control is None:
            from PySide6.QtAxContainer import QAxWidget

            control = QAxWidget("WMPlayer.OCX", self)
            control.setGeometry(self.rect())
            control.hide()
            self._windows_media_control = control
        return self._windows_media_control

    def set_media_loaded(self, loaded: bool) -> None:
        self._placeholder.setVisible(not loaded)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if local_drop_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = local_drop_paths(event.mimeData())
        if paths:
            self.files_dropped.emit(paths)
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

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._windows_media_control is not None:
            self._windows_media_control.setGeometry(self.rect())
