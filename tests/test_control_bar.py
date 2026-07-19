import pytest
from PySide6.QtCore import QPoint, Qt

from mediacraft.ui.control_bar import ControlBar


def test_buttons_use_fixed_size_icons(qtbot) -> None:
    controls = ControlBar()
    qtbot.addWidget(controls)

    buttons = (
        controls.play_button,
        controls.stop_button,
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
