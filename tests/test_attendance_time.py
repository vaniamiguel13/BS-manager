from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from flask import Flask

from app.attendance_time import local_to_utc, period_bounds, split_sessions, to_local, utc_now


UTC = timezone.utc


def dt(value):
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def app_with_timezone(name):
    app = Flask(__name__)
    app.config["APP_TIMEZONE"] = name
    return app


def test_utc_now_is_aware_utc_with_microseconds():
    value = utc_now()
    assert value.tzinfo is UTC
    assert 0 <= value.microsecond < 1_000_000


def test_to_local_uses_app_timezone_and_rejects_naive_input():
    with app_with_timezone("America/New_York").app_context():
        assert to_local(dt("2026-01-01T12:00:00")) == datetime(
            2026, 1, 1, 7, tzinfo=ZoneInfo("America/New_York")
        )
    with pytest.raises(ValueError, match="aware"):
        to_local(datetime(2026, 1, 1))


@pytest.mark.parametrize("fold, expected", [(0, "2026-10-25T00:30:00+00:00"), (1, "2026-10-25T01:30:00+00:00")])
def test_local_to_utc_selects_explicit_occurrence_for_ambiguous_time(fold, expected):
    assert local_to_utc("2026-10-25T01:30:00", fold=fold) == datetime.fromisoformat(expected)


def test_local_to_utc_requires_fold_for_ambiguous_and_rejects_nonexistent():
    with pytest.raises(ValueError, match="ambiguous.*fold=0.*fold=1"):
        local_to_utc(datetime(2026, 10, 25, 1, 30))
    with pytest.raises(ValueError, match="does not exist"):
        local_to_utc("2026-03-29T01:30:00")


def test_local_to_utc_accepts_explicit_offset_and_unambiguous_wall_time():
    assert local_to_utc("2026-01-01T12:00:00+02:00") == dt("2026-01-01T10:00:00")
    assert local_to_utc(datetime(2026, 1, 1, 12)) == dt("2026-01-01T12:00:00")


def test_period_bounds_are_local_midnights_across_spring_dst():
    start, end = period_bounds(date(2026, 3, 29), date(2026, 3, 30))
    assert start == dt("2026-03-29T00:00:00")
    assert end == dt("2026-03-29T23:00:00")
    assert end - start == timedelta(hours=23)
    autumn_start, autumn_end = period_bounds(date(2026, 10, 25), date(2026, 10, 26))
    assert autumn_end - autumn_start == timedelta(hours=25)


def test_split_sessions_slices_overnight_and_excludes_exact_midnight_endpoint():
    session = SimpleNamespace(start=dt("2026-01-31T23:30:00"), end=dt("2026-02-01T00:30:00"), voided_at=None)
    result = split_sessions([session], date(2026, 1, 31), date(2026, 2, 2))
    assert [(part.day, part.duration) for part in result] == [
        (date(2026, 1, 31), timedelta(minutes=30)),
        (date(2026, 2, 1), timedelta(minutes=30)),
    ]
    assert all(part.session is session and not part.is_open for part in result)
    ending_at_boundary = SimpleNamespace(start=dt("2026-01-31T23:00:00"), end=dt("2026-02-01T00:00:00"), voided_at=None)
    january = split_sessions([ending_at_boundary], date(2026, 1, 31), date(2026, 2, 1))
    assert len(january) == 1 and january[0].day == date(2026, 1, 31)
    assert january[0].duration == timedelta(hours=1)


def test_split_sessions_crosses_year_boundary():
    session = SimpleNamespace(start=dt("2025-12-31T23:30:00"), end=dt("2026-01-01T00:30:00"), voided_at=None)
    result = split_sessions([session], date(2025, 12, 31), date(2026, 1, 2))
    assert [part.day for part in result] == [date(2025, 12, 31), date(2026, 1, 1)]
    assert all(part.duration == timedelta(minutes=30) for part in result)


def test_split_sessions_handles_25_hour_dst_day_and_voided_rows():
    session = SimpleNamespace(start=dt("2026-10-24T22:30:00"), end=dt("2026-10-25T02:30:00"), voided_at=None)
    voided = SimpleNamespace(start=dt("2026-10-25T00:00:00"), end=dt("2026-10-25T02:00:00"), voided_at=dt("2026-10-26T00:00:00"))
    result = split_sessions([session, voided], date(2026, 10, 25), date(2026, 10, 26))
    assert len(result) == 1
    assert result[0].day == date(2026, 10, 25)
    assert result[0].duration == timedelta(hours=3, minutes=30)
    assert result[0].hours == 3.5


def test_open_session_clips_once_at_now_and_marks_only_final_segment():
    session = SimpleNamespace(start=dt("2026-01-01T23:30:00"), end=None, voided_at=None)
    at = dt("2026-01-02T00:15:00")
    result = split_sessions([session], date(2026, 1, 1), date(2026, 1, 3), at=at)
    assert [part.duration for part in result] == [timedelta(minutes=30), timedelta(minutes=15)]
    assert [part.is_open for part in result] == [False, True]
    assert all(part.end.tzinfo is UTC for part in result)


def test_closed_future_session_is_not_clipped_to_now_and_period_is_half_open():
    future = SimpleNamespace(start=dt("2026-01-02T00:00:00"), end=dt("2026-01-02T02:00:00"), voided_at=None)
    at = dt("2026-01-01T12:00:00")
    result = split_sessions([future], date(2026, 1, 2), date(2026, 1, 3), at=at)
    assert len(result) == 1 and result[0].duration == timedelta(hours=2)
    assert not result[0].is_open
    with pytest.raises(ValueError, match="aware"):
        split_sessions([SimpleNamespace(start=datetime(2026, 1, 2), end=None)], date(2026, 1, 2), date(2026, 1, 3), at=at)


def test_app_timezone_context_controls_period_boundaries():
    with app_with_timezone("America/New_York").app_context():
        start, end = period_bounds(date(2026, 1, 1), date(2026, 1, 2))
    assert start == dt("2026-01-01T05:00:00")
    assert end == dt("2026-01-02T05:00:00")
