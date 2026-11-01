"""UTC timestamp and local-calendar helpers for attendance reporting."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context
from .i18n import gettext as _


UTC = timezone.utc


def _timezone_name(timezone_name: str | None = None) -> str:
    if timezone_name is not None:
        return timezone_name
    if has_app_context():
        return current_app.config.get("APP_TIMEZONE", "Europe/Lisbon")
    return "Europe/Lisbon"


def utc_now() -> datetime:
    """Return the current UTC instant, retaining microsecond precision."""
    return datetime.now(UTC)


def to_local(value: datetime, timezone_name: str | None = None) -> datetime:
    """Convert an aware instant to the configured local timezone."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("value must be a timezone-aware datetime")
    return value.astimezone(ZoneInfo(_timezone_name(timezone_name)))


def local_to_utc(
    value: str | datetime,
    fold: int | None = None,
    timezone_name: str | None = None,
) -> datetime:
    """Convert an ISO datetime or local wall time to an aware UTC datetime.

    Naive wall times in a daylight-saving gap are rejected. Repeated wall times
    require ``fold=0`` (earlier occurrence) or ``fold=1`` (later occurrence).
    ISO strings carrying an offset already identify an instant and are converted
    directly to UTC.
    """
    if fold not in (None, 0, 1):
        raise ValueError("fold must be 0, 1, or None")
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(_("Indique uma data e hora válidas.")) from exc
    if not isinstance(value, datetime):
        raise TypeError("value must be an ISO datetime string or datetime")
    if value.tzinfo is not None and value.utcoffset() is not None:
        return value.astimezone(UTC)

    zone = ZoneInfo(_timezone_name(timezone_name))
    candidates: list[tuple[int, datetime]] = []
    for candidate_fold in (0, 1):
        local = value.replace(tzinfo=zone, fold=candidate_fold)
        instant = local.astimezone(UTC)
        roundtrip = instant.astimezone(zone)
        if roundtrip.replace(tzinfo=None) == value:
            candidates.append((candidate_fold, instant))

    unique_instants = {instant for _, instant in candidates}
    if not unique_instants:
        raise ValueError(_("{value} does not exist in {zone}", value=value.isoformat(), zone=_timezone_name(timezone_name)))
    if len(unique_instants) > 1:
        if fold is None:
            raise ValueError(
                _("{value} is ambiguous in {zone}; specify fold=0 or fold=1", value=value.isoformat(), zone=_timezone_name(timezone_name))
            )
        return next(instant for candidate_fold, instant in candidates if candidate_fold == fold)
    return next(iter(unique_instants))


def period_bounds(firstdate: date, followingdate: date) -> tuple[datetime, datetime]:
    """Return local-midnight period boundaries as aware UTC instants."""
    if not isinstance(firstdate, date) or isinstance(firstdate, datetime):
        raise TypeError("firstdate must be a date")
    if not isinstance(followingdate, date) or isinstance(followingdate, datetime):
        raise TypeError("followingdate must be a date")
    if followingdate <= firstdate:
        raise ValueError("followingdate must be after firstdate")
    return (
        local_to_utc(datetime.combine(firstdate, time.min), fold=0),
        local_to_utc(datetime.combine(followingdate, time.min), fold=0),
    )


@dataclass(frozen=True)
class AttendanceSlice:
    session: object
    start: datetime
    end: datetime
    day: date
    duration: timedelta
    hours: float
    is_open: bool


def split_sessions(
    sessions: Iterable[object],
    firstdate: date,
    followingdate: date,
    at: datetime | None = None,
) -> list[AttendanceSlice]:
    """Clip sessions to local calendar days in [firstdate, followingdate).

    Session ``start`` and non-null ``end`` attributes must be aware datetimes.
    Open sessions are clipped at one captured ``at`` instant; closed sessions
    retain their recorded end even when that end is after ``at``.
    """
    period_start, period_end = period_bounds(firstdate, followingdate)
    captured_at = utc_now() if at is None else _as_utc(at, "at")
    zone = ZoneInfo(_timezone_name())
    slices: list[AttendanceSlice] = []

    for session in sessions:
        if getattr(session, "voided_at", None) is not None:
            continue
        start = _as_utc(getattr(session, "start"), "session.start")
        original_end = getattr(session, "end", None)
        is_open_session = original_end is None
        end = captured_at if is_open_session else _as_utc(original_end, "session.end")
        clipped_start = max(start, period_start)
        clipped_end = min(end, period_end)
        if clipped_end <= clipped_start:
            continue

        cursor = clipped_start
        while cursor < clipped_end:
            local_cursor = cursor.astimezone(zone)
            day = local_cursor.date()
            next_day = day + timedelta(days=1)
            day_end = local_to_utc(datetime.combine(next_day, time.min), fold=0)
            segment_end = min(clipped_end, day_end)
            duration = segment_end - cursor
            if duration > timedelta(0):
                slices.append(
                    AttendanceSlice(
                        session=session,
                        start=cursor,
                        end=segment_end,
                        day=day,
                        duration=duration,
                        hours=duration.total_seconds() / 3600,
                        is_open=is_open_session and segment_end == captured_at,
                    )
                )
            cursor = segment_end

    slices.sort(key=lambda item: (item.start, item.day))
    return slices


def _as_utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value.astimezone(UTC)
