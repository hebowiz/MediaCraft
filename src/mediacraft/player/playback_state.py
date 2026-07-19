from enum import Enum, auto


class PlaybackState(Enum):
    NO_MEDIA = auto()
    LOADING = auto()
    READY = auto()
    PLAYING = auto()
    PAUSED = auto()
    FRAME_INSPECTION = auto()
    SEEKING = auto()
    STOPPED = auto()
    ENDED = auto()
    ERROR = auto()
