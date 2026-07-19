import pytest

from mediacraft.utils.time_format import format_time, format_time_millis


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


def test_format_time_millis_uses_three_decimal_places() -> None:
    assert format_time_millis(3661.2346) == "01:01:01.235"
    assert format_time_millis(-1) == "00:00:00.000"
