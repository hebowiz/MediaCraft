from conftest import FakeBackend
from mediacraft.player.player_controller import PlayerController
from mediacraft.repeat.ab_repeat_controller import ABRepeatController


def loaded_controllers(tmp_path):
    backend = FakeBackend()
    player = PlayerController(backend)
    repeat = ABRepeatController(player)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    player.initialize(123)
    player.load_file(media_file)
    return backend, player, repeat


def test_sets_points_and_enables_backend_loop(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(10.0)
    assert repeat.set_point_a()
    player.seek_absolute(20.0)
    assert repeat.set_point_b()

    assert repeat.set_enabled(True)
    assert repeat.point_a == 10.0
    assert repeat.point_b == 20.0
    assert repeat.enabled
    assert backend.ab_loop == (10.0, 20.0)

    repeat.set_enabled(False)
    assert backend.ab_loop is None
    assert repeat.point_a == 10.0
    assert repeat.point_b == 20.0


def test_rejects_b_point_before_a_point(qtbot, tmp_path) -> None:
    _backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(30.0)
    repeat.set_point_a()
    player.seek_absolute(20.0)

    with qtbot.waitSignal(repeat.message) as blocker:
        result = repeat.set_point_b()

    assert result is False
    assert repeat.point_b is None
    assert "B点はA点より後" in blocker.args[0]


def test_file_change_clears_points_and_loop(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(5.0)
    repeat.set_point_a()
    player.seek_absolute(15.0)
    repeat.set_point_b()
    repeat.set_enabled(True)
    next_file = tmp_path / "next.mp4"
    next_file.touch()

    player.load_file(next_file)

    assert repeat.point_a is None
    assert repeat.point_b is None
    assert not repeat.enabled
    assert backend.ab_loop is None


def test_seek_and_individual_clear(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(7.0)
    repeat.set_point_a()
    player.seek_absolute(17.0)
    repeat.set_point_b()

    repeat.seek_to_a()
    assert backend.current_position == 7.0
    repeat.seek_to_b()
    assert backend.current_position == 17.0

    repeat.clear_point_a()
    assert repeat.point_a is None
    assert repeat.point_b == 17.0


def test_enabling_outside_range_seeks_to_a_and_preserves_pause(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(10.0)
    repeat.set_point_a()
    player.seek_absolute(20.0)
    repeat.set_point_b()
    player.toggle_play_pause()
    assert backend.paused
    player.seek_absolute(30.0)

    repeat.set_enabled(True)

    assert backend.current_position == 10.0
    assert backend.paused
    assert backend.ab_loop == (10.0, 20.0)


def test_enabling_inside_range_keeps_current_position(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(10.0)
    repeat.set_point_a()
    player.seek_absolute(20.0)
    repeat.set_point_b()
    player.seek_absolute(15.0)

    repeat.set_enabled(True)

    assert backend.current_position == 15.0


def test_manual_seek_outside_range_disables_loop_but_keeps_points(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(10.0)
    repeat.set_point_a()
    player.seek_absolute(20.0)
    repeat.set_point_b()
    player.seek_absolute(15.0)
    repeat.set_enabled(True)

    with qtbot.waitSignal(repeat.message) as blocker:
        player.seek_absolute(25.0)

    assert not repeat.enabled
    assert repeat.point_a == 10.0
    assert repeat.point_b == 20.0
    assert backend.ab_loop is None
    assert "区間外へ移動したため" in blocker.args[0]


def test_manual_seek_inside_range_keeps_loop_enabled(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(10.0)
    repeat.set_point_a()
    player.seek_absolute(20.0)
    repeat.set_point_b()
    repeat.set_enabled(True)

    player.seek_absolute(15.0)

    assert repeat.enabled
    assert backend.ab_loop == (10.0, 20.0)


def test_manual_frame_step_outside_range_disables_loop(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(10.0)
    repeat.set_point_a()
    player.seek_absolute(20.0)
    repeat.set_point_b()
    repeat.set_enabled(True)

    assert player.frame_step(-1)
    player.refresh()

    assert not repeat.enabled
    assert repeat.point_a == 10.0
    assert repeat.point_b == 20.0
    assert backend.ab_loop is None


def test_playback_position_outside_range_does_not_count_as_manual_seek(qtbot, tmp_path) -> None:
    backend, player, repeat = loaded_controllers(tmp_path)
    player.seek_absolute(10.0)
    repeat.set_point_a()
    player.seek_absolute(20.0)
    repeat.set_point_b()
    repeat.set_enabled(True)

    backend.current_position = 25.0
    player.refresh()

    assert repeat.enabled
    assert backend.ab_loop == (10.0, 20.0)
