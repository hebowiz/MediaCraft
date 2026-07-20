from mediacraft.player.playback_state import PlaybackState
from mediacraft.player.player_controller import PlayerController


def test_load_play_pause_stop_and_seek(qtbot, tmp_path) -> None:
    from conftest import FakeBackend

    backend = FakeBackend()
    controller = PlayerController(backend)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()

    assert controller.initialize(123)
    assert controller.load_file(media_file)
    assert backend.loaded_path == media_file.resolve()
    assert controller.state is PlaybackState.PLAYING

    controller.toggle_play_pause()
    assert backend.paused
    assert controller.state is PlaybackState.PAUSED

    controller.seek_absolute(42.5)
    controller.seek_relative(5)
    assert backend.current_position == 47.5

    controller.stop()
    assert backend.current_position == 0
    assert controller.state is PlaybackState.STOPPED

    controller.shutdown()
    assert backend.shutdown_called


def test_volume_speed_and_mute_are_clamped(qtbot) -> None:
    from conftest import FakeBackend

    backend = FakeBackend()
    controller = PlayerController(backend)
    controller.set_volume(150)
    controller.set_speed(10)
    controller.set_mute(True)
    controller.initialize(123)

    assert backend.volume == 100
    assert backend.speed == 4.0
    assert backend.muted is True


def test_missing_file_emits_error(qtbot, tmp_path) -> None:
    from conftest import FakeBackend

    controller = PlayerController(FakeBackend())
    with qtbot.waitSignal(controller.error_occurred) as blocker:
        result = controller.load_file(tmp_path / "missing.mp4")

    assert result is False
    assert controller.state is PlaybackState.ERROR
    assert "ファイルが見つかりません" in blocker.args[0]


def test_frame_step_pauses_playback_and_moves_requested_frames(qtbot, tmp_path) -> None:
    from conftest import FakeBackend

    backend = FakeBackend()
    controller = PlayerController(backend)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    controller.initialize(123)
    controller.load_file(media_file)

    assert controller.frame_step(1)
    assert backend.paused
    assert backend.frame_steps == [1]
    assert controller.state is PlaybackState.PAUSED

    assert controller.set_frame_inspection(True)
    assert controller.frame_step(-10)
    assert backend.frame_steps == [1, -10]
    assert controller.state is PlaybackState.FRAME_INSPECTION


def test_media_end_is_reported_only_once(qtbot, tmp_path) -> None:
    from conftest import FakeBackend

    backend = FakeBackend()
    controller = PlayerController(backend)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    controller.initialize(123)
    controller.load_file(media_file)
    ended: list[str] = []
    controller.media_ended.connect(ended.append)

    backend.ended = True
    controller.refresh()
    controller.refresh()

    assert ended == [str(media_file.resolve())]
    assert controller.state is PlaybackState.ENDED


def test_clear_media_returns_controller_to_initial_state(qtbot, tmp_path) -> None:
    from conftest import FakeBackend

    backend = FakeBackend()
    controller = PlayerController(backend)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    controller.initialize(123)
    controller.load_file(media_file)

    assert controller.clear_media()
    assert backend.clear_called
    assert controller.current_file is None
    assert controller.state is PlaybackState.NO_MEDIA


def test_screenshot_is_forwarded_as_video_only(qtbot, tmp_path) -> None:
    from conftest import FakeBackend

    backend = FakeBackend()
    controller = PlayerController(backend)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    output = tmp_path / "shot.png"
    controller.initialize(123)
    controller.load_file(media_file)

    assert controller.save_screenshot(output)
    assert backend.screenshot_requests == [(output, False)]
