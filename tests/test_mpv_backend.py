from pathlib import Path

from mediacraft.player.mpv_backend import MpvBackend


class CommandRecorder:
    def __init__(self) -> None:
        self.commands: list[tuple[object, ...]] = []

    def command(self, *args: object) -> None:
        self.commands.append(args)


def test_screenshot_command_uses_extension_and_video_only_mode() -> None:
    backend = MpvBackend()
    player = CommandRecorder()
    backend._player = player
    output = Path("frame.png")

    backend.save_screenshot(output)
    backend.save_screenshot(Path("with-subs.jpg"), include_subtitles=True)

    assert player.commands == [
        ("screenshot-to-file", str(output), "video"),
        ("screenshot-to-file", "with-subs.jpg", "subtitles"),
    ]
