from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from mediacraft.playlist.playlist_controller import RepeatMode
from mediacraft.ui.direct_slider import DirectSlider
from mediacraft.utils.time_format import format_time, format_time_millis


class ControlBar(QWidget):
    shuffle_requested = Signal()
    previous_requested = Signal()
    play_pause_requested = Signal()
    stop_requested = Signal()
    next_requested = Signal()
    repeat_requested = Signal()
    frame_back_requested = Signal()
    frame_forward_requested = Signal()
    seek_requested = Signal(float)
    volume_requested = Signal(int)
    mute_requested = Signal()
    speed_requested = Signal(float)
    fullscreen_requested = Signal()
    seek_hovered = Signal(float, QPoint)
    seek_hover_left = Signal()

    SPEEDS = (0.10, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 3.00, 4.00)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._duration = 0.0
        self._seeking = False
        self._frame_inspection = False
        self._audio_mode = False
        self._video_codec = ""
        self._audio_codec = ""
        self._frame_number = -1
        self._fps = 0.0
        self._variable_rate: object = None
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
        self.seek_slider.hover_value_changed.connect(self._on_seek_hovered)
        self.seek_slider.hover_left.connect(self.seek_hover_left.emit)

        self.shuffle_button = QPushButton()
        self.previous_button = QPushButton()
        self.play_button = QPushButton()
        self.stop_button = QPushButton()
        self.next_button = QPushButton()
        self.repeat_button = QPushButton()
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

        self._configure_custom_icon_button(
            self.shuffle_button,
            self._shuffle_icon(),
            "シャッフル再生: OFF",
        )
        self.shuffle_button.setCheckable(True)
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
            self.repeat_button,
            self._repeat_icon(one=False),
            "リピート再生: OFF",
        )
        self.repeat_button.setCheckable(True)
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
        transport_row.addWidget(self.shuffle_button)
        transport_row.addWidget(self.previous_button)
        transport_row.addWidget(self.play_button)
        transport_row.addWidget(self.stop_button)
        transport_row.addWidget(self.next_button)
        transport_row.addWidget(self.repeat_button)
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

        self.shuffle_button.clicked.connect(self.shuffle_requested.emit)
        self.previous_button.clicked.connect(self.previous_requested.emit)
        self.play_button.clicked.connect(self.play_pause_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.next_button.clicked.connect(self.next_requested.emit)
        self.repeat_button.clicked.connect(self.repeat_requested.emit)
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
        if self._audio_mode:
            self.frame_label.setText("Audio")
            return
        self._frame_number = frame_number
        self._fps = fps
        self._variable_rate = variable
        self._refresh_media_info()

    def set_codecs(self, video_codec: str, audio_codec: str) -> None:
        self._video_codec = video_codec
        self._audio_codec = audio_codec
        self._refresh_media_info()

    def _refresh_media_info(self) -> None:
        if self._audio_mode:
            self.frame_label.setText("Audio")
            return
        frame_text = "--" if self._frame_number < 0 else f"{self._frame_number:,}"
        if self._variable_rate is True:
            fps_text = "VFR"
        else:
            fps_text = f"{self._fps:.2f} FPS" if self._fps > 0 else "-- FPS"
        codec_text = f"V: {self._video_codec or '—'} / A: {self._audio_codec or '—'}"
        self.frame_label.setText(f"Frame: {frame_text} | {fps_text} | {codec_text}")

    def set_audio_mode(self, enabled: bool) -> None:
        self._audio_mode = enabled
        self.frame_back_button.setEnabled(not enabled)
        self.frame_forward_button.setEnabled(not enabled)
        if enabled:
            self.frame_label.setText("Audio")
        else:
            self._frame_number = -1
            self._fps = 0.0
            self._variable_rate = None
            self._video_codec = ""
            self._audio_codec = ""
            self._refresh_media_info()

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

    def set_shuffle(self, enabled: bool) -> None:
        label = f"シャッフル再生: {'ON' if enabled else 'OFF'}"
        self.shuffle_button.setChecked(enabled)
        self.shuffle_button.setToolTip(label)
        self.shuffle_button.setAccessibleName(label)

    def set_repeat_mode(self, mode: RepeatMode) -> None:
        if mode is RepeatMode.ALL:
            label = "リピート再生: ON"
        elif mode is RepeatMode.ONE:
            label = "1ファイルリピート"
        else:
            label = "リピート再生: OFF"
        self.repeat_button.setChecked(mode is not RepeatMode.OFF)
        self.repeat_button.setIcon(self._repeat_icon(one=mode is RepeatMode.ONE))
        self.repeat_button.setToolTip(label)
        self.repeat_button.setAccessibleName(label)

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

    def _on_seek_hovered(self, value: int, global_position: QPoint) -> None:
        if self._duration <= 0:
            return
        ratio = value / max(1, self.seek_slider.maximum())
        self.seek_hovered.emit(ratio * self._duration, global_position)

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

    @staticmethod
    def _shuffle_icon() -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 255, 255), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(3, 5, 6, 5)
        painter.drawLine(6, 5, 14, 15)
        painter.drawLine(14, 15, 17, 15)
        painter.drawLine(14, 12, 17, 15)
        painter.drawLine(14, 18, 17, 15)
        painter.drawLine(3, 15, 6, 15)
        painter.drawLine(6, 15, 14, 5)
        painter.drawLine(14, 5, 17, 5)
        painter.drawLine(14, 2, 17, 5)
        painter.drawLine(14, 8, 17, 5)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _repeat_icon(*, one: bool) -> QIcon:
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 255, 255), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(4, 6, 15, 6)
        painter.drawLine(12, 3, 15, 6)
        painter.drawLine(12, 9, 15, 6)
        painter.drawLine(15, 6, 17, 8)
        painter.drawLine(17, 8, 17, 11)
        painter.drawLine(16, 14, 5, 14)
        painter.drawLine(8, 11, 5, 14)
        painter.drawLine(8, 17, 5, 14)
        painter.drawLine(5, 14, 3, 12)
        painter.drawLine(3, 12, 3, 9)
        if one:
            badge_rect = QRectF(9, 9, 10, 10)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(badge_rect)

            font = QFont(painter.font())
            font.setBold(True)
            font.setPixelSize(9)
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "1")
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
