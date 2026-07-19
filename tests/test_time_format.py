import pytest

from mediacraft.utils.time_format import format_time


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00:00"),
        (-1, "00:00:00"),
        (65.9, "00:01:05"),
        (3754, "01:02:34"),
    ],
)
def test_format_time(seconds: float, expected: str) -> None:
    assert format_time(seconds) == expected
