from PySide6.QtCore import QObject, QTimer, Signal

from mediacraft.player.playback_state import PlaybackState
from mediacraft.player.player_controller import PlayerController


class FrameController(QObject):
    inspection_mode_changed = Signal(bool)
    frame_display_changed = Signal(int, bool)

    def __init__(self, player: PlayerController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = player
        self._inspection_mode = False
        self._variable_frame_rate: bool | None = None
        self._probe_fps = 0.0
        self._frame_number = -1
        self._pending_steps = 0

        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.setInterval(45)
        self._throttle_timer.timeout.connect(self._flush_pending_steps)

        player.frame_metrics_changed.connect(self._update_frame_metrics)
        player.file_changed.connect(self._reset_media)
        player.playback_changed.connect(self._playback_changed)
        player.state_changed.connect(self._state_changed)

    @property
    def inspection_mode(self) -> bool:
        return self._inspection_mode

    def toggle_inspection_mode(self) -> None:
        self.set_inspection_mode(not self._inspection_mode)

    def set_inspection_mode(self, enabled: bool) -> None:
        if enabled == self._inspection_mode:
            return
        if not self._player.set_frame_inspection(enabled):
            self.inspection_mode_changed.emit(self._inspection_mode)
            return
        self._inspection_mode = enabled
        if not enabled:
            self._pending_steps = 0
            self._throttle_timer.stop()
        self.inspection_mode_changed.emit(enabled)
        self._emit_frame_display()

    def request_step(self, count: int) -> None:
        if count == 0:
            return
        if not self._throttle_timer.isActive() and self._pending_steps == 0:
            self._player.frame_step(count)
            self._throttle_timer.start()
            return

        self._pending_steps = max(-500, min(500, self._pending_steps + count))

    def set_frame_rate_analysis(self, fps: float, variable: bool | None) -> None:
        self._probe_fps = max(0.0, fps)
        self._variable_frame_rate = variable
        self._emit_frame_display()

    def _flush_pending_steps(self) -> None:
        if self._pending_steps == 0:
            return
        steps = self._pending_steps
        self._pending_steps = 0
        self._player.frame_step(steps)
        self._throttle_timer.start()

    def _update_frame_metrics(self, frame_number: int, frame_rate: float) -> None:
        self._frame_number = frame_number
        if self._probe_fps <= 0 and frame_rate > 0:
            self._probe_fps = frame_rate
        self._emit_frame_display()

    def _reset_media(self, _path: str) -> None:
        self._frame_number = 0
        self._probe_fps = 0.0
        self._variable_frame_rate = None
        if self._inspection_mode:
            self._inspection_mode = False
            self.inspection_mode_changed.emit(False)
        self._emit_frame_display()

    def _playback_changed(self, playing: bool) -> None:
        if playing and self._inspection_mode:
            self._leave_local_mode()

    def _state_changed(self, state: PlaybackState) -> None:
        if state in {PlaybackState.STOPPED, PlaybackState.ERROR, PlaybackState.NO_MEDIA}:
            self._leave_local_mode()
        if state is PlaybackState.STOPPED:
            self._frame_number = 0
            self._emit_frame_display()

    def _leave_local_mode(self) -> None:
        if not self._inspection_mode:
            return
        self._inspection_mode = False
        self._pending_steps = 0
        self._throttle_timer.stop()
        self.inspection_mode_changed.emit(False)

    def _emit_frame_display(self) -> None:
        approximate = self._variable_frame_rate is not False
        self.frame_display_changed.emit(self._frame_number, approximate)
