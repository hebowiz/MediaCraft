from fractions import Fraction

import av
from PySide6.QtGui import QImage

from mediacraft.thumbnail.thumbnail_provider import (
    ThumbnailPreloadTask,
    ThumbnailProvider,
    ThumbnailTask,
)


def create_test_video(path) -> None:
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("mpeg4", rate=10)
        stream.width = 64
        stream.height = 36
        stream.pix_fmt = "yuv420p"
        for index in range(20):
            frame = av.VideoFrame(64, 36, "rgb24")
            frame.pts = index
            frame.time_base = Fraction(1, 10)
            frame.planes[0].update(bytes([index * 8]) * frame.planes[0].buffer_size)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def test_provider_generates_and_reuses_quantized_thumbnail(qtbot, tmp_path) -> None:
    video = tmp_path / "preview.mp4"
    create_test_video(video)
    provider = ThumbnailProvider(interval=1.0, width=80)
    provider.set_media(str(video))

    with qtbot.waitSignal(provider.thumbnail_ready, timeout=5000) as result:
        key, cached = provider.request(0.8)
    assert key == 1
    assert cached is None
    assert result.args[1] == 1
    assert not result.args[3].isNull()
    assert result.args[3].width() == 80
    same_key, cached = provider.request(1.2)
    assert same_key == key
    assert cached is not None
    assert not cached.isNull()
    provider.shutdown()


def test_switching_media_clears_cache(tmp_path) -> None:
    provider = ThumbnailProvider(interval=2.0)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    provider.set_media(str(first))
    provider._cache.put(0, QImage(2, 2, QImage.Format.Format_RGB32))

    provider.set_media(str(second))

    assert len(provider._cache) == 0
    provider.shutdown()


def test_cancelled_task_does_not_open_media_or_emit(monkeypatch) -> None:
    opened = False

    def track_open(_path):
        nonlocal opened
        opened = True

    monkeypatch.setattr(av, "open", track_open)
    task = ThumbnailTask("unused.mp4", 1, 0, 0.0, 80)
    emitted = False

    def mark_emitted(*_args) -> None:
        nonlocal emitted
        emitted = True

    task.signals.finished.connect(mark_emitted)
    task.cancel()
    task.run()

    assert not opened
    assert not emitted


def test_provider_preloads_coarse_thumbnail_in_background(qtbot, tmp_path) -> None:
    video = tmp_path / "preload.mp4"
    create_test_video(video)
    provider = ThumbnailProvider(interval=1.0)
    provider.set_media(str(video))

    with qtbot.waitSignal(provider.coarse_thumbnail_ready, timeout=5000) as result:
        provider.start_preload(2.0)

    assert result.args[0] == str(video.resolve())
    assert not result.args[2].isNull()
    _key, cached = provider.cached(result.args[1])
    assert cached is not None
    assert cached.width() == 160
    provider.shutdown()


def test_preload_targets_cover_whole_video_without_exceeding_cache() -> None:
    duration = 3600.0
    task = ThumbnailPreloadTask(
        "unused.mp4",
        1,
        duration,
        duration / 239,
        160,
    )

    targets = task._target_times()

    assert len(targets) == 240
    assert targets[0] == 0.0
    assert duration in targets[: ThumbnailPreloadTask.INITIAL_ANCHORS + 1]
    assert len(set(targets)) == len(targets)
