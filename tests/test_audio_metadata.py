from PySide6.QtGui import QColor, QImage

from mediacraft.media.audio_metadata import (
    read_audio_metadata,
    repair_legacy_japanese_tag,
)


class FakeStream:
    def __init__(
        self, stream_type: str, *, metadata=None, bit_rate=None, codec_name=""
    ) -> None:
        self.type = stream_type
        self.metadata = dict(metadata or {})
        self.bit_rate = bit_rate
        self.duration = None
        self.time_base = None
        self.codec_context = type("CodecContext", (), {"name": codec_name})()


class FakeContainer:
    def __init__(self, streams, *, metadata=None, bit_rate=None, duration=None) -> None:
        self.streams = streams
        self.metadata = dict(metadata or {})
        self.bit_rate = bit_rate
        self.duration = duration

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def decode(self, _stream):
        return iter([object()])


def test_legacy_cp932_id3_text_is_repaired() -> None:
    title = "\x82\xdc\x82\xc7\x82\xeb\x82\xdd\x82\xcc\x97\xd6\x89\xf4"
    artist = "\x89\xcd\x88\xe4\x89p\x97\xa2"
    encoder = "Exact Audio Copy   (\x83o\x81[\x83X\x83g\x83\x82\x81[\x83h)"

    assert repair_legacy_japanese_tag(title) == "まどろみの輪廻"
    assert repair_legacy_japanese_tag(artist) == "河井英里"
    assert repair_legacy_japanese_tag(encoder) == "Exact Audio Copy   (バーストモード)"


def test_valid_unicode_and_western_tags_are_not_changed() -> None:
    assert repair_legacy_japanese_tag("まどろみの輪廻") == "まどろみの輪廻"
    assert repair_legacy_japanese_tag("Beyoncé") == "Beyoncé"
    assert repair_legacy_japanese_tag("Track Title") == "Track Title"


def test_audio_metadata_normalizes_common_tag_names_and_artwork(
    tmp_path, monkeypatch
) -> None:
    media_path = tmp_path / "tagged.m4a"
    media_path.touch()
    audio_stream = FakeStream(
        "audio",
        metadata={"PERFORMER": "Track Artist", "WM/AlbumTitle": "Album Name"},
        bit_rate=256_000,
        codec_name="aac",
    )
    container = FakeContainer(
        [audio_stream, FakeStream("video")],
        metadata={"TITLE": "Track Title"},
    )
    artwork = QImage(4, 4, QImage.Format.Format_RGB32)
    artwork.fill(QColor("red"))
    monkeypatch.setattr(
        "mediacraft.media.audio_metadata.av.open", lambda _path: container
    )
    monkeypatch.setattr(
        "mediacraft.media.audio_metadata.frame_to_image",
        lambda _frame, _width: artwork,
    )

    metadata = read_audio_metadata(media_path)

    assert metadata.title == "Track Title"
    assert metadata.artist == "Track Artist"
    assert metadata.album == "Album Name"
    assert metadata.bitrate_kbps == 256
    assert metadata.codec == "AAC"
    assert metadata.artwork is artwork


def test_audio_metadata_estimates_bitrate_from_file_size(tmp_path, monkeypatch) -> None:
    media_path = tmp_path / "untagged.wav"
    media_path.write_bytes(b"0" * 2000)
    container = FakeContainer(
        [FakeStream("audio")],
        duration=2_000_000,
    )
    monkeypatch.setattr(
        "mediacraft.media.audio_metadata.av.open", lambda _path: container
    )

    metadata = read_audio_metadata(media_path)

    assert metadata.title == ""
    assert metadata.artist == ""
    assert metadata.album == ""
    assert metadata.bitrate_kbps == 8
    assert metadata.codec == ""
    assert metadata.artwork is None
