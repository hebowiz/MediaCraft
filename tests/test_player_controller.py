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
