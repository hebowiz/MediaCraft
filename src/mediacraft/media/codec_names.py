"""Short, user-facing names for FFmpeg codec identifiers."""

_CODEC_NAMES = {
    "aac": "AAC",
    "ac3": "AC-3",
    "alac": "ALAC",
    "amv": "AMV",
    "amv4": "AMV4",
    "av1": "AV1",
    "dts": "DTS",
    "eac3": "E-AC-3",
    "flac": "FLAC",
    "h264": "H.264",
    "hevc": "HEVC",
    "mp2": "MP2",
    "mp3": "MP3",
    "mpeg1video": "MPEG-1",
    "mpeg2video": "MPEG-2",
    "mpeg4": "MPEG-4",
    "opus": "Opus",
    "prores": "ProRes",
    "theora": "Theora",
    "truehd": "TrueHD",
    "vc1": "VC-1",
    "vorbis": "Vorbis",
    "vp8": "VP8",
    "vp9": "VP9",
    "wmav1": "WMA",
    "wmav2": "WMA",
    "wmv1": "WMV",
    "wmv2": "WMV",
    "wmv3": "WMV9",
}


def display_codec_name(name: object) -> str:
    """Return a compact display name, preserving unknown codec identifiers."""
    if not isinstance(name, str) or not name.strip():
        return ""
    normalized = name.strip().casefold()
    if normalized.startswith("pcm_"):
        return "PCM"
    return _CODEC_NAMES.get(normalized, name.strip().upper())
