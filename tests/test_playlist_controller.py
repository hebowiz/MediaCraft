from mediacraft.playlist.playlist_controller import PlaylistController


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
