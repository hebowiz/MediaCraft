from dataclasses import dataclass
from pathlib import Path
from threading import Event

import av
from av.error import FFmpegError
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QImage

from mediacraft.thumbnail.thumbnail_provider import frame_to_image


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    title: str = ""
    artist: str = ""
    album: str = ""
    bitrate_kbps: int | None = None
    artwork: QImage | None = None


def _contains_japanese(text: str) -> bool:
    return any(
        "\u3040" <= character <= "\u30ff"
        or "\u3400" <= character <= "\u4dbf"
        or "\u4e00" <= character <= "\u9fff"
        or "\uf900" <= character <= "\ufaff"
        or "\uff66" <= character <= "\uff9f"
        for character in text
    )


def repair_legacy_japanese_tag(text: str) -> str:
    """Repair CP932 bytes incorrectly labelled as Latin-1 in legacy ID3 tags."""
    if not text or _contains_japanese(text):
        return text
    has_c1_control = any("\u0080" <= character <= "\u009f" for character in text)
    cp1252_mojibake = any(
        character in "‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ" for character in text
    )
    if not has_c1_control and not cp1252_mojibake:
        return text

    for encoding in ("latin-1", "cp1252"):
        try:
            raw = text.encode(encoding)
            candidate = raw.decode("cp932")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if _contains_japanese(candidate):
            return candidate
    return text


def _normalized_metadata(*sources: object) -> dict[str, str]:
    result: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            text = repair_legacy_japanese_tag(str(value).strip())
            if not text:
                continue
            normalized_key = (
                str(key).casefold().replace(" ", "").replace("_", "").replace("/", "")
            )
            result.setdefault(normalized_key, text)
    return result


def _first_value(metadata: dict[str, str], *keys: str) -> str:
    return next((metadata[key] for key in keys if metadata.get(key)), "")


def _positive_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number > 0 else None


def _duration_seconds(container: object, audio_stream: object | None) -> float:
    duration = getattr(container, "duration", None)
    if duration is not None:
        try:
            seconds = float(duration) / av.time_base
            if seconds > 0:
                return seconds
        except (TypeError, ValueError, OverflowError):
            pass
    if audio_stream is not None:
        stream_duration = getattr(audio_stream, "duration", None)
        time_base = getattr(audio_stream, "time_base", None)
        if stream_duration is not None and time_base is not None:
            try:
                seconds = float(stream_duration * time_base)
                if seconds > 0:
                    return seconds
            except (TypeError, ValueError, OverflowError):
                pass
    return 0.0


def read_audio_metadata(path: str | Path) -> AudioMetadata:
    media_path = Path(path)
    with av.open(str(media_path)) as container:
        audio_stream = next(
            (stream for stream in container.streams if stream.type == "audio"),
            None,
        )
        stream_metadata = getattr(audio_stream, "metadata", {}) if audio_stream else {}
        metadata = _normalized_metadata(container.metadata, stream_metadata)

        bit_rate = _positive_int(getattr(audio_stream, "bit_rate", None))
        if bit_rate is None:
            bit_rate = _positive_int(getattr(container, "bit_rate", None))
        if bit_rate is None:
            duration = _duration_seconds(container, audio_stream)
            if duration > 0:
                try:
                    bit_rate = round(media_path.stat().st_size * 8 / duration)
                except OSError:
                    pass

        artwork: QImage | None = None
        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"),
            None,
        )
        if video_stream is not None:
            frame = next(container.decode(video_stream), None)
            if frame is not None:
                image = frame_to_image(frame, 640)
                if not image.isNull():
                    artwork = image

        return AudioMetadata(
            title=_first_value(metadata, "title", "wmtitle"),
            artist=_first_value(
                metadata,
                "artist",
                "wmartist",
                "author",
                "performer",
                "albumartist",
                "wmalbumartist",
            ),
            album=_first_value(metadata, "album", "albumtitle", "wmalbumtitle"),
            bitrate_kbps=round(bit_rate / 1000) if bit_rate is not None else None,
            artwork=artwork,
        )


class AudioMetadataSignals(QObject):
    finished = Signal(str, object)


class AudioMetadataTask(QRunnable):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.path = path
        self.signals = AudioMetadataSignals()
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        metadata = AudioMetadata()
        try:
            metadata = read_audio_metadata(self.path)
        except (FFmpegError, OSError, StopIteration, ValueError):
            pass
        if not self._cancelled.is_set():
            self.signals.finished.emit(self.path, metadata)


class AudioMetadataProbe(QObject):
    metadata_ready = Signal(str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._tasks: set[AudioMetadataTask] = set()

    def probe(self, path: str) -> None:
        self.cancel()
        task = AudioMetadataTask(path)
        self._tasks.add(task)
        task.signals.finished.connect(
            lambda result_path, metadata, current=task: self._task_finished(
                current, result_path, metadata
            )
        )
        self._thread_pool.start(task)

    def cancel(self) -> None:
        for task in tuple(self._tasks):
            task.cancel()
            if self._thread_pool.tryTake(task):
                self._tasks.discard(task)

    def shutdown(self) -> None:
        self.cancel()
        self._thread_pool.waitForDone(1000)
        self._tasks.clear()

    def _task_finished(
        self,
        task: AudioMetadataTask,
        path: str,
        metadata: AudioMetadata,
    ) -> None:
        self._tasks.discard(task)
        self.metadata_ready.emit(path, metadata)
