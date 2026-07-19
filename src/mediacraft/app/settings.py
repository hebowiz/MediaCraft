from PySide6.QtCore import QByteArray, QSettings


class AppSettings:
    def __init__(self) -> None:
        self._settings = QSettings()

    def window_geometry(self) -> QByteArray:
        value = self._settings.value("window/geometry", QByteArray())
        return value if isinstance(value, QByteArray) else QByteArray()

    def set_window_geometry(self, geometry: QByteArray) -> None:
        self._settings.setValue("window/geometry", geometry)

    def playlist_splitter_state(self) -> QByteArray:
        value = self._settings.value("playlist/splitter_state", QByteArray())
        return value if isinstance(value, QByteArray) else QByteArray()

    def set_playlist_splitter_state(self, state: QByteArray) -> None:
        self._settings.setValue("playlist/splitter_state", state)

    def playlist_visible(self) -> bool:
        return self._settings.value("playlist/visible", True, type=bool)

    def set_playlist_visible(self, visible: bool) -> None:
        self._settings.setValue("playlist/visible", visible)

    def volume(self) -> int:
        return max(0, min(100, int(self._settings.value("playback/volume", 100))))

    def set_volume(self, value: int) -> None:
        self._settings.setValue("playback/volume", value)

    def muted(self) -> bool:
        return self._settings.value("playback/muted", False, type=bool)

    def set_muted(self, value: bool) -> None:
        self._settings.setValue("playback/muted", value)

    def speed(self) -> float:
        return max(0.1, min(4.0, float(self._settings.value("playback/speed", 1.0))))

    def set_speed(self, value: float) -> None:
        self._settings.setValue("playback/speed", value)

    def last_directory(self) -> str:
        return str(self._settings.value("files/last_directory", ""))

    def set_last_directory(self, path: str) -> None:
        self._settings.setValue("files/last_directory", path)
