import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLabel

from mediacraft.ui.control_bar import ControlBar


def assert_icon_is_white(button) -> None:
    image = button.icon().pixmap(button.iconSize()).toImage()
    visible_colors = {
        image.pixelColor(x, y).getRgb()[:3]
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
    }
    assert visible_colors == {(255, 255, 255)}


def test_buttons_use_fixed_size_icons(qtbot) -> None:
    controls = ControlBar()
    qtbot.addWidget(controls)

    buttons = (
        controls.previous_button,
        controls.play_button,
        controls.stop_button,
        controls.next_button,
        controls.frame_back_button,
        controls.frame_forward_button,
        controls.mute_button,
        controls.fullscreen_button,
    )
    original_sizes = [button.size() for button in buttons]

    controls.set_playing(True)
    controls.set_volume(75, True)
    controls.set_fullscreen(True)

    assert not hasattr(controls, "open_button")
    assert all(button.text() == "" for button in buttons)
    assert [button.size() for button in buttons] == original_sizes
    assert controls.play_button.accessibleName() == "一時停止"
    assert controls.fullscreen_button.accessibleName() == "フルスクリーン解除"
    assert "速度" not in {label.text() for label in controls.findChildren(QLabel)}
    for button in buttons:
        assert_icon_is_white(button)


def test_frame_inspection_shows_precision_and_simplifies_controls(qtbot) -> None:
    controls = ControlBar()
    qtbot.addWidget(controls)
    controls.show()

    controls.set_frame_info(1234, True, 29.97, True)
    controls.set_frame_inspection(True)
    controls.set_position(1.234, 10.0)

    assert controls.frame_label.text() == "Frame: 1,234 | VFR"
    assert controls.time_label.text() == "00:00:01.234 / 00:00:10.000"
    assert not hasattr(controls, "frame_mode_button")
    assert not controls.speed_combo.isVisible()
    assert not controls.volume_slider.isVisible()

    controls.set_frame_inspection(False)
    controls.set_position(1.234, 10.0)
    assert controls.time_label.text() == "00:00:01 / 00:00:10"


def test_cfr_frame_rate_is_displayed_as_fps(qtbot) -> None:
    controls = ControlBar()
    qtbot.addWidget(controls)

    controls.set_frame_info(90, False, 60.0, False)
    assert controls.frame_label.text() == "Frame: 90 | 60.00 FPS"

    controls.set_frame_info(-1, True, 0.0, None)
    assert controls.frame_label.text() == "Frame: -- | -- FPS"


def test_ab_points_are_forwarded_to_seek_slider(qtbot) -> None:
    controls = ControlBar()
    qtbot.addWidget(controls)
    controls.set_position(0.0, 100.0)

    controls.set_ab_points(10.0, 30.0, True)

    assert controls.seek_slider._ab_start == 10.0
    assert controls.seek_slider._ab_end == 30.0
    assert controls.seek_slider._ab_duration == 100.0
    assert controls.seek_slider._ab_enabled is True
    assert controls.seek_slider.toolTip() == (
        "A: 00:00:10.000\nB: 00:00:30.000\nA-Bリピート中"
    )


def test_ab_overlay_keeps_handle_and_point_markers_visible(qtbot) -> None:
    controls = ControlBar()
    controls.resize(800, controls.sizeHint().height())
    qtbot.addWidget(controls)
    controls.show()
    controls.set_position(20.0, 100.0)
    controls.set_ab_points(10.0, 30.0, True)

    slider = controls.seek_slider
    image = QImage(slider.size(), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    slider.render(image)
    colors = {
        image.pixelColor(x, y).getRgb()[:3]
        for y in range(image.height())
        for x in range(image.width())
    }

    assert (108, 166, 220) in colors  # 再生位置ハンドル
    assert (97, 210, 135) in colors  # A点
    assert (242, 166, 90) in colors  # B点


def test_volume_click_jumps_to_pointer(qtbot) -> None:
    controls = ControlBar()
    qtbot.addWidget(controls)
    controls.show()

    slider = controls.volume_slider
    qtbot.mouseClick(
        slider,
        Qt.MouseButton.LeftButton,
        pos=QPoint(round(slider.width() * 0.75), slider.height() // 2),
    )

    assert slider.value() == pytest.approx(75, abs=8)


def test_seek_click_emits_clicked_position(qtbot) -> None:
    controls = ControlBar()
    controls.resize(800, controls.sizeHint().height())
    controls.set_position(0, 200)
    qtbot.addWidget(controls)
    controls.show()

    slider = controls.seek_slider
    with qtbot.waitSignal(controls.seek_requested) as blocker:
        qtbot.mouseClick(
            slider,
            Qt.MouseButton.LeftButton,
            pos=QPoint(round(slider.width() * 0.25), slider.height() // 2),
        )

    assert blocker.args[0] == pytest.approx(50, abs=3)


def test_speed_and_volume_stay_on_transport_row(qtbot) -> None:
    controls = ControlBar()
    qtbot.addWidget(controls)
    controls.show()

    transport_y = controls.fullscreen_button.geometry().center().y()
    assert controls.speed_combo.geometry().center().y() == transport_y
    assert controls.mute_button.geometry().center().y() == transport_y
    assert controls.volume_slider.geometry().center().y() == transport_y
    assert controls.seek_slider.geometry().center().y() < transport_y
