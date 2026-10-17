"""Time helpers.

Times are stored in UTC without a timezone attached (SQLite can't keep one),
and the API always returns them in UTC with a "Z" on the end.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    """Convert an incoming time to the stored form (UTC, no timezone).

    A time sent without a timezone is assumed to already be UTC.
    """
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)


def to_utc(dt: datetime | None) -> datetime | None:
    """Mark a stored (naive UTC) time as UTC so it serializes with "Z"."""
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
