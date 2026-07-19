from PySide6.QtCore import QObject, Signal

from mediacraft.player.playback_state import PlaybackState
from mediacraft.player.player_controller import PlayerController


class ABRepeatController(QObject):
    state_changed = Signal(float, float, bool)
    message = Signal(str)

    def __init__(self, player: PlayerController, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = player
        self._position = 0.0
        self._a: float | None = None
        self._b: float | None = None
        self._enabled = False
        self._manual_navigation_pending = False

        player.manual_navigation_started.connect(self._manual_navigation_started)
        player.position_changed.connect(self._position_changed)
        player.file_changed.connect(self._file_changed)
        player.state_changed.connect(self._player_state_changed)

    @property
    def point_a(self) -> float | None:
        return self._a

    @property
    def point_b(self) -> float | None:
        return self._b

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_point_a(self) -> bool:
        if not self._has_media():
            return False
        if self._b is not None and self._position >= self._b:
            self.message.emit("A点はB点より前に設定してください。")
            return False
        self._a = self._position
        self._update_active_loop()
        self._emit_state()
        return True

    def set_point_b(self) -> bool:
        if not self._has_media():
            return False
        if self._a is not None and self._position <= self._a:
            self.message.emit("B点はA点より後に設定してください。")
            return False
        self._b = self._position
        self._update_active_loop()
        self._emit_state()
        return True

    def set_enabled(self, enabled: bool) -> bool:
        if enabled:
            if self._a is None or self._b is None:
                self.message.emit("A点とB点を設定してください。")
                self._emit_state()
                return False
            if self._a >= self._b:
                self.message.emit("A点はB点より前に設定してください。")
                self._emit_state()
                return False
        if enabled == self._enabled:
            return True
        applied = (
            self._player.set_ab_loop(self._a, self._b)
            if enabled
            else self._player.set_ab_loop(None, None)
        )
        if not applied:
            return False
        self._enabled = enabled
        if enabled and self._a is not None and self._b is not None:
            if self._position < self._a or self._position >= self._b:
                self._player.seek_absolute(self._a, user_initiated=False)
                self._position = self._a
        self._emit_state()
        return True

    def toggle(self) -> None:
        self.set_enabled(not self._enabled)

    def clear_point_a(self) -> None:
        self._a = None
        self._disable_backend_loop()
        self._emit_state()

    def clear_point_b(self) -> None:
        self._b = None
        self._disable_backend_loop()
        self._emit_state()

    def clear(self) -> None:
        self._a = None
        self._b = None
        self._disable_backend_loop()
        self._emit_state()

    def seek_to_a(self) -> None:
        if self._a is not None:
            self._player.seek_absolute(self._a)

    def seek_to_b(self) -> None:
        if self._b is not None:
            self._player.seek_absolute(self._b)

    def _position_changed(self, position: float, _duration: float) -> None:
        self._position = position
        manually_navigated = self._manual_navigation_pending
        self._manual_navigation_pending = False
        if (
            manually_navigated
            and self._enabled
            and self._a is not None
            and self._b is not None
            and (position < self._a or position >= self._b)
            and self._player.set_ab_loop(None, None)
        ):
            self._enabled = False
            self._emit_state()
            self.message.emit("区間外へ移動したためA-Bリピートを解除しました。")

    def _manual_navigation_started(self) -> None:
        self._manual_navigation_pending = True

    def _file_changed(self, _path: str) -> None:
        self._position = 0.0
        self._a = None
        self._b = None
        self._enabled = False
        self._manual_navigation_pending = False
        self._player.set_ab_loop(None, None)
        self._emit_state()

    def _player_state_changed(self, state: PlaybackState) -> None:
        if state is PlaybackState.NO_MEDIA:
            self._position = 0.0
            self._a = None
            self._b = None
            self._enabled = False
            self._manual_navigation_pending = False
            self._emit_state()

    def _update_active_loop(self) -> None:
        if self._enabled:
            self._player.set_ab_loop(self._a, self._b)

    def _disable_backend_loop(self) -> None:
        if self._enabled:
            self._player.set_ab_loop(None, None)
        self._enabled = False

    def _has_media(self) -> bool:
        if self._player.current_file is not None:
            return True
        self.message.emit("動画を読み込んでください。")
        return False

    def _emit_state(self) -> None:
        self.state_changed.emit(
            self._a if self._a is not None else -1.0,
            self._b if self._b is not None else -1.0,
            self._enabled,
        )
