from conftest import FakeBackend
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

    window.close()
    assert backend.shutdown_called


def test_fullscreen_uses_mouse_activated_overlay(qtbot, tmp_path) -> None:
    backend = FakeBackend()
    window = MainWindow(backend)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: backend.initialized)

    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    window._load_file(str(media_file))
    button_size = window.control_bar.fullscreen_button.size()

    window.toggle_fullscreen()
    qtbot.waitUntil(window.isFullScreen)
    qtbot.waitUntil(window._fullscreen_overlay.isVisible)

    assert not window.menuBar().isVisible()
    assert not window.statusBar().isVisible()
    assert window.control_bar.parentWidget() is window._fullscreen_overlay
    assert window.control_bar.fullscreen_button.size() == button_size
    assert window._fullscreen_overlay.width() == window.width()
    assert "background-color: transparent" in window.control_bar.styleSheet()

    window._hide_fullscreen_overlay()
    assert not window._fullscreen_overlay.isVisible()

    qtbot.mouseMove(window.video_widget, pos=window.video_widget.rect().center())
    qtbot.waitUntil(window._fullscreen_overlay.isVisible)

    window.leave_fullscreen()
    qtbot.waitUntil(lambda: not window.isFullScreen())
    assert window.menuBar().isVisible()
    assert window.statusBar().isVisible()
    assert window.control_bar.parentWidget() is window.centralWidget()
