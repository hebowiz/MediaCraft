import logging
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from mediacraft.player.playback_state import PlaybackState
from mediacraft.player.player_backend import BackendError, PlayerBackend

logger = logging.getLogger(__name__)


class PlayerController(QObject):
    state_changed = Signal(object)
    position_changed = Signal(float, float)
    playback_changed = Signal(bool)
    volume_changed = Signal(int, bool)
    speed_changed = Signal(float)
    frame_metrics_changed = Signal(int, float)
    manual_navigation_started = Signal()
    file_changed = Signal(str)
    media_ended = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, backend: PlayerBackend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._state = PlaybackState.NO_MEDIA
        self._current_file: Path | None = None
        self._initialized = False
        self._volume = 100
        self._muted = False
        self._speed = 1.0
        self._position = 0.0
        self._duration = 0.0
        self._frame_inspection = False
        self._end_reported = False

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self.refresh)

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def current_file(self) -> Path | None:
        return self._current_file

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def frame_inspection(self) -> bool:
        return self._frame_inspection

    @property
    def position(self) -> float:
        return self._position

    @property
    def duration(self) -> float:
        return self._duration

    def initialize(self, window_id: int) -> bool:
        if self._initialized:
            return True
        try:
            self._backend.initialize(window_id)
            self._backend.set_volume(self._volume)
            self._backend.set_mute(self._muted)
            self._backend.set_speed(self._speed)
        except BackendError as exc:
            self._fail(str(exc))
            return False
        self._initialized = True
        self._timer.start()
        return True

    def load_file(self, path: str | Path) -> bool:
        media_path = Path(path).expanduser().resolve()
        if not media_path.is_file():
            self._fail(f"ファイルが見つかりません: {media_path}")
            return False
        if not self._initialized:
            self._fail("再生バックエンドが初期化されていません。")
            return False

        self._set_state(PlaybackState.LOADING)
        try:
            self._backend.load(media_path)
        except BackendError as exc:
            self._fail(str(exc))
            return False

        self._current_file = media_path
        self._position = 0.0
        self._duration = 0.0
        self._frame_inspection = False
        self._end_reported = False
        self.file_changed.emit(str(media_path))
        self._set_state(PlaybackState.PLAYING)
        self.playback_changed.emit(True)
        return True

    def toggle_play_pause(self) -> None:
        if self._current_file is None:
            return
        try:
            if self._backend.is_paused():
                self._frame_inspection = False
                if self._state is PlaybackState.ENDED:
                    self._backend.seek_absolute(0.0)
                    self._end_reported = False
                self._backend.play()
                self._set_state(PlaybackState.PLAYING)
                self.playback_changed.emit(True)
            else:
                self._backend.pause()
                self._set_state(PlaybackState.PAUSED)
                self.playback_changed.emit(False)
        except BackendError as exc:
            self._fail(str(exc))

    def stop(self) -> None:
        if self._current_file is None:
            return
        try:
            self._backend.stop()
        except BackendError as exc:
            self._fail(str(exc))
            return
        try:
            duration = self._backend.duration()
        except BackendError:
            duration = 0.0
        self._position = 0.0
        self._duration = duration
        self.position_changed.emit(self._position, self._duration)
        self._frame_inspection = False
        self._end_reported = False
        self.playback_changed.emit(False)
        self._set_state(PlaybackState.STOPPED)

    def clear_media(self) -> bool:
        if self._initialized:
            try:
                self._backend.clear_media()
            except BackendError as exc:
                self._fail(str(exc))
                return False
        self._current_file = None
        self._position = 0.0
        self._duration = 0.0
        self._frame_inspection = False
        self._end_reported = False
        self.position_changed.emit(0.0, 0.0)
        self.frame_metrics_changed.emit(-1, 0.0)
        self.playback_changed.emit(False)
        self._set_state(PlaybackState.NO_MEDIA)
        return True

    def seek_absolute(self, seconds: float, *, user_initiated: bool = True) -> None:
        if self._current_file is None:
            return
        try:
            self._backend.seek_absolute(seconds)
            self._end_reported = False
        except BackendError as exc:
            self._fail(str(exc))
            return
        self._position = max(0.0, min(self._duration, seconds)) if self._duration > 0 else max(0.0, seconds)
        if user_initiated:
            self.manual_navigation_started.emit()
        self.position_changed.emit(self._position, self._duration)

    def seek_relative(self, seconds: float) -> None:
        if self._current_file is None:
            return
        try:
            self._backend.seek_relative(seconds)
            self._end_reported = False
        except BackendError as exc:
            self._fail(str(exc))
            return
        upper = self._duration if self._duration > 0 else float("inf")
        self._position = max(0.0, min(upper, self._position + seconds))
        self.manual_navigation_started.emit()
        self.position_changed.emit(self._position, self._duration)

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, int(volume)))
        if self._initialized:
            try:
                self._backend.set_volume(self._volume)
            except BackendError as exc:
                self._fail(str(exc))
                return
        self.volume_changed.emit(self._volume, self._muted)

    def adjust_volume(self, delta: int) -> None:
        self.set_volume(self._volume + delta)

    def set_mute(self, muted: bool) -> None:
        self._muted = bool(muted)
        if self._initialized:
            try:
                self._backend.set_mute(self._muted)
            except BackendError as exc:
                self._fail(str(exc))
                return
        self.volume_changed.emit(self._volume, self._muted)

    def toggle_mute(self) -> None:
        self.set_mute(not self._muted)

    def set_ab_loop(self, start: float | None, end: float | None) -> bool:
        if not self._initialized:
            return False
        try:
            self._backend.set_ab_loop(start, end)
        except BackendError as exc:
            self._fail(str(exc))
            return False
        return True

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.1, min(4.0, float(speed)))
        if self._initialized:
            try:
                self._backend.set_speed(self._speed)
            except BackendError as exc:
                self._fail(str(exc))
                return
        self.speed_changed.emit(self._speed)

    def adjust_speed(self, delta: float) -> None:
        self.set_speed(round(self._speed + delta, 2))

    def set_frame_inspection(self, enabled: bool) -> bool:
        if enabled and self._current_file is None:
            return False
        if enabled == self._frame_inspection:
            return True
        try:
            if enabled and not self._backend.is_paused():
                self._backend.pause()
        except BackendError as exc:
            self._fail(str(exc))
            return False

        self._frame_inspection = enabled
        if enabled:
            self.playback_changed.emit(False)
            self._set_state(PlaybackState.FRAME_INSPECTION)
        else:
            self._set_state(PlaybackState.PAUSED)
        return True

    def frame_step(self, count: int) -> bool:
        if self._current_file is None or count == 0:
            return False
        try:
            if not self._backend.is_paused():
                self._backend.pause()
            self._backend.frame_step(count)
        except BackendError as exc:
            self._fail(str(exc))
            return False

        self.manual_navigation_started.emit()
        self.playback_changed.emit(False)
        state = PlaybackState.FRAME_INSPECTION if self._frame_inspection else PlaybackState.PAUSED
        self._set_state(state)
        return True

    def refresh(self) -> None:
        if not self._initialized or self._current_file is None:
            return
        try:
            position = self._backend.position()
            duration = self._backend.duration()
            paused = self._backend.is_paused()
            frame_number = self._backend.estimated_frame_number()
            frame_rate = self._backend.frame_rate()
            ended = self._backend.has_ended()
        except BackendError as exc:
            self._fail(str(exc))
            return
        self._position = position
        self._duration = duration
        self.position_changed.emit(position, duration)
        if frame_number is None and frame_rate > 0:
            frame_number = max(0, round(position * frame_rate))
        self.frame_metrics_changed.emit(frame_number if frame_number is not None else -1, frame_rate)
        if ended:
            if not self._end_reported:
                self._end_reported = True
                self._frame_inspection = False
                self.playback_changed.emit(False)
                self._set_state(PlaybackState.ENDED)
                self.media_ended.emit(str(self._current_file))
            return
        if self._state not in {PlaybackState.STOPPED, PlaybackState.ERROR}:
            if self._frame_inspection:
                state = PlaybackState.FRAME_INSPECTION
            else:
                state = PlaybackState.PAUSED if paused else PlaybackState.PLAYING
            if state is not self._state:
                self._set_state(state)
                self.playback_changed.emit(not paused)

    def shutdown(self) -> None:
        self._timer.stop()
        self._backend.shutdown()
        self._initialized = False

    def _set_state(self, state: PlaybackState) -> None:
        if state is self._state:
            return
        self._state = state
        self.state_changed.emit(state)

    def _fail(self, message: str) -> None:
        logger.error(message)
        self._set_state(PlaybackState.ERROR)
        self.error_occurred.emit(message)
