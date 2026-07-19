from conftest import FakeBackend
from mediacraft.frame.frame_controller import FrameController
from mediacraft.player.player_controller import PlayerController


def loaded_controllers(tmp_path):
    backend = FakeBackend()
    player = PlayerController(backend)
    frame = FrameController(player)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    player.initialize(123)
    player.load_file(media_file)
    return backend, player, frame


def test_inspection_mode_pauses_and_throttles_repeated_steps(qtbot, tmp_path) -> None:
    backend, _player, frame = loaded_controllers(tmp_path)

    frame.set_inspection_mode(True)
    frame.request_step(1)
    frame.request_step(10)
    frame.request_step(10)

    assert backend.paused
    assert backend.frame_steps == [1]
    qtbot.waitUntil(lambda: backend.frame_steps == [1, 20])


def test_vfr_frame_display_is_marked_as_approximate(qtbot, tmp_path) -> None:
    _backend, player, frame = loaded_controllers(tmp_path)
    received: list[tuple[int, bool]] = []
    frame.frame_display_changed.connect(
        lambda number, approximate: received.append((number, approximate))
    )

    frame.set_frame_rate_analysis(30.0, False)
    player.refresh()
    assert received[-1] == (0, False)

    frame.set_frame_rate_analysis(30.0, True)
    assert received[-1] == (0, True)


def test_stop_exits_inspection_mode(qtbot, tmp_path) -> None:
    _backend, player, frame = loaded_controllers(tmp_path)
    frame.set_inspection_mode(True)

    player.stop()

    assert frame.inspection_mode is False
