import struct

from mediacraft.media.avi_info import inspect_avi, is_amv4


def _chunk(chunk_id: bytes, payload: bytes) -> bytes:
    padding = b"\0" if len(payload) % 2 else b""
    return chunk_id + struct.pack("<I", len(payload)) + payload + padding


def _amv4_avi() -> bytes:
    main_header = bytearray(56)
    struct.pack_into("<I", main_header, 0, 20_000)
    struct.pack_into("<I", main_header, 16, 165)
    stream_header = b"vidsAMV4" + bytes(48)
    header_list = b"hdrl" + _chunk(b"avih", main_header) + _chunk(
        b"LIST", b"strl" + _chunk(b"strh", stream_header)
    )
    payload = b"AVI " + _chunk(b"LIST", header_list)
    return b"RIFF" + struct.pack("<I", len(payload)) + payload


def test_inspect_avi_reads_amv4_without_media_decoder(tmp_path) -> None:
    media_path = tmp_path / "capture.avi"
    media_path.write_bytes(_amv4_avi())

    info = inspect_avi(media_path)

    assert info is not None
    assert info.video_fourcc == "AMV4"
    assert info.is_amv4
    assert info.frame_rate == 50.0
    assert info.duration == 3.3
    assert info.total_frames == 165
    assert is_amv4(media_path)


def test_inspect_avi_rejects_non_avi_file(tmp_path) -> None:
    media_path = tmp_path / "capture.mp4"
    media_path.write_bytes(b"not an AVI")

    assert inspect_avi(media_path) is None
    assert not is_amv4(media_path)
