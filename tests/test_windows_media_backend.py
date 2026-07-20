from pathlib import Path

from mediacraft.player.windows_media_backend import WindowsMediaBackend


class FakeAxObject:
    def __init__(self, properties=None) -> None:
        self.properties = dict(properties or {})
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def propertyBag(self):
        return dict(self.properties)

    def setPropertyBag(self, properties) -> None:
        self.properties = dict(properties)

    def setProperty(self, name: str, value: object) -> bool:
        self.properties[name] = value
        return True

    def dynamicCall(self, name: str, *args):
        self.calls.append((name, args))
        if name == "currentPosition":
            return self.properties.get("currentPosition", 0.0)
        if name == "duration":
            return self.properties.get("duration", 0.0)
        if name == "playState":
            return self.properties.get("playState", 0)
        return None


class FakeAxPlayer(FakeAxObject):
    def __init__(self) -> None:
        super().__init__({"playState": WindowsMediaBackend.PLAYING})
        self.controls = FakeAxObject({"currentPosition": 0.0})
        self.settings = FakeAxObject()
        self.media = FakeAxObject({"duration": 12.5})
        self.visible = False
        self.cleared = False

    def isNull(self) -> bool:
        return False

    def querySubObject(self, name: str):
        return {
            "controls": self.controls,
            "settings": self.settings,
            "currentMedia": self.media,
        }.get(name)

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def raise_(self) -> None:
        pass

    def clear(self) -> None:
        self.cleared = True


def test_windows_media_backend_controls_amv4_player(tmp_path, monkeypatch) -> None:
    player = FakeAxPlayer()
    backend = WindowsMediaBackend(lambda: player)
    media_path = tmp_path / "capture.avi"
    media_path.touch()
    monkeypatch.setattr(
        "mediacraft.player.windows_media_backend.inspect_avi",
        lambda _path: type("Info", (), {"frame_rate": 60.0, "duration": 12.5})(),
    )

    backend.initialize(123)
    backend.set_volume(72)
    backend.set_mute(True)
    backend.set_speed(1.25)
    backend.load(media_path)
    backend.seek_absolute(6.0)

    assert player.visible
    assert player.properties["URL"] == str(media_path)
    assert player.settings.properties == {"volume": 72, "mute": True, "rate": 1.25}
    assert player.controls.properties["currentPosition"] == 6.0
    assert backend.duration() == 12.5
    assert backend.frame_rate() == 60.0
    assert not backend.is_paused()


def test_windows_media_backend_enforces_ab_loop() -> None:
    player = FakeAxPlayer()
    backend = WindowsMediaBackend(lambda: player)
    backend.initialize(0)
    player.controls.properties["currentPosition"] = 8.0
    backend.set_ab_loop(2.0, 7.0)

    assert backend.position() == 2.0
    assert player.controls.properties["currentPosition"] == 2.0


def test_windows_media_backend_treats_stopped_near_end_as_media_end() -> None:
    player = FakeAxPlayer()
    backend = WindowsMediaBackend(lambda: player)
    backend.initialize(0)
    backend._fps = 60.0
    backend._duration = 3.3
    player.controls.properties["currentPosition"] = 3.29

    assert backend.position() == 3.29
    assert not backend.has_ended()

    player.properties["playState"] = WindowsMediaBackend.STOPPED
    player.controls.properties["currentPosition"] = 0.0

    assert backend.position() == 0.0
    assert backend.has_ended()


def test_windows_media_backend_rewinds_by_frame_duration() -> None:
    player = FakeAxPlayer()
    backend = WindowsMediaBackend(lambda: player)
    backend.initialize(0)
    backend._fps = 50.0
    player.controls.properties["currentPosition"] = 2.0

    backend.frame_step(-1)

    assert player.controls.properties["currentPosition"] == 1.98
