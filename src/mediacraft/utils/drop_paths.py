from pathlib import Path

from PySide6.QtCore import QMimeData


def local_drop_paths(mime_data: QMimeData) -> list[str]:
    if not mime_data.hasUrls():
        return []
    return [
        str(Path(url.toLocalFile()))
        for url in mime_data.urls()
        if url.isLocalFile() and Path(url.toLocalFile()).exists()
    ]
