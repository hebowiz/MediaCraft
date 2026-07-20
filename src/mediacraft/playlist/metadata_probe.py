import av
from av.error import FFmpegError
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from mediacraft.media.avi_info import inspect_avi


class DurationProbeSignals(QObject):
    finished = Signal(str, float)


class DurationProbeTask(QRunnable):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.path = path
        self.signals = DurationProbeSignals()

    def run(self) -> None:
        duration = 0.0
        try:
            with av.open(self.path) as container:
                video_stream = next(
                    (stream for stream in container.streams if stream.type == "video"),
                    None,
                )
                if (
                    video_stream is not None
                    and video_stream.duration is not None
                    and video_stream.time_base is not None
                ):
                    duration = float(video_stream.duration * video_stream.time_base)
                elif container.duration is not None:
                    duration = float(container.duration / av.time_base)
        except (FFmpegError, OSError, ValueError):
            pass
        self.signals.finished.emit(self.path, max(0.0, duration))


class PlaylistMetadataProbe(QObject):
    duration_ready = Signal(str, float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(2)
        self._tasks: set[DurationProbeTask] = set()
        self._requested_paths: set[str] = set()
        self._duration_cache: dict[str, float] = {}

    def probe(self, paths: list[str]) -> None:
        for path in paths:
            if path in self._requested_paths:
                if path in self._duration_cache:
                    self.duration_ready.emit(path, self._duration_cache[path])
                continue
            self._requested_paths.add(path)
            avi_info = inspect_avi(path)
            if avi_info is not None and avi_info.is_amv4:
                self._duration_cache[path] = avi_info.duration
                self.duration_ready.emit(path, avi_info.duration)
                continue
            task = DurationProbeTask(path)
            self._tasks.add(task)
            task.signals.finished.connect(
                lambda result_path, duration, current=task: self._task_finished(
                    current, result_path, duration
                )
            )
            self._thread_pool.start(task)

    def shutdown(self) -> None:
        self._thread_pool.clear()
        self._thread_pool.waitForDone(1000)
        self._tasks.clear()

    def _task_finished(self, task: DurationProbeTask, path: str, duration: float) -> None:
        self._tasks.discard(task)
        self._duration_cache[path] = duration
        self.duration_ready.emit(path, duration)
