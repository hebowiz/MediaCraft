from collections.abc import Callable
from pathlib import Path
from typing import Any

from mediacraft.media.avi_info import is_amv4
from mediacraft.player.mpv_backend import MpvBackend
from mediacraft.player.player_backend import PlayerBackend
from mediacraft.player.windows_media_backend import WindowsMediaBackend


class AdaptiveBackend(PlayerBackend):
    """Use libmpv normally and Windows' installed VfW codec for AMV4."""

    def __init__(self, windows_media_factory: Callable[[], Any]) -> None:
        self._mpv = MpvBackend()
        self._windows_media = WindowsMediaBackend(windows_media_factory)
        self._active: PlayerBackend = self._mpv
        self._window_id = 0
        self._volume = 100
        self._muted = False
        self._speed = 1.0

    def initialize(self, window_id: int) -> None:
        self._window_id = window_id
        self._mpv.initialize(window_id)

    def load(self, path: Path) -> None:
        next_backend: PlayerBackend
        if is_amv4(path):
            self._windows_media.initialize(self._window_id)
            next_backend = self._windows_media
        else:
            next_backend = self._mpv
        if self._active is not next_backend:
            self._active.clear_media()
        self._active = next_backend
        self._active.set_volume(self._volume)
        self._active.set_mute(self._muted)
        self._active.set_speed(self._speed)
        self._active.load(path)

    def play(self) -> None:
        self._active.play()

    def pause(self) -> None:
        self._active.pause()

    def stop(self) -> None:
        self._active.stop()

    def clear_media(self) -> None:
        self._active.clear_media()

    def seek_absolute(self, seconds: float) -> None:
        self._active.seek_absolute(seconds)

    def seek_relative(self, seconds: float) -> None:
        self._active.seek_relative(seconds)

    def set_speed(self, speed: float) -> None:
        self._speed = speed
        self._active.set_speed(speed)

    def set_volume(self, volume: int) -> None:
        self._volume = volume
        self._active.set_volume(volume)

    def set_mute(self, muted: bool) -> None:
        self._muted = muted
        self._active.set_mute(muted)

    def set_ab_loop(self, start: float | None, end: float | None) -> None:
        self._active.set_ab_loop(start, end)

    def save_screenshot(self, path: Path, include_subtitles: bool = False) -> None:
        self._active.save_screenshot(path, include_subtitles)

    def frame_step(self, count: int) -> None:
        self._active.frame_step(count)

    def position(self) -> float:
        return self._active.position()

    def duration(self) -> float:
        return self._active.duration()

    def is_paused(self) -> bool:
        return self._active.is_paused()

    def estimated_frame_number(self) -> int | None:
        return self._active.estimated_frame_number()

    def frame_rate(self) -> float:
        return self._active.frame_rate()

    def has_ended(self) -> bool:
        return self._active.has_ended()

    def shutdown(self) -> None:
        self._windows_media.shutdown()
        self._mpv.shutdown()
