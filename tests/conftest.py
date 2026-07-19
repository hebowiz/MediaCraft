from pathlib import Path

from mediacraft.player.player_backend import PlayerBackend


class FakeBackend(PlayerBackend):
    def __init__(self) -> None:
        self.initialized = False
        self.loaded_path: Path | None = None
        self.paused = True
        self.current_position = 0.0
        self.media_duration = 120.0
        self.volume = 100
        self.muted = False
        self.speed = 1.0
        self.shutdown_called = False

    def initialize(self, window_id: int) -> None:
        self.initialized = window_id >= 0

    def load(self, path: Path) -> None:
        self.loaded_path = path
        self.paused = False

    def play(self) -> None:
        self.paused = False

    def pause(self) -> None:
        self.paused = True

    def stop(self) -> None:
        self.paused = True
        self.current_position = 0.0

    def seek_absolute(self, seconds: float) -> None:
        self.current_position = seconds

    def seek_relative(self, seconds: float) -> None:
        self.current_position += seconds

    def set_speed(self, speed: float) -> None:
        self.speed = speed

    def set_volume(self, volume: int) -> None:
        self.volume = volume

    def set_mute(self, muted: bool) -> None:
        self.muted = muted

    def position(self) -> float:
        return self.current_position

    def duration(self) -> float:
        return self.media_duration

    def is_paused(self) -> bool:
        return self.paused

    def shutdown(self) -> None:
        self.shutdown_called = True
