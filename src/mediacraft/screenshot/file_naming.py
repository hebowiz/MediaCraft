from datetime import datetime
from pathlib import Path


SUPPORTED_FORMATS = {"png": ".png", "jpeg": ".jpg"}


def build_screenshot_path(
    directory: str | Path,
    media_path: str | Path,
    frame_number: int,
    image_format: str,
    *,
    captured_at: datetime | None = None,
) -> Path:
    extension = SUPPORTED_FORMATS.get(image_format.lower())
    if extension is None:
        raise ValueError(f"未対応のスクリーンショット形式です: {image_format}")

    frame_text = f"{frame_number:06d}" if frame_number >= 0 else "unknown"
    timestamp = (captured_at or datetime.now()).strftime("%Y%m%d_%H%M%S")
    filename = f"{Path(media_path).stem}_frame{frame_text}_{timestamp}{extension}"
    return Path(directory).expanduser() / filename
