import av
import pytest

from mediacraft.playlist.metadata_probe import PlaylistMetadataProbe


def test_duration_probe_reports_unreadable_media(qtbot, tmp_path) -> None:
    media_file = tmp_path / "empty.mp4"
    media_file.touch()
    probe = PlaylistMetadataProbe()

    with qtbot.waitSignal(probe.duration_ready) as blocker:
        probe.probe([str(media_file)])

    assert blocker.args == [str(media_file), 0.0]
    probe.shutdown()


def test_duration_probe_reads_video_duration(qtbot, tmp_path) -> None:
    media_file = tmp_path / "sample.mp4"
    with av.open(str(media_file), "w") as container:
        stream = container.add_stream("mpeg4", rate=10)
        stream.width = 16
        stream.height = 16
        stream.pix_fmt = "yuv420p"
        for index in range(10):
            frame = av.VideoFrame(16, 16, "yuv420p")
            frame.pts = index
            for plane in frame.planes:
                plane.update(bytes(plane.buffer_size))
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)

    probe = PlaylistMetadataProbe()
    with qtbot.waitSignal(probe.duration_ready) as blocker:
        probe.probe([str(media_file)])

    assert blocker.args[1] == pytest.approx(1.0, abs=0.1)
    probe.shutdown()
