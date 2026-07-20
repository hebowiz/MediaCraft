from mediacraft.media.codec_names import display_codec_name


def test_common_codec_names_are_short_and_readable() -> None:
    assert display_codec_name("h264") == "H.264"
    assert display_codec_name("hevc") == "HEVC"
    assert display_codec_name("aac") == "AAC"
    assert display_codec_name("pcm_s16le") == "PCM"


def test_unknown_codec_name_is_preserved_in_uppercase() -> None:
    assert display_codec_name("custom_codec") == "CUSTOM_CODEC"
    assert display_codec_name(None) == ""
