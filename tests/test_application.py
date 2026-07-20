from PySide6.QtGui import QIcon

from mediacraft.app.application import APP_ICON_PATH


def test_application_icon_contains_all_windows_sizes() -> None:
    icon = QIcon(str(APP_ICON_PATH))

    assert APP_ICON_PATH.is_file()
    assert not icon.isNull()
    assert [size.width() for size in icon.availableSizes()] == [
        16,
        24,
        32,
        48,
        64,
        128,
        256,
    ]
