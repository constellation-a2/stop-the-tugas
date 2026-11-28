"""Date and time helpers for the application's WIB business rules."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def now_wib() -> datetime:
    """Return the current time as a timezone-aware WIB datetime."""
    return datetime.now(WIB)


def to_wib(value: datetime) -> datetime:
    """Interpret a naive datetime as WIB or convert an aware datetime to WIB."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=WIB)
    return value.astimezone(WIB)


def parse_date(value: str | date) -> date:
    """Parse an ISO date string, or return an existing date."""
    if isinstance(value, datetime):
        raise TypeError("Expected a date without a time component.")
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Date must use the YYYY-MM-DD format.") from exc


def parse_time(value: str | time) -> time:
    """Parse an ISO local time without a timezone offset."""
    if isinstance(value, time):
        parsed = value
    else:
        try:
            parsed = time.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Time must use a valid ISO time format.") from exc
    if parsed.tzinfo is not None and parsed.utcoffset() is not None:
        raise ValueError("Time must be local and must not include a timezone.")
    return parsed


def parse_datetime(value: str | datetime) -> datetime:
    """Parse an ISO datetime and return it normalized to WIB.

    Datetimes without an offset are interpreted as WIB.
    """
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Datetime must use a valid ISO format.") from exc
    return to_wib(parsed)


def format_date(value: date) -> str:
    """Format a date using ISO YYYY-MM-DD notation."""
    return value.isoformat()


def format_time(value: time) -> str:
    """Format a local time using ISO notation."""
    return value.replace(tzinfo=None).isoformat()


def format_datetime(value: datetime) -> str:
    """Format a datetime as an ISO string with its WIB offset."""
    return to_wib(value).isoformat()


def time_until(target: datetime, now: datetime | None = None) -> timedelta:
    """Return the signed duration from now until a target datetime."""
    current_time = to_wib(now) if now is not None else now_wib()
    return to_wib(target) - current_time
