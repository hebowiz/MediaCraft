from PySide6.QtCore import QPoint

from mediacraft.ui.thumbnail_preview import ThumbnailPreview


def test_preview_time_is_displayed_to_whole_seconds(qtbot) -> None:
    preview = ThumbnailPreview()
    qtbot.addWidget(preview)

    preview.show_pending(754.567, "Frame: 22,637", QPoint(400, 400))

    assert preview.time_label.text() == "00:12:34"
    assert preview.frame_label.text() == "Frame: 22,637"
