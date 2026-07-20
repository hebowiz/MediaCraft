from datetime import datetime

import pytest

from mediacraft.screenshot.file_naming import build_screenshot_path


def test_screenshot_path_contains_media_frame_and_second_timestamp(tmp_path) -> None:
    output = build_screenshot_path(
        tmp_path,
        "sample.video.mp4",
        12345,
        "png",
        captured_at=datetime(2026, 7, 20, 12, 34, 56, 789000),
    )

    assert output == tmp_path / (
        "sample.video_frame012345_20260720_123456.png"
    )


def test_screenshot_path_uses_jpg_extension_and_marks_unknown_frame(tmp_path) -> None:
    output = build_screenshot_path(
        tmp_path,
        "sample.mkv",
        -1,
        "jpeg",
        captured_at=datetime(2026, 1, 2, 3, 4, 5, 6000),
    )

    assert output.name == "sample_frameunknown_20260102_030405.jpg"


def test_screenshot_path_rejects_unknown_format(tmp_path) -> None:
    with pytest.raises(ValueError, match="未対応"):
        build_screenshot_path(tmp_path, "sample.mp4", 0, "bmp")
