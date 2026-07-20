from conftest import FakeBackend
from PySide6.QtCore import QPointF, QEvent, Qt
from PySide6.QtGui import QAction, QKeySequence, QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog

from mediacraft.media.audio_metadata import AudioMetadata
from mediacraft.player.playback_state import PlaybackState
from mediacraft.playlist.playlist_controller import RepeatMode
from mediacraft.ui.main_window import MainWindow


def test_window_initializes_backend_and_controls(qtbot) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()

    qtbot.waitUntil(lambda: backend.initialized)

    assert window.windowTitle() == "MediaCraft"
    assert window.control_bar.play_button.text() == ""
    assert window.control_bar.play_button.accessibleName() == "再生"
    assert window.video_widget.isVisible()
    assert window.playlist_panel.window() is window
    assert not window.playlist_panel.isWindow()
    assert window.frame_inspection_action.text() == "フレーム確認モード\tI"
    assert not window.frame_inspection_action.isEnabled()
    assert all(
        shortcut.context() is Qt.ShortcutContext.ApplicationShortcut
        for shortcut in window._shortcuts
    )
    assert "設定" in {action.text() for action in window.menuBar().actions()}
    assert "ヘルプ" in {action.text() for action in window.menuBar().actions()}
    assert window.shortcut_help_action.text() == "キーボードショートカット..."
    assert len(window._shortcut_help_entries) == len(window._shortcuts) == 30
    assert {entry.key for entry in window._shortcut_help_entries} == set(
        window._shortcut_by_key
    )

    window.close()
    assert backend.shutdown_called


def test_settings_dialog_updates_runtime_preferences(qtbot, monkeypatch, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)

    class AcceptedSettingsDialog:
        screenshot_directory = str(tmp_path / "captures")
        screenshot_format = "jpeg"
        thumbnail_preload_enabled = False

        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

    cancelled = False

    def cancel_preload() -> None:
        nonlocal cancelled
        cancelled = True

    monkeypatch.setattr(
        "mediacraft.ui.main_window.SettingsDialog",
        AcceptedSettingsDialog,
    )
    monkeypatch.setattr(window._thumbnail_provider, "cancel_preload", cancel_preload)
    saved: dict[str, object] = {}
    monkeypatch.setattr(
        window._settings,
        "set_screenshot_directory",
        lambda value: saved.__setitem__("directory", value),
    )
    monkeypatch.setattr(
        window._settings,
        "set_screenshot_format",
        lambda value: saved.__setitem__("format", value),
    )
    monkeypatch.setattr(
        window._settings,
        "set_thumbnail_preload_enabled",
        lambda value: saved.__setitem__("preload", value),
    )

    window.open_settings()

    assert saved == {
        "directory": str(tmp_path / "captures"),
        "format": "jpeg",
        "preload": False,
    }
    assert not window._thumbnail_preload_enabled
    assert cancelled


def test_fullscreen_uses_mouse_activated_overlay(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)

    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    window._load_file(str(media_file))
    window._set_playlist_visible(True)
    button_size = window.control_bar.fullscreen_button.size()

    window.toggle_fullscreen()
    qtbot.waitUntil(window.isFullScreen)
    qtbot.waitUntil(window._fullscreen_overlay.isVisible)

    assert not window.menuBar().isVisible()
    assert not window.statusBar().isVisible()
    assert not window.playlist_panel.isVisible()
    assert not window.playlist_action.isEnabled()
    assert not window._shortcut_by_key["Ctrl+L"].isEnabled()
    assert window.control_bar.parentWidget() is window._fullscreen_overlay
    assert window.control_bar.fullscreen_button.size() == button_size
    assert window._fullscreen_overlay.width() == window.width()
    assert "background-color: transparent" in window.control_bar.styleSheet()

    backend.current_position = 12.0
    window._controller.refresh()
    qtbot.keyClick(window, Qt.Key.Key_A)
    qtbot.waitUntil(lambda: window._ab_repeat_controller.point_a == 12.0)
    qtbot.keyClick(window, Qt.Key.Key_M)
    qtbot.waitUntil(lambda: backend.muted)
    qtbot.keyClick(
        window,
        Qt.Key.Key_L,
        modifier=Qt.KeyboardModifier.ControlModifier,
    )
    assert window.playlist_action.isChecked()
    assert window._playlist_was_visible

    window._hide_fullscreen_overlay()
    assert not window._fullscreen_overlay.isVisible()
    assert window.cursor().shape() is Qt.CursorShape.BlankCursor

    center = QPointF(window.video_widget.rect().center())
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        center,
        center,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(window.video_widget, event)
    qtbot.waitUntil(window._fullscreen_overlay.isVisible)
    assert window.cursor().shape() is not Qt.CursorShape.BlankCursor

    window.leave_fullscreen()
    qtbot.waitUntil(lambda: not window.isFullScreen())
    assert window.menuBar().isVisible()
    assert window.statusBar().isVisible()
    assert window.playlist_panel.isVisible()
    assert window.playlist_action.isEnabled()
    assert window._shortcut_by_key["Ctrl+L"].isEnabled()
    assert window.control_bar.parentWidget() is window.centralWidget()


def test_screenshot_action_saves_video_frame_and_shows_toast(
    qtbot, tmp_path, monkeypatch
) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    screenshot_directory = tmp_path / "screenshots"
    monkeypatch.setattr(
        window._settings,
        "screenshot_directory",
        lambda: str(screenshot_directory),
    )
    monkeypatch.setattr(window._settings, "screenshot_format", lambda: "png")

    assert "Ctrl+S" in window.screenshot_action.text()
    assert window.screenshot_shortcut.key() == QKeySequence("Ctrl+S")
    assert not window.screenshot_action.isEnabled()

    window._load_file(str(media_file))
    backend.current_position = 10.123
    window._controller.refresh()
    window.screenshot_action.trigger()

    assert window.screenshot_action.isEnabled()
    assert len(backend.screenshot_requests) == 1
    output_path, include_subtitles = backend.screenshot_requests[0]
    assert output_path.parent == screenshot_directory
    assert output_path.name.startswith("sample_frame000304_")
    assert output_path.suffix == ".png"
    assert include_subtitles is False
    assert window._toast.isVisible()
    assert "スクリーンショットを保存しました" in window._toast.label.text()

    window.toggle_fullscreen()
    qtbot.waitUntil(window.isFullScreen)
    qtbot.keyClick(
        window,
        Qt.Key.Key_S,
        modifier=Qt.KeyboardModifier.ControlModifier,
    )
    qtbot.waitUntil(lambda: len(backend.screenshot_requests) == 2)


def test_frame_inspection_menu_action_tracks_mode(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)

    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    window._load_file(str(media_file))

    assert window.frame_inspection_action.isEnabled()
    window.frame_inspection_action.trigger()
    assert window.frame_inspection_action.isChecked()
    assert window._frame_controller.inspection_mode
    assert backend.paused

    window._frame_controller.set_inspection_mode(False)
    assert not window.frame_inspection_action.isChecked()


def test_fullscreen_preserves_hidden_playlist_and_reenables_toggle(qtbot) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    window._set_playlist_visible(False)

    window.toggle_fullscreen()
    qtbot.waitUntil(window.isFullScreen)
    assert not window._shortcut_by_key["Ctrl+L"].isEnabled()

    window.leave_fullscreen()
    qtbot.waitUntil(lambda: not window.isFullScreen())

    assert not window.playlist_panel.isVisible()
    assert not window.playlist_action.isChecked()
    assert window.playlist_action.isEnabled()
    assert window._shortcut_by_key["Ctrl+L"].isEnabled()


def test_playlist_loads_multiple_files_and_advances_on_end(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()

    window._add_paths([str(first), str(second)], play_first=True)
    assert len(window._playlist_controller.entries) == 2
    assert backend.loaded_path == first.resolve()
    assert window._playlist_controller.current_index == 0

    backend.ended = True
    window._controller.refresh()

    assert backend.loaded_path == second.resolve()
    assert window._playlist_controller.current_index == 1


def test_open_files_replaces_playlist_and_accepts_multiple_selection(
    qtbot, tmp_path, monkeypatch
) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    old_file = tmp_path / "old.mp4"
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    for path in (old_file, first, second):
        path.touch()
    window._add_paths([str(old_file)], play_first=True)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        lambda *_args, **_kwargs: ([str(first), str(second)], ""),
    )

    window.open_files()

    assert [entry.path for entry in window._playlist_controller.entries] == [
        first.resolve(),
        second.resolve(),
    ]
    assert backend.loaded_path == first.resolve()
    assert "Ctrl+Shift+O" not in window._shortcut_by_key
    assert "複数ファイルを追加" not in {
        action.text() for action in window.findChildren(QAction)
    }


def test_folder_addition_uses_only_direct_media_files(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    (tmp_path / "b.mkv").touch()
    (tmp_path / "a.mp4").touch()
    (tmp_path / "notes.txt").touch()
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "hidden.mp4").touch()

    window._add_paths([str(tmp_path)], play_first=False)

    assert [entry.path.name for entry in window._playlist_controller.entries] == [
        "a.mp4",
        "b.mkv",
    ]


def test_folder_addition_includes_supported_audio_files(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    for extension in window.AUDIO_EXTENSIONS:
        (tmp_path / f"audio{extension}").touch()

    window._add_paths([str(tmp_path)], play_first=False)

    assert {entry.path.suffix for entry in window._playlist_controller.entries} == (
        window.AUDIO_EXTENSIONS
    )


def test_audio_mode_disables_video_only_features_and_restores_them(
    qtbot, tmp_path, monkeypatch
) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    audio = tmp_path / "sample.mp3"
    video = tmp_path / "sample.mp4"
    audio.touch()
    video.touch()
    probed: list[str] = []
    monkeypatch.setattr(window._media_probe, "probe", probed.append)
    monkeypatch.setattr(window._audio_metadata_probe, "probe", lambda _path: None)

    window._add_paths([str(audio)], play_first=True)

    assert backend.loaded_path == audio.resolve()
    assert window._audio_mode
    assert window.control_bar.frame_label.text() == "Audio"
    assert window.video_widget._audio_panel.isVisibleTo(window.video_widget)
    assert window.video_widget._audio_title.text() == "sample"
    assert not window.frame_inspection_action.isEnabled()
    assert not window.screenshot_action.isEnabled()
    assert not window._shortcut_by_key["Ctrl+S"].isEnabled()
    assert not window._shortcut_by_key[","].isEnabled()
    assert not window._shortcut_by_key["."].isEnabled()
    assert not window._shortcut_by_key["I"].isEnabled()
    assert window._thumbnail_provider.media_path is None
    assert probed == []

    window._on_audio_metadata(
        str(audio),
        AudioMetadata(
            title="Track Title",
            artist="Track Artist",
            album="Album Name",
            bitrate_kbps=320,
        ),
    )

    assert window.video_widget._audio_title.text() == "Track Title"
    assert window.video_widget._audio_artist.text() == "アーティスト: Track Artist"
    assert window.video_widget._audio_album.text() == "アルバム: Album Name"
    assert window.video_widget._audio_bitrate.text() == "ビットレート: 320 kbps"

    window._add_paths([str(video)], play_first=True)

    assert backend.loaded_path == video.resolve()
    assert not window._audio_mode
    assert not window.video_widget._audio_panel.isVisibleTo(window.video_widget)
    assert window.frame_inspection_action.isEnabled()
    assert window.screenshot_action.isEnabled()
    assert window._shortcut_by_key["Ctrl+S"].isEnabled()
    assert window._shortcut_by_key[","].isEnabled()
    assert window._shortcut_by_key["."].isEnabled()
    assert window._shortcut_by_key["I"].isEnabled()
    assert probed == [str(video.resolve())]


def test_unreadable_playlist_item_is_skipped(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    broken = tmp_path / "broken.mp4"
    valid = tmp_path / "valid.mp4"
    broken.touch()
    valid.touch()
    backend.fail_load_paths.add(broken.resolve())

    window._add_paths([str(broken), str(valid)], play_first=True)

    qtbot.waitUntil(lambda: backend.loaded_path == valid.resolve())
    assert window._playlist_controller.current_index == 1


def test_playlist_item_can_be_selected_and_double_clicked(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    window._add_paths([str(first), str(second)], play_first=False)
    window._set_playlist_visible(True)
    qtbot.wait(200)

    item = window.playlist_panel.list_widget.item(1)
    position = window.playlist_panel.list_widget.visualItemRect(item).center()
    qtbot.mouseClick(
        window.playlist_panel.list_widget.viewport(),
        Qt.MouseButton.LeftButton,
        pos=position,
    )
    assert item.isSelected()

    qtbot.mouseDClick(
        window.playlist_panel.list_widget.viewport(),
        Qt.MouseButton.LeftButton,
        pos=position,
    )
    assert backend.loaded_path == second.resolve()


def test_play_button_starts_selected_playlist_item(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    window._append_playlist_from_drop([str(first), str(second)])
    window._set_playlist_visible(True)
    qtbot.wait(200)

    item = window.playlist_panel.list_widget.item(1)
    position = window.playlist_panel.list_widget.visualItemRect(item).center()
    qtbot.mouseClick(
        window.playlist_panel.list_widget.viewport(),
        Qt.MouseButton.LeftButton,
        pos=position,
    )
    qtbot.mouseClick(window.control_bar.play_button, Qt.MouseButton.LeftButton)

    assert backend.loaded_path == second.resolve()
    assert not backend.paused


def test_play_button_pauses_current_item_before_selected_item(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    window._add_paths([str(first), str(second)], play_first=True)
    window._set_playlist_visible(True)
    qtbot.wait(200)

    item = window.playlist_panel.list_widget.item(1)
    position = window.playlist_panel.list_widget.visualItemRect(item).center()
    qtbot.mouseClick(
        window.playlist_panel.list_widget.viewport(),
        Qt.MouseButton.LeftButton,
        pos=position,
    )
    qtbot.mouseClick(window.control_bar.play_button, Qt.MouseButton.LeftButton)

    assert backend.loaded_path == first.resolve()
    assert backend.paused

    qtbot.mouseClick(window.control_bar.play_button, Qt.MouseButton.LeftButton)

    assert backend.loaded_path == second.resolve()
    assert not backend.paused


def test_selected_playlist_item_can_be_removed(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    window._add_paths([str(first), str(second)], play_first=False)
    window._set_playlist_visible(True)
    qtbot.wait(200)

    item = window.playlist_panel.list_widget.item(0)
    position = window.playlist_panel.list_widget.visualItemRect(item).center()
    qtbot.mouseClick(
        window.playlist_panel.list_widget.viewport(),
        Qt.MouseButton.LeftButton,
        pos=position,
    )
    qtbot.mouseClick(window.playlist_panel.remove_button, Qt.MouseButton.LeftButton)

    assert [entry.path for entry in window._playlist_controller.entries] == [
        second.resolve()
    ]


def test_drop_target_controls_append_or_replace_behavior(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    appended = tmp_path / "appended.mp4"
    replacement = tmp_path / "replacement.mp4"
    first.touch()
    appended.touch()
    replacement.touch()
    window._add_paths([str(first)], play_first=True)

    window._append_playlist_from_drop([str(appended)])
    assert [entry.path for entry in window._playlist_controller.entries] == [
        first.resolve(),
        appended.resolve(),
    ]
    assert backend.loaded_path == first.resolve()

    window._replace_playlist_from_drop([str(replacement)])
    assert [entry.path for entry in window._playlist_controller.entries] == [
        replacement.resolve()
    ]
    assert backend.loaded_path == replacement.resolve()


def test_playlist_end_selects_first_item_and_stops(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    window._add_paths([str(first), str(second)], play_first=True)
    window._play_next()

    backend.ended = True
    window._controller.refresh()

    assert backend.loaded_path == first.resolve()
    assert backend.paused
    assert window._controller.state is PlaybackState.STOPPED
    assert window._playlist_controller.current_index == 0
    assert window.playlist_panel.list_widget.currentRow() == 0
    assert window.control_bar.play_button.accessibleName() == "再生"


def test_playlist_repeat_modes_continue_playback_on_media_end(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    window._add_paths([str(first), str(second)], play_first=True)
    window._play_next()

    window._playlist_controller.set_repeat_mode(RepeatMode.ALL)
    backend.ended = True
    window._controller.refresh()
    assert backend.loaded_path == first.resolve()
    assert not backend.paused

    window._playlist_controller.set_repeat_mode(RepeatMode.ONE)
    backend.ended = True
    window._controller.refresh()
    assert backend.loaded_path == first.resolve()
    assert not backend.paused


def test_removing_playing_item_loads_remaining_item_and_stops(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    window._add_paths([str(first), str(second)], play_first=True)

    window._playlist_controller.remove_indices([0])

    assert backend.loaded_path == second.resolve()
    assert backend.paused
    assert window._controller.state is PlaybackState.STOPPED
    assert window._playlist_controller.current_index == 0
    assert window.playlist_panel.list_widget.currentRow() == 0
    assert window.control_bar.play_button.accessibleName() == "再生"


def test_clearing_playlist_restores_initial_player_view(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    window._add_paths([str(media_file)], play_first=True)

    window._playlist_controller.clear()

    assert backend.clear_called
    assert backend.loaded_path is None
    assert window._controller.current_file is None
    assert window._controller.state is PlaybackState.NO_MEDIA
    assert window.windowTitle() == "MediaCraft"
    assert window.video_widget._placeholder.isVisible()
    assert window.control_bar.play_button.accessibleName() == "再生"


def test_ab_repeat_menu_controls_seek_bar_state(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    window._add_paths([str(media_file)], play_first=True)

    window._controller.seek_absolute(10.0)
    window.set_a_action.trigger()
    window._controller.seek_absolute(25.0)
    window.set_b_action.trigger()
    window.ab_repeat_action.trigger()

    assert backend.ab_loop == (10.0, 25.0)
    assert window.ab_repeat_action.isChecked()
    assert window.control_bar.seek_slider._ab_start == 10.0
    assert window.control_bar.seek_slider._ab_end == 25.0
    assert window.control_bar.seek_slider._ab_enabled is True


def test_shift_a_and_b_remove_ab_markers(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    window._add_paths([str(media_file)], play_first=True)

    window._controller.seek_absolute(10.0)
    window.set_a_action.trigger()
    window._controller.seek_absolute(25.0)
    window.set_b_action.trigger()

    qtbot.keyClick(
        window,
        Qt.Key.Key_A,
        modifier=Qt.KeyboardModifier.ShiftModifier,
    )
    assert window._ab_repeat_controller.point_a is None
    assert window._ab_repeat_controller.point_b == 25.0

    qtbot.keyClick(
        window,
        Qt.Key.Key_B,
        modifier=Qt.KeyboardModifier.ShiftModifier,
    )
    assert window._ab_repeat_controller.point_b is None
    assert window.seek_a_action.text() == "A点へ移動"
    assert window.seek_b_action.text() == "B点へ移動"
    assert "Shift+A" in window.clear_a_action.text()
    assert "Shift+B" in window.clear_b_action.text()


def test_ab_repeat_action_returns_to_unchecked_without_points(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    window._add_paths([str(media_file)], play_first=True)

    window.ab_repeat_action.trigger()

    assert not window.ab_repeat_action.isChecked()
    assert backend.ab_loop is None
