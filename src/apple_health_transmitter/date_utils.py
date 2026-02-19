from datetime import UTC, datetime


def parse_apple_date(date_str: str) -> str:
    """Convert Apple Health date format to ISO-8601 UTC string.

    Input:  "2025-01-15 07:58:00 -0500"
    Output: "2025-01-15T12:58:00+00:00"
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
    dt_utc = dt.astimezone(UTC)
    return dt_utc.isoformat()
