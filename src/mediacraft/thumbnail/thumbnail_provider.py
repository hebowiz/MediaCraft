import math
from pathlib import Path
from threading import Event

import av
from av.error import FFmpegError
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtGui import QImage

from mediacraft.thumbnail.thumbnail_cache import ThumbnailCache


def frame_to_image(frame, width: int) -> QImage:
    if frame.width <= 0 or frame.height <= 0:
        return QImage()
    height = max(1, round(width * frame.height / frame.width))
    rgb_frame = frame.reformat(width=width, height=height, format="rgb24")
    plane = rgb_frame.planes[0]
    return QImage(
        bytes(plane),
        rgb_frame.width,
        rgb_frame.height,
        plane.line_size,
        QImage.Format.Format_RGB888,
    ).copy()


class ThumbnailTaskSignals(QObject):
    finished = Signal(str, int, int, float, object)
    cancelled = Signal()


class ThumbnailTask(QRunnable):
    def __init__(
        self,
        path: str,
        generation: int,
        cache_key: int,
        timestamp: float,
        width: int,
    ) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.path = path
        self.generation = generation
        self.cache_key = cache_key
        self.timestamp = timestamp
        self.width = width
        self.signals = ThumbnailTaskSignals()
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def _stop_if_cancelled(self) -> bool:
        if not self._cancelled.is_set():
            return False
        self.signals.cancelled.emit()
        return True

    def run(self) -> None:
        if self._stop_if_cancelled():
            return
        image = QImage()
        actual_timestamp = self.timestamp
        try:
            with av.open(self.path) as container:
                if self._stop_if_cancelled():
                    return
                stream = next(item for item in container.streams if item.type == "video")
                container.seek(
                    max(0, int(self.timestamp * av.time_base)),
                    backward=True,
                )
                selected = None
                for frame in container.decode(stream):
                    if self._stop_if_cancelled():
                        return
                    selected = frame
                    frame_time = frame.time
                    if frame_time is not None:
                        actual_timestamp = float(frame_time)
                        if actual_timestamp >= self.timestamp:
                            break
                if selected is not None and selected.width > 0 and selected.height > 0:
                    if self._stop_if_cancelled():
                        return
                    image = frame_to_image(selected, self.width)
        except (FFmpegError, OSError, StopIteration, ValueError):
            pass
        if self._stop_if_cancelled():
            return
        self.signals.finished.emit(
            self.path,
            self.generation,
            self.cache_key,
            actual_timestamp,
            image,
        )


class ThumbnailPreloadSignals(QObject):
    thumbnail_ready = Signal(str, int, float, object)
    finished = Signal()


class ThumbnailPreloadTask(QRunnable):
    INITIAL_ANCHORS = 40

    def __init__(
        self,
        path: str,
        generation: int,
        duration: float,
        interval: float,
        width: int,
    ) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.path = path
        self.generation = generation
        self.duration = duration
        self.interval = interval
        self.width = width
        self.signals = ThumbnailPreloadSignals()
        self._cancelled = Event()

    def cancel(self) -> None:
        self._cancelled.set()

    def run(self) -> None:
        try:
            with av.open(self.path) as container:
                stream = next(item for item in container.streams if item.type == "video")
                for timestamp in self._target_times():
                    if self._cancelled.is_set():
                        break
                    container.seek(
                        max(0, int(timestamp * av.time_base)),
                        backward=True,
                    )
                    # Coarse previews favor speed: use the first decodable
                    # frame at the keyframe reached by the backward seek.
                    selected = next(container.decode(stream), None)
                    actual_timestamp = timestamp
                    if self._cancelled.is_set():
                        break
                    if selected is not None:
                        if selected.time is not None:
                            actual_timestamp = float(selected.time)
                        image = frame_to_image(selected, self.width)
                        if not image.isNull():
                            self.signals.thumbnail_ready.emit(
                                self.path,
                                self.generation,
                                actual_timestamp,
                                image,
                            )
                    if self._cancelled.wait(0.01):
                        break
        except (FFmpegError, OSError, StopIteration, ValueError):
            pass
        self.signals.finished.emit()

    def _target_times(self) -> list[float]:
        detailed_count = max(1, math.ceil(self.duration / self.interval))
        detailed = [
            min(self.duration, index * self.interval)
            for index in range(detailed_count + 1)
        ]
        anchor_count = min(self.INITIAL_ANCHORS, detailed_count)
        anchor_indices = {
            round(index * detailed_count / anchor_count)
            for index in range(anchor_count + 1)
        }
        anchors = [detailed[index] for index in sorted(anchor_indices)]
        remaining = [
            timestamp
            for index, timestamp in enumerate(detailed)
            if index not in anchor_indices
        ]
        return anchors + remaining


class ThumbnailProvider(QObject):
    """Decode and cache thumbnails without blocking the UI thread."""

    thumbnail_ready = Signal(str, int, float, object)
    coarse_thumbnail_ready = Signal(str, float, object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        interval: float = 2.0,
        cache_size: int = 48,
        width: int = 240,
    ) -> None:
        super().__init__(parent)
        if interval <= 0:
            raise ValueError("interval must be positive")
        self._interval = interval
        self._width = width
        self._cache = ThumbnailCache(cache_size)
        self._coarse_cache = ThumbnailCache(240)
        self._thread_pool = QThreadPool(self)
        # Keep the newest hover request moving even if an older seek/decode is
        # still finishing. Two workers balance responsiveness and disk load.
        self._thread_pool.setMaxThreadCount(2)
        self._tasks: set[ThumbnailTask] = set()
        self._pending_keys: set[int] = set()
        self._path: str | None = None
        self._generation = 0
        self._preload_task: ThumbnailPreloadTask | None = None
        self._preload_started = False
        self._coarse_max_distance_ms = 0

    @property
    def media_path(self) -> str | None:
        return self._path

    def set_media(self, path: str | None) -> None:
        resolved = str(Path(path).resolve()) if path else None
        if resolved == self._path:
            return
        self._generation += 1
        self._path = resolved
        self._cache.clear()
        self._coarse_cache.clear()
        self._pending_keys.clear()
        self._preload_started = False
        self._coarse_max_distance_ms = 0
        if self._preload_task is not None:
            self._preload_task.cancel()
            self._thread_pool.tryTake(self._preload_task)
            self._preload_task = None
        for task in tuple(self._tasks):
            task.cancel()
            if self._thread_pool.tryTake(task):
                self._tasks.discard(task)

    def cache_key(self, timestamp: float) -> int:
        return max(0, round(max(0.0, timestamp) / self._interval))

    def request(self, timestamp: float) -> tuple[int, QImage | None]:
        key = self.cache_key(timestamp)
        cached = self._cache.get(key)
        if cached is not None or self._path is None or key in self._pending_keys:
            return key, cached

        for pending in tuple(self._tasks):
            if pending.cache_key == key:
                continue
            pending.cancel()
            if self._thread_pool.tryTake(pending):
                self._tasks.discard(pending)
                self._pending_keys.discard(pending.cache_key)

        task = ThumbnailTask(
            self._path,
            self._generation,
            key,
            key * self._interval,
            self._width,
        )
        self._tasks.add(task)
        self._pending_keys.add(key)
        task.signals.finished.connect(
            lambda path, generation, result_key, actual, image, current=task: self._task_finished(
                current,
                path,
                generation,
                result_key,
                actual,
                image,
            )
        )
        task.signals.cancelled.connect(
            lambda current=task, generation=self._generation, result_key=key: self._task_cancelled(
                current,
                generation,
                result_key,
            )
        )
        self._thread_pool.start(task)
        return key, None

    def cached(self, timestamp: float) -> tuple[int, QImage | None]:
        key = self.cache_key(timestamp)
        exact = self._cache.get(key)
        if exact is not None:
            return key, exact
        coarse = self._coarse_cache.get_nearest(
            round(max(0.0, timestamp) * 1000),
            self._coarse_max_distance_ms,
        )
        return key, coarse[1] if coarse is not None else None

    def start_preload(self, duration: float) -> None:
        if self._path is None or duration <= 0 or self._preload_started:
            return
        self._preload_started = True
        interval = max(5.0, duration / 239)
        initial_spacing = duration / ThumbnailPreloadTask.INITIAL_ANCHORS
        self._coarse_max_distance_ms = round(max(interval, initial_spacing / 2) * 1000)
        task = ThumbnailPreloadTask(
            self._path,
            self._generation,
            duration,
            interval,
            160,
        )
        self._preload_task = task
        task.signals.thumbnail_ready.connect(self._preload_thumbnail_ready)
        task.signals.finished.connect(
            lambda current=task: self._preload_finished(current)
        )
        self._thread_pool.start(task, -1)

    def cancel_preload(self, *, clear_cache: bool = True) -> None:
        self._preload_started = False
        if self._preload_task is not None:
            self._preload_task.cancel()
            self._thread_pool.tryTake(self._preload_task)
            self._preload_task = None
        if clear_cache:
            self._coarse_cache.clear()

    def shutdown(self) -> None:
        self._generation += 1
        if self._preload_task is not None:
            self._preload_task.cancel()
        for task in tuple(self._tasks):
            task.cancel()
        self._thread_pool.clear()
        self._thread_pool.waitForDone(100)
        self._tasks.clear()
        self._pending_keys.clear()
        self._preload_task = None

    def _task_finished(
        self,
        task: ThumbnailTask,
        path: str,
        generation: int,
        key: int,
        actual_timestamp: float,
        image: QImage,
    ) -> None:
        self._tasks.discard(task)
        if generation != self._generation or path != self._path:
            return
        self._pending_keys.discard(key)
        if image.isNull():
            return
        self._cache.put(key, image)
        self.thumbnail_ready.emit(path, key, actual_timestamp, image)

    def _task_cancelled(
        self,
        task: ThumbnailTask,
        generation: int,
        key: int,
    ) -> None:
        self._tasks.discard(task)
        if generation == self._generation:
            self._pending_keys.discard(key)

    def _preload_thumbnail_ready(
        self,
        path: str,
        generation: int,
        timestamp: float,
        image: QImage,
    ) -> None:
        if generation != self._generation or path != self._path:
            return
        self._coarse_cache.put(round(timestamp * 1000), image)
        self.coarse_thumbnail_ready.emit(path, timestamp, image)

    def _preload_finished(self, task: ThumbnailPreloadTask) -> None:
        if self._preload_task is task:
            self._preload_task = None
