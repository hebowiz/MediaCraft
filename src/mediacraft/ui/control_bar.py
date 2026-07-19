from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from mediacraft.ui.direct_slider import DirectSlider
from mediacraft.utils.time_format import format_time, format_time_millis


class ControlBar(QWidget):
    previous_requested = Signal()
    play_pause_requested = Signal()
    stop_requested = Signal()
    next_requested = Signal()
    frame_back_requested = Signal()
    frame_forward_requested = Signal()
    seek_requested = Signal(float)
    volume_requested = Signal(int)
    mute_requested = Signal()
    speed_requested = Signal(float)
    fullscreen_requested = Signal()

    SPEEDS = (0.10, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 3.00, 4.00)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._duration = 0.0
        self._seeking = False
        self._frame_inspection = False
        self._ab_start: float | None = None
        self._ab_end: float | None = None
        self._ab_enabled = False
        self._white_icon_cache: dict[QStyle.StandardPixmap, QIcon] = {}

        self.seek_slider = DirectSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setObjectName("seekSlider")
        self.seek_slider.set_centered_track(True)
        self.seek_slider.setRange(0, 10_000)
        self.seek_slider.setEnabled(False)
        self.seek_slider.interaction_started.connect(self._on_seek_started)
        self.seek_slider.value_committed.connect(self._on_seek_finished)

        self.previous_button = QPushButton()
        self.play_button = QPushButton()
        self.stop_button = QPushButton()
        self.next_button = QPushButton()
        self.frame_back_button = QPushButton()
        self.frame_forward_button = QPushButton()
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.frame_label = QLabel("Frame: -- | -- FPS")

        self.speed_combo = QComboBox()
        self.speed_combo.setEditable(True)
        self.speed_combo.lineEdit().setReadOnly(True)
        for speed in self.SPEEDS:
            self.speed_combo.addItem(f"{speed:.2f}x", speed)
        self.speed_combo.setCurrentIndex(self.SPEEDS.index(1.0))

        self.mute_button = QPushButton()
        self.volume_slider = DirectSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(120)
        self.volume_label = QLabel("100%")
        self.fullscreen_button = QPushButton()

        self._configure_icon_button(
            self.previous_button,
            QStyle.StandardPixmap.SP_MediaSkipBackward,
            "前のファイル",
        )
        self._configure_icon_button(
            self.play_button,
            QStyle.StandardPixmap.SP_MediaPlay,
            "再生",
        )
        self._configure_icon_button(
            self.stop_button,
            QStyle.StandardPixmap.SP_MediaStop,
            "停止",
        )
        self._configure_icon_button(
            self.next_button,
            QStyle.StandardPixmap.SP_MediaSkipForward,
            "次のファイル",
        )
        self._configure_custom_icon_button(
            self.frame_back_button,
            self._frame_step_icon(forward=False),
            "1フレーム戻る",
        )
        self._configure_custom_icon_button(
            self.frame_forward_button,
            self._frame_step_icon(forward=True),
            "1フレーム進む",
        )
        self._configure_icon_button(
            self.mute_button,
            QStyle.StandardPixmap.SP_MediaVolume,
            "ミュート",
        )
        self._configure_icon_button(
            self.fullscreen_button,
            QStyle.StandardPixmap.SP_TitleBarMaxButton,
            "フルスクリーン",
        )

        transport_row = QHBoxLayout()
        transport_row.addWidget(self.previous_button)
        transport_row.addWidget(self.play_button)
        transport_row.addWidget(self.stop_button)
        transport_row.addWidget(self.next_button)
        transport_row.addWidget(self.frame_back_button)
        transport_row.addWidget(self.frame_forward_button)
        transport_row.addWidget(self.time_label)
        transport_row.addWidget(self.frame_label)
        transport_row.addStretch(1)
        transport_row.addWidget(self.speed_combo)
        transport_row.addWidget(self.mute_button)
        transport_row.addWidget(self.volume_slider)
        transport_row.addWidget(self.volume_label)
        transport_row.addWidget(self.fullscreen_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.addWidget(self.seek_slider)
        layout.addLayout(transport_row)

        self.previous_button.clicked.connect(self.previous_requested.emit)
        self.play_button.clicked.connect(self.play_pause_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.next_button.clicked.connect(self.next_requested.emit)
        self.frame_back_button.clicked.connect(self.frame_back_requested.emit)
        self.frame_forward_button.clicked.connect(self.frame_forward_requested.emit)
        self.volume_slider.valueChanged.connect(self.volume_requested.emit)
        self.mute_button.clicked.connect(self.mute_requested.emit)
        self.speed_combo.currentIndexChanged.connect(self._emit_speed)
        self.fullscreen_button.clicked.connect(self.fullscreen_requested.emit)

    def set_position(self, position: float, duration: float) -> None:
        self._duration = duration
        self.seek_slider.setEnabled(duration > 0)
        if not self._seeking:
            value = int((position / duration) * self.seek_slider.maximum()) if duration else 0
            self.seek_slider.setValue(max(0, min(self.seek_slider.maximum(), value)))
        formatter = format_time_millis if self._frame_inspection else format_time
        self.time_label.setText(f"{formatter(position)} / {formatter(duration)}")
        self.seek_slider.set_ab_points(
            self._ab_start,
            self._ab_end,
            duration,
            self._ab_enabled,
        )

    def set_ab_points(self, start: float, end: float, enabled: bool) -> None:
        self._ab_start = start if start >= 0 else None
        self._ab_end = end if end >= 0 else None
        self._ab_enabled = enabled
        self.seek_slider.set_ab_points(
            self._ab_start,
            self._ab_end,
            self._duration,
            enabled,
        )
        details: list[str] = []
        if self._ab_start is not None:
            details.append(f"A: {format_time_millis(self._ab_start)}")
        if self._ab_end is not None:
            details.append(f"B: {format_time_millis(self._ab_end)}")
        if enabled:
            details.append("A-Bリピート中")
        self.seek_slider.setToolTip("\n".join(details))

    def set_frame_info(
        self,
        frame_number: int,
        _approximate: bool,
        fps: float,
        variable: object,
    ) -> None:
        frame_text = "--" if frame_number < 0 else f"{frame_number:,}"
        if variable is True:
            fps_text = "VFR"
        else:
            fps_text = f"{fps:.2f} FPS" if fps > 0 else "-- FPS"
        self.frame_label.setText(f"Frame: {frame_text} | {fps_text}")

    def set_frame_inspection(self, enabled: bool) -> None:
        self._frame_inspection = enabled
        self.frame_label.setStyleSheet("font-weight: 700;" if enabled else "")
        for widget in (
            self.speed_combo,
            self.mute_button,
            self.volume_slider,
            self.volume_label,
        ):
            widget.setVisible(not enabled)

    def set_playing(self, playing: bool) -> None:
        icon = QStyle.StandardPixmap.SP_MediaPause if playing else QStyle.StandardPixmap.SP_MediaPlay
        label = "一時停止" if playing else "再生"
        self.play_button.setIcon(self._white_standard_icon(icon))
        self.play_button.setToolTip(label)
        self.play_button.setAccessibleName(label)

    def set_volume(self, volume: int, muted: bool) -> None:
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)
        self.volume_label.setText(f"{volume}%")
        icon = QStyle.StandardPixmap.SP_MediaVolumeMuted if muted else QStyle.StandardPixmap.SP_MediaVolume
        label = "ミュート解除" if muted else "ミュート"
        self.mute_button.setIcon(self._white_standard_icon(icon))
        self.mute_button.setToolTip(label)
        self.mute_button.setAccessibleName(label)

    def set_fullscreen(self, fullscreen: bool) -> None:
        icon = (
            QStyle.StandardPixmap.SP_TitleBarNormalButton
            if fullscreen
            else QStyle.StandardPixmap.SP_TitleBarMaxButton
        )
        label = "フルスクリーン解除" if fullscreen else "フルスクリーン"
        self.fullscreen_button.setIcon(self._white_standard_icon(icon))
        self.fullscreen_button.setToolTip(label)
        self.fullscreen_button.setAccessibleName(label)

    def set_speed(self, speed: float) -> None:
        self.speed_combo.blockSignals(True)
        try:
            index = self.SPEEDS.index(speed)
        except ValueError:
            self.speed_combo.setCurrentIndex(-1)
            self.speed_combo.setEditText(f"{speed:.2f}x")
        else:
            self.speed_combo.setCurrentIndex(index)
        self.speed_combo.blockSignals(False)

    def _on_seek_started(self) -> None:
        self._seeking = True

    def _on_seek_finished(self, value: int) -> None:
        self._seeking = False
        if self._duration > 0:
            ratio = value / self.seek_slider.maximum()
            self.seek_requested.emit(ratio * self._duration)

    def _emit_speed(self, index: int) -> None:
        speed = self.speed_combo.itemData(index)
        if speed is not None:
            self.speed_requested.emit(float(speed))

    def _configure_icon_button(
        self,
        button: QPushButton,
        icon: QStyle.StandardPixmap,
        label: str,
    ) -> None:
        self._configure_custom_icon_button(button, self._white_standard_icon(icon), label)

    @staticmethod
    def _configure_custom_icon_button(
        button: QPushButton,
        icon: QIcon,
        label: str,
    ) -> None:
        button.setFixedSize(40, 34)
        button.setIconSize(QSize(20, 20))
        button.setIcon(icon)
        button.setToolTip(label)
        button.setAccessibleName(label)

    @staticmethod
    def _frame_step_icon(*, forward: bool) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 255, 255), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        frame_left = 3 if forward else 9
        painter.drawRoundedRect(frame_left, 4, 8, 12, 1, 1)
        if forward:
            painter.drawLine(11, 10, 17, 10)
            painter.drawLine(14, 7, 17, 10)
            painter.drawLine(14, 13, 17, 10)
        else:
            painter.drawLine(3, 10, 9, 10)
            painter.drawLine(3, 10, 6, 7)
            painter.drawLine(3, 10, 6, 13)
        painter.end()
        return QIcon(pixmap)

    def _white_standard_icon(self, icon: QStyle.StandardPixmap) -> QIcon:
        cached = self._white_icon_cache.get(icon)
        if cached is not None:
            return cached

        pixmap = self.style().standardIcon(icon).pixmap(QSize(20, 20))
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(255, 255, 255))
        painter.end()

        white_icon = QIcon(pixmap)
        self._white_icon_cache[icon] = white_icon
        return white_icon
