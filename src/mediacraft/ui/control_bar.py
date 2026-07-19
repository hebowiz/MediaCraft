from PySide6.QtCore import QSize, Qt, Signal
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
from mediacraft.utils.time_format import format_time


class ControlBar(QWidget):
    play_pause_requested = Signal()
    stop_requested = Signal()
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

        self.seek_slider = DirectSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 10_000)
        self.seek_slider.setEnabled(False)
        self.seek_slider.interaction_started.connect(self._on_seek_started)
        self.seek_slider.value_committed.connect(self._on_seek_finished)

        self.play_button = QPushButton()
        self.stop_button = QPushButton()
        self.time_label = QLabel("00:00:00 / 00:00:00")

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
            self.mute_button,
            QStyle.StandardPixmap.SP_MediaVolume,
            "ミュート",
        )
        self._configure_icon_button(
            self.fullscreen_button,
            QStyle.StandardPixmap.SP_TitleBarMaxButton,
            "フルスクリーン",
        )

        row = QHBoxLayout()
        row.addWidget(self.play_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.time_label)
        row.addStretch(1)
        row.addWidget(QLabel("速度"))
        row.addWidget(self.speed_combo)
        row.addWidget(self.mute_button)
        row.addWidget(self.volume_slider)
        row.addWidget(self.volume_label)
        row.addWidget(self.fullscreen_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.addWidget(self.seek_slider)
        layout.addLayout(row)

        self.play_button.clicked.connect(self.play_pause_requested.emit)
        self.stop_button.clicked.connect(self.stop_requested.emit)
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
        self.time_label.setText(f"{format_time(position)} / {format_time(duration)}")

    def set_playing(self, playing: bool) -> None:
        icon = QStyle.StandardPixmap.SP_MediaPause if playing else QStyle.StandardPixmap.SP_MediaPlay
        label = "一時停止" if playing else "再生"
        self.play_button.setIcon(self.style().standardIcon(icon))
        self.play_button.setToolTip(label)
        self.play_button.setAccessibleName(label)

    def set_volume(self, volume: int, muted: bool) -> None:
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)
        self.volume_label.setText(f"{volume}%")
        icon = QStyle.StandardPixmap.SP_MediaVolumeMuted if muted else QStyle.StandardPixmap.SP_MediaVolume
        label = "ミュート解除" if muted else "ミュート"
        self.mute_button.setIcon(self.style().standardIcon(icon))
        self.mute_button.setToolTip(label)
        self.mute_button.setAccessibleName(label)

    def set_fullscreen(self, fullscreen: bool) -> None:
        icon = (
            QStyle.StandardPixmap.SP_TitleBarNormalButton
            if fullscreen
            else QStyle.StandardPixmap.SP_TitleBarMaxButton
        )
        label = "フルスクリーン解除" if fullscreen else "フルスクリーン"
        self.fullscreen_button.setIcon(self.style().standardIcon(icon))
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
        button.setFixedSize(40, 34)
        button.setIconSize(QSize(20, 20))
        button.setIcon(self.style().standardIcon(icon))
        button.setToolTip(label)
        button.setAccessibleName(label)
