from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QColor, QImage
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


def test_audio_file_uses_metadata_panel(qtbot) -> None:
    widget = VideoWidget()
    qtbot.addWidget(widget)

    widget.set_audio_loaded("music & voice.mp3")

    assert widget._audio_panel.isVisibleTo(widget)
    assert not widget._placeholder.isVisibleTo(widget)
    assert widget._audio_title.text() == "music & voice"
    assert widget._audio_artist.text() == "Artist: —"
    assert widget._audio_album.text() == "Album: —"
    assert widget._audio_bitrate.text() == "Codec: — / Bitrate: —"
    assert widget._audio_artwork.pixmap().isNull()

    widget.set_media_loaded(False)

    assert "動画・音声ファイル" in widget._placeholder.text()
    assert not widget._audio_panel.isVisibleTo(widget)


def test_audio_metadata_and_artwork_are_displayed(qtbot) -> None:
    widget = VideoWidget()
    qtbot.addWidget(widget)
    widget.resize(1200, 900)
    artwork = QImage(40, 30, QImage.Format.Format_RGB32)
    artwork.fill(QColor("navy"))

    widget.set_audio_loaded("fallback.flac")
    widget.set_audio_metadata(
        title="Track Title",
        artist="Track Artist",
        album="Album Name",
        bitrate_kbps=1411,
        codec="flac",
        artwork=artwork,
    )

    assert widget._audio_title.text() == "Track Title"
    assert widget._audio_artist.text() == "Artist: Track Artist"
    assert widget._audio_album.text() == "Album: Album Name"
    assert widget._audio_bitrate.text() == "Codec: flac / Bitrate: 1,411 kbps"
    assert not widget._audio_artwork.pixmap().isNull()
    assert widget._audio_artwork.width() > 420
    assert widget._audio_artwork.height() == widget._audio_artwork.width()
