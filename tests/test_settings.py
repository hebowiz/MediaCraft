from PySide6.QtWidgets import QFileDialog

from mediacraft.app.settings import AppSettings
from mediacraft.ui.settings_dialog import SettingsDialog


class MemorySettings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key, value) -> None:
        self.values[key] = value


def test_thumbnail_preload_setting_defaults_to_enabled() -> None:
    settings = AppSettings()
    settings._settings = MemorySettings()

    assert settings.thumbnail_preload_enabled()
    settings.set_thumbnail_preload_enabled(False)
    assert not settings.thumbnail_preload_enabled()


def test_settings_dialog_exposes_selected_values(qtbot, tmp_path, monkeypatch) -> None:
    dialog = SettingsDialog("C:/old", "png", True)
    qtbot.addWidget(dialog)
    selected = tmp_path / "captures"
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *_args, **_kwargs: str(selected),
    )

    dialog._choose_screenshot_directory()
    dialog.screenshot_format_combo.setCurrentIndex(1)
    dialog.thumbnail_preload_checkbox.setChecked(False)

    assert dialog.screenshot_directory == str(selected)
    assert dialog.screenshot_format == "jpeg"
    assert not dialog.thumbnail_preload_enabled
