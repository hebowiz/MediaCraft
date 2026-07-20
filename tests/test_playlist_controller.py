import random

from mediacraft.playlist.playlist_controller import PlaylistController, RepeatMode


def test_playlist_adds_unique_files_and_navigates(qtbot, tmp_path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mkv"
    first.touch()
    second.touch()
    playlist = PlaylistController()
    requested: list[str] = []
    playlist.play_requested.connect(requested.append)

    assert playlist.add_files([first, second, first]) == 0
    assert [entry.path for entry in playlist.entries] == [first.resolve(), second.resolve()]

    playlist.set_current_path(first)
    assert playlist.play_next()
    assert requested[-1] == str(second.resolve())
    assert not playlist.play_previous()


def test_playlist_reorders_and_removes_current_item(qtbot, tmp_path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    playlist = PlaylistController()
    playlist.add_files([first, second])
    playlist.set_current_path(first)

    playlist.reorder([second, first])
    assert playlist.current_index == 1
    assert [entry.path for entry in playlist.entries] == [second.resolve(), first.resolve()]

    replacements: list[str] = []
    playlist.current_item_removed.connect(replacements.append)
    playlist.remove_indices([1])
    assert playlist.current_index == 0
    assert [entry.path for entry in playlist.entries] == [second.resolve()]
    assert replacements == [str(second.resolve())]


def test_playlist_updates_known_duration(qtbot, tmp_path) -> None:
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    playlist = PlaylistController()
    playlist.add_files([media_file])
    playlist.set_current_path(media_file)

    playlist.update_current_duration(12.5)

    assert playlist.entries[0].duration == 12.5


def test_repeat_all_wraps_and_repeat_one_only_affects_automatic_advance(
    qtbot, tmp_path
) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    playlist = PlaylistController()
    playlist.add_files([first, second])
    requested: list[str] = []
    playlist.play_requested.connect(requested.append)

    playlist.set_current_path(second)
    playlist.set_repeat_mode(RepeatMode.ALL)
    assert playlist.play_next(automatic=True)
    assert requested[-1] == str(first.resolve())

    playlist.set_current_path(first)
    playlist.set_repeat_mode(RepeatMode.ONE)
    assert playlist.play_next(automatic=True)
    assert requested[-1] == str(first.resolve())
    assert playlist.play_next()
    assert requested[-1] == str(second.resolve())


def test_shuffle_plays_every_other_item_once_and_previous_uses_history(
    qtbot, tmp_path
) -> None:
    paths = [tmp_path / f"{index}.mp4" for index in range(4)]
    for path in paths:
        path.touch()
    playlist = PlaylistController(rng=random.Random(7))
    playlist.add_files(paths)
    playlist.set_current_path(paths[0])
    playlist.set_shuffle_enabled(True)
    requested: list[str] = []

    def record_and_select(path: str) -> None:
        requested.append(path)
        playlist.set_current_path(path)

    playlist.play_requested.connect(record_and_select)
    for _ in range(3):
        assert playlist.play_next()

    assert len(set(requested)) == 3
    assert str(paths[0].resolve()) not in requested
    assert not playlist.play_next()

    last = requested[-1]
    assert playlist.play_previous()
    assert requested[-1] != last


def test_repeat_all_reshuffles_after_each_shuffle_pass(qtbot, tmp_path) -> None:
    paths = [tmp_path / f"{index}.mp4" for index in range(3)]
    for path in paths:
        path.touch()
    playlist = PlaylistController(rng=random.Random(11))
    playlist.add_files(paths)
    playlist.set_current_path(paths[0])
    playlist.set_shuffle_enabled(True)
    playlist.set_repeat_mode(RepeatMode.ALL)
    requested: list[str] = []

    def record_and_select(path: str) -> None:
        requested.append(path)
        playlist.set_current_path(path)

    playlist.play_requested.connect(record_and_select)
    for _ in range(3):
        assert playlist.play_next(automatic=True)

    assert len(set(requested[:2])) == 2
    assert requested[2] != requested[1]
