from dataclasses import dataclass
from pathlib import Path
import struct


@dataclass(frozen=True)
class AviInfo:
    video_fourcc: str | None = None
    frame_rate: float = 0.0
    duration: float = 0.0
    total_frames: int = 0

    @property
    def is_amv4(self) -> bool:
        return self.video_fourcc == "AMV4"


def inspect_avi(path: str | Path) -> AviInfo | None:
    """Read the small RIFF header without invoking a media decoder."""
    media_path = Path(path)
    if media_path.suffix.lower() != ".avi":
        return None
    try:
        with media_path.open("rb") as source:
            data = source.read(4 * 1024 * 1024)
    except OSError:
        return None
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"AVI ":
        return None

    microseconds_per_frame = 0
    total_frames = 0
    video_fourcc: str | None = None

    def walk(start: int, end: int) -> None:
        nonlocal microseconds_per_frame, total_frames, video_fourcc
        offset = start
        while offset + 8 <= end:
            chunk_id = data[offset : offset + 4]
            size = struct.unpack_from("<I", data, offset + 4)[0]
            payload = offset + 8
            chunk_end = min(payload + size, end)
            if chunk_id == b"LIST" and payload + 4 <= chunk_end:
                walk(payload + 4, chunk_end)
            elif chunk_id == b"avih" and payload + 20 <= chunk_end:
                microseconds_per_frame = struct.unpack_from("<I", data, payload)[0]
                total_frames = struct.unpack_from("<I", data, payload + 16)[0]
            elif chunk_id == b"strh" and payload + 8 <= chunk_end:
                if data[payload : payload + 4] == b"vids" and video_fourcc is None:
                    video_fourcc = data[payload + 4 : payload + 8].decode(
                        "ascii", errors="replace"
                    ).upper()
            offset = payload + size + (size & 1)

    walk(12, len(data))
    frame_rate = (
        1_000_000.0 / microseconds_per_frame if microseconds_per_frame > 0 else 0.0
    )
    duration = (
        total_frames * microseconds_per_frame / 1_000_000.0
        if microseconds_per_frame > 0 and total_frames > 0
        else 0.0
    )
    return AviInfo(video_fourcc, frame_rate, duration, total_frames)


def is_amv4(path: str | Path) -> bool:
    info = inspect_avi(path)
    return info is not None and info.is_amv4
