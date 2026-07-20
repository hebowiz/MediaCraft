from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QMouseEvent,
    QPixmap,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QWidget

from mediacraft.utils.drop_paths import local_drop_paths


class ArtworkLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_image(self, image: QImage | None) -> None:
        self._source = QPixmap.fromImage(image) if image is not None else QPixmap()
        self._refresh_pixmap()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()

    def _refresh_pixmap(self) -> None:
        if self._source.isNull():
            self.clear()
            return
        self.setPixmap(
            self._source.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


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

        self._placeholder = QLabel(
            "動画・音声ファイルを開くか、ここへドロップしてください", self
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._audio_panel = QWidget(self)
        self._audio_panel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._audio_panel.setStyleSheet("background-color: transparent;")
        self._audio_artwork = ArtworkLabel(self._audio_panel)
        self._audio_title = QLabel(self._audio_panel)
        self._audio_artist = QLabel(self._audio_panel)
        self._audio_album = QLabel(self._audio_panel)
        self._audio_bitrate = QLabel(self._audio_panel)
        for label in (
            self._audio_artwork,
            self._audio_title,
            self._audio_artist,
            self._audio_album,
            self._audio_bitrate,
        ):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._audio_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        self._audio_artist.setStyleSheet("font-size: 14px;")
        self._audio_album.setStyleSheet("font-size: 14px;")
        self._audio_bitrate.setStyleSheet("font-size: 13px; color: #9aa3af;")
        for label in (self._audio_title, self._audio_artist, self._audio_album):
            label.setWordWrap(True)

        audio_layout = QVBoxLayout(self._audio_panel)
        audio_layout.setContentsMargins(28, 20, 28, 20)
        audio_layout.addStretch(1)
        audio_layout.addWidget(self._audio_artwork, 0, Qt.AlignmentFlag.AlignCenter)
        audio_layout.addSpacing(24)
        audio_layout.addWidget(self._audio_title)
        audio_layout.addSpacing(5)
        audio_layout.addWidget(self._audio_artist)
        audio_layout.addWidget(self._audio_album)
        audio_layout.addWidget(self._audio_bitrate)
        audio_layout.addStretch(1)
        self._audio_panel.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self._placeholder)
        layout.addWidget(self._audio_panel)

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
        self._audio_panel.hide()
        if not loaded:
            self._placeholder.setText(
                "動画・音声ファイルを開くか、ここへドロップしてください"
            )
            self._placeholder.setStyleSheet("")
        self._placeholder.setVisible(not loaded)

    def set_audio_loaded(self, file_name: str) -> None:
        self._placeholder.hide()
        self._audio_panel.show()
        self.set_audio_metadata(
            title=Path(file_name).stem,
            artist="",
            album="",
            bitrate_kbps=None,
            codec="",
            artwork=None,
        )

    def set_audio_metadata(
        self,
        *,
        title: str,
        artist: str,
        album: str,
        bitrate_kbps: int | None,
        codec: str,
        artwork: QImage | None,
    ) -> None:
        self._audio_title.setText(title or "—")
        self._audio_artist.setText(f"Artist: {artist or '—'}")
        self._audio_album.setText(f"Album: {album or '—'}")
        bitrate = f"{bitrate_kbps:,} kbps" if bitrate_kbps is not None else "—"
        self._audio_bitrate.setText(f"Codec: {codec or '—'} / Bitrate: {bitrate}")
        self._audio_artwork.set_image(artwork)
        self._resize_audio_artwork()

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
        self._resize_audio_artwork()
        if self._windows_media_control is not None:
            self._windows_media_control.setGeometry(self.rect())

    def _resize_audio_artwork(self) -> None:
        details_height = sum(
            label.sizeHint().height()
            for label in (
                self._audio_title,
                self._audio_artist,
                self._audio_album,
                self._audio_bitrate,
            )
        )
        horizontal_space = max(1, self.width() - 56)
        vertical_space = max(1, self.height() - details_height - 93)
        side = min(horizontal_space, vertical_space)
        self._audio_artwork.setFixedSize(side, side)
