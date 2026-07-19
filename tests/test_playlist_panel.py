from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from mediacraft.playlist.playlist_controller import PlaylistEntry
from mediacraft.ui.playlist_panel import PlaylistPanel


def test_panel_displays_duration_and_current_item(qtbot, tmp_path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mkv"
    panel = PlaylistPanel()
    qtbot.addWidget(panel)

    panel.set_entries((PlaylistEntry(first, 65.0), PlaylistEntry(second)))
    panel.set_current_index(1)

    assert "00:01:05" in panel.list_widget.item(0).text()
    assert "--:--:--" in panel.list_widget.item(1).text()
    assert panel.list_widget.item(1).text().startswith("▶ ")
    assert panel.list_widget.item(1).font().bold()
    assert not panel.list_widget.alternatingRowColors()
    assert "border-bottom" in panel.list_widget.styleSheet()


def test_external_drop_emits_files_without_reordering(qtbot, tmp_path) -> None:
    media_file = tmp_path / "sample.mp4"
    media_file.touch()
    panel = PlaylistPanel()
    qtbot.addWidget(panel)
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(media_file))])
    event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    with qtbot.waitSignal(panel.files_dropped) as blocker:
        panel.list_widget.dropEvent(event)

    assert blocker.args == [[str(media_file)]]
    assert event.isAccepted()
