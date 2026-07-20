from PySide6.QtGui import QImage

from mediacraft.thumbnail.thumbnail_cache import ThumbnailCache


def make_image(color: int) -> QImage:
    image = QImage(2, 2, QImage.Format.Format_RGB32)
    image.fill(color)
    return image


def test_cache_evicts_least_recently_used_image() -> None:
    cache = ThumbnailCache(maximum_size=2)
    first = make_image(0xFF0000)
    second = make_image(0x00FF00)
    third = make_image(0x0000FF)

    cache.put(1, first)
    cache.put(2, second)
    assert cache.get(1) is first
    cache.put(3, third)

    assert cache.get(1) is first
    assert cache.get(2) is None
    assert cache.get(3) is third
    assert len(cache) == 2


def test_cache_can_be_cleared() -> None:
    cache = ThumbnailCache()
    cache.put(1, make_image(0xFFFFFF))

    cache.clear()

    assert len(cache) == 0
    assert cache.get(1) is None


def test_cache_returns_nearest_image_within_limit() -> None:
    cache = ThumbnailCache()
    first = make_image(0x111111)
    second = make_image(0x222222)
    cache.put(1_000, first)
    cache.put(5_000, second)

    assert cache.get_nearest(4_200, 1_000) == (5_000, second)
    assert cache.get_nearest(3_000, 1_000) is None
