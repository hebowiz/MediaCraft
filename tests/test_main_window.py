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
