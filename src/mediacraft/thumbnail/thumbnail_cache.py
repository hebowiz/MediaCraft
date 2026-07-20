from collections import OrderedDict

from PySide6.QtGui import QImage


class ThumbnailCache:
    """A small least-recently-used cache for decoded preview images."""

    def __init__(self, maximum_size: int = 48) -> None:
        if maximum_size < 1:
            raise ValueError("maximum_size must be at least 1")
        self._maximum_size = maximum_size
        self._images: OrderedDict[int, QImage] = OrderedDict()

    def get(self, key: int) -> QImage | None:
        image = self._images.get(key)
        if image is None:
            return None
        self._images.move_to_end(key)
        return image

    def put(self, key: int, image: QImage) -> None:
        self._images[key] = image
        self._images.move_to_end(key)
        while len(self._images) > self._maximum_size:
            self._images.popitem(last=False)

    def get_nearest(
        self,
        key: int,
        maximum_distance: int,
    ) -> tuple[int, QImage] | None:
        if not self._images:
            return None
        nearest_key = min(self._images, key=lambda candidate: abs(candidate - key))
        if abs(nearest_key - key) > maximum_distance:
            return None
        image = self._images[nearest_key]
        self._images.move_to_end(nearest_key)
        return nearest_key, image

    def clear(self) -> None:
        self._images.clear()

    def __len__(self) -> int:
        return len(self._images)
