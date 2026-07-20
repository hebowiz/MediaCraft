from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from mediacraft.utils.time_format import format_time


class ThumbnailPreview(QWidget):
    IMAGE_WIDTH = 240
    IMAGE_HEIGHT = 135

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setObjectName("thumbnailPreview")
        self.setStyleSheet(
            """
            QWidget#thumbnailPreview {
                background: rgba(20, 22, 27, 235);
                border: 1px solid #69717d;
                border-radius: 6px;
            }
            QLabel { color: white; border: none; background: transparent; }
            """
        )

        self.image_label = QLabel("読み込み中…")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)
        self.image_label.setStyleSheet("background: #111318; color: #aeb5c0;")
        self.time_label = QLabel("00:00:00")
        self.frame_label = QLabel("Frame: --")

        details = QHBoxLayout()
        details.addWidget(self.time_label)
        details.addStretch(1)
        details.addWidget(self.frame_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 5)
        layout.setSpacing(4)
        layout.addWidget(self.image_label)
        layout.addLayout(details)

    def show_pending(
        self,
        timestamp: float,
        frame_text: str,
        anchor: QPoint,
    ) -> None:
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("読み込み中…")
        self._show_details(timestamp, frame_text, anchor)

    def show_thumbnail(
        self,
        image: QImage,
        timestamp: float,
        frame_text: str,
        anchor: QPoint,
    ) -> None:
        pixmap = QPixmap.fromImage(image).scaled(
            self.IMAGE_WIDTH,
            self.IMAGE_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setText("")
        self.image_label.setPixmap(pixmap)
        self._show_details(timestamp, frame_text, anchor)

    def _show_details(self, timestamp: float, frame_text: str, anchor: QPoint) -> None:
        self.time_label.setText(format_time(timestamp))
        self.frame_label.setText(frame_text)
        self.adjustSize()
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        x = anchor.x() - self.width() // 2
        y = anchor.y() - self.height() - 14
        if screen is not None:
            bounds = screen.availableGeometry()
            x = max(bounds.left(), min(x, bounds.right() - self.width() + 1))
            if y < bounds.top():
                y = anchor.y() + 18
        self.move(x, y)
        self.show()
        self.raise_()
