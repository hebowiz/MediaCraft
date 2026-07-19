from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtTest import QSignalSpy

from mediacraft.ui.video_widget import VideoWidget
from mediacraft.utils.drop_paths import local_drop_paths


def test_double_click_does_not_emit_single_click(qtbot) -> None:
    widget = VideoWidget()
    qtbot.addWidget(widget)
    widget.show()

    single_clicks = QSignalSpy(widget.clicked)
    double_clicks = QSignalSpy(widget.double_clicked)

    qtbot.mouseDClick(widget, Qt.MouseButton.LeftButton)
    qtbot.wait(widget._click_timer.interval() + 50)

    assert single_clicks.count() == 0
    assert double_clicks.count() == 1


def test_single_click_emits_after_double_click_window(qtbot) -> None:
    widget = VideoWidget()
    qtbot.addWidget(widget)
    widget.show()

    single_clicks = QSignalSpy(widget.clicked)

    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: single_clicks.count() == 1)

    assert single_clicks.count() == 1


def test_local_drop_accepts_files_and_directories(tmp_path) -> None:
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    folder = tmp_path / "videos"
    folder.mkdir()
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(media_file)), QUrl.fromLocalFile(str(folder))])

    assert local_drop_paths(mime_data) == [str(media_file), str(folder)]
