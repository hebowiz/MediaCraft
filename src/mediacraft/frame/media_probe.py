import statistics

import av
from av.error import FFmpegError
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from mediacraft.media.avi_info import inspect_avi
from mediacraft.media.codec_names import display_codec_name


def detect_variable_frame_rate(timestamps: list[float]) -> bool | None:
    intervals = [
        current - previous
        for previous, current in zip(timestamps, timestamps[1:])
        if current > previous
    ]
    if len(intervals) < 10:
        return None

    median_interval = statistics.median(intervals)
    if median_interval <= 0:
        return None
    tolerance = median_interval * 0.02
    return any(abs(interval - median_interval) > tolerance for interval in intervals)


class ProbeSignals(QObject):
    finished = Signal(str, float, object)
    codecs_finished = Signal(str, str, str)


class ProbeTask(QRunnable):
    SAMPLE_FRAMES = 180

    def __init__(self, path: str) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.path = path
        self.signals = ProbeSignals()

    def run(self) -> None:
        fps = 0.0
        variable: bool | None = None
        video_codec = ""
        audio_codec = ""
        codecs_emitted = False
        try:
            with av.open(self.path) as container:
                stream = next(stream for stream in container.streams if stream.type == "video")
                video_codec = display_codec_name(
                    getattr(getattr(stream, "codec_context", None), "name", "")
                )
                audio_stream = next(
                    (item for item in container.streams if item.type == "audio"), None
                )
                audio_codec = display_codec_name(
                    getattr(getattr(audio_stream, "codec_context", None), "name", "")
                )
                self.signals.codecs_finished.emit(
                    self.path, video_codec, audio_codec
                )
                codecs_emitted = True
                average_rate = stream.average_rate or stream.guessed_rate
                fps = float(average_rate) if average_rate is not None else 0.0

                timestamps: list[float] = []
                for frame in container.decode(stream):
                    if frame.pts is not None and frame.time_base is not None:
                        timestamps.append(float(frame.pts * frame.time_base))
                    if len(timestamps) >= self.SAMPLE_FRAMES:
                        break

                variable = detect_variable_frame_rate(timestamps)
                if fps <= 0 and len(timestamps) >= 2:
                    intervals = [
                        current - previous
                        for previous, current in zip(timestamps, timestamps[1:])
                        if current > previous
                    ]
                    if intervals:
                        median_interval = statistics.median(intervals)
                        if median_interval > 0:
                            fps = 1.0 / median_interval
        except (FFmpegError, OSError, StopIteration, ValueError):
            pass
        if not codecs_emitted:
            self.signals.codecs_finished.emit(self.path, video_codec, audio_codec)
        self.signals.finished.emit(self.path, fps, variable)


class MediaProbe(QObject):
    analysis_ready = Signal(str, float, object)
    codecs_ready = Signal(str, str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._tasks: set[ProbeTask] = set()

    def probe(self, path: str) -> None:
        avi_info = inspect_avi(path)
        if avi_info is not None and avi_info.is_amv4:
            QTimer.singleShot(
                0,
                lambda: self.analysis_ready.emit(path, avi_info.frame_rate, False),
            )
            QTimer.singleShot(
                0,
                lambda: self.codecs_ready.emit(path, "AMV4", ""),
            )
            return
        for pending in tuple(self._tasks):
            if self._thread_pool.tryTake(pending):
                self._tasks.discard(pending)
        task = ProbeTask(path)
        self._tasks.add(task)
        task.signals.finished.connect(
            lambda result_path, fps, variable, current=task: self._task_finished(
                current, result_path, fps, variable
            )
        )
        task.signals.codecs_finished.connect(self.codecs_ready.emit)
        self._thread_pool.start(task)

    def shutdown(self) -> None:
        self._thread_pool.clear()
        self._thread_pool.waitForDone(1000)
        self._tasks.clear()

    def _task_finished(
        self,
        task: ProbeTask,
        path: str,
        fps: float,
        variable: bool | None,
    ) -> None:
        self._tasks.discard(task)
        self.analysis_ready.emit(path, fps, variable)
