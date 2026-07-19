from conftest import FakeBackend
from PySide6.QtCore import QPointF, QEvent, Qt
from PySide6.QtGui import QKeySequence, QMouseEvent
from PySide6.QtWidgets import QApplication

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
    assert window.frame_inspection_action.text() == "フレーム確認モード"
    assert window.frame_inspection_action.shortcut() == QKeySequence("I")
    assert not window.frame_inspection_action.isEnabled()

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

    window.leave_fullscreen()
    qtbot.waitUntil(lambda: not window.isFullScreen())
    assert window.menuBar().isVisible()
    assert window.statusBar().isVisible()
    assert window.control_bar.parentWidget() is window.centralWidget()


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
