from abc import ABC, abstractmethod
from pathlib import Path


class BackendError(RuntimeError):
    """Raised when the playback backend cannot complete an operation."""


class BackendUnavailableError(BackendError):
    """Raised when libmpv or its Python binding cannot be loaded."""


class PlayerBackend(ABC):
    @abstractmethod
    def initialize(self, window_id: int) -> None:
        """Initialize the backend and bind video output to a native window."""

    @abstractmethod
    def load(self, path: Path) -> None:
        pass

    @abstractmethod
    def play(self) -> None:
        pass

    @abstractmethod
    def pause(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def seek_absolute(self, seconds: float) -> None:
        pass

    @abstractmethod
    def seek_relative(self, seconds: float) -> None:
        pass

    @abstractmethod
    def set_speed(self, speed: float) -> None:
        pass

    @abstractmethod
    def set_volume(self, volume: int) -> None:
        pass

    @abstractmethod
    def set_mute(self, muted: bool) -> None:
        pass

    @abstractmethod
    def frame_step(self, count: int) -> None:
        pass

    @abstractmethod
    def position(self) -> float:
        pass

    @abstractmethod
    def duration(self) -> float:
        pass

    @abstractmethod
    def is_paused(self) -> bool:
        pass

    @abstractmethod
    def estimated_frame_number(self) -> int | None:
        pass

    @abstractmethod
    def frame_rate(self) -> float:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
