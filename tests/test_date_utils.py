from apple_health_transmitter.date_utils import parse_apple_date


def test_parse_negative_offset() -> None:
    result = parse_apple_date("2025-01-15 07:58:00 -0500")
    assert result == "2025-01-15T12:58:00+00:00"


def test_parse_positive_offset() -> None:
    result = parse_apple_date("2025-01-15 07:58:00 +0300")
    assert result == "2025-01-15T04:58:00+00:00"


def test_parse_utc() -> None:
    result = parse_apple_date("2025-01-15 12:00:00 +0000")
    assert result == "2025-01-15T12:00:00+00:00"


def test_parse_midnight() -> None:
    result = parse_apple_date("2025-01-15 00:00:00 -0500")
    assert result == "2025-01-15T05:00:00+00:00"


def test_date_ordering_after_parse() -> None:
    earlier = parse_apple_date("2025-01-10 08:00:00 -0500")
    later = parse_apple_date("2025-01-15 08:00:00 -0500")
    assert earlier < later
