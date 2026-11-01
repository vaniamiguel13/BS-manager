import csv
import io
from datetime import date, datetime, timezone

import pytest
from flask_migrate import upgrade
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import AttendanceAudit, User, WorkSession


UTC = timezone.utc
ADMIN_PASSWORD = "synthetic-admin-password"
WORKER_PASSWORD = "synthetic-worker-password"


@pytest.fixture
def workflow(database_url):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "synthetic-test-secret-key-with-32-characters",
        "SQLALCHEMY_DATABASE_URI": database_url,
        "APP_TIMEZONE": "Europe/Lisbon",
    })
    with app.app_context():
        upgrade()
        admin = User(name="Synthetic Admin", email="admin@example.invalid", is_admin=True)
        worker = User(name="Synthetic Worker", email="worker@example.invalid")
        other = User(name="Other Worker", email="other@example.invalid")
        admin.set_password(ADMIN_PASSWORD)
        worker.set_password(WORKER_PASSWORD)
        other.set_password(WORKER_PASSWORD)
        db.session.add_all([admin, worker, other])
        db.session.commit()
        ids = {"admin": admin.id, "worker": worker.id, "other": other.id}
    yield app, ids
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def login(app, email, password):
    client = app.test_client()
    response = client.post("/login", data={"email": email, "password": password})
    assert response.status_code == 302
    return client


def local_form(user_id, start="2026-01-10T09:00:00", end="2026-01-10T10:00:00", **extra):
    return {"user_id": str(user_id), "start": start, "end": end, "reason": "Synthetic correction", "note": "synthetic note", **extra}


def add_session(user_id, start, end, note="synthetic existing"):
    record = WorkSession(user_id=user_id, start=start, end=end, note=note)
    db.session.add(record)
    db.session.commit()
    return record.id


def test_admin_create_edit_void_preserves_audit_and_voided_row(workflow):
    app, ids = workflow
    client = login(app, "admin@example.invalid", ADMIN_PASSWORD)

    response = client.post("/picagens/nova", data=local_form(ids["worker"], reason=" "))
    assert response.status_code == 400
    with app.app_context():
        assert db.session.scalar(select(db.func.count()).select_from(WorkSession)) == 0

    response = client.post("/picagens/nova", data=local_form(ids["worker"]))
    assert response.status_code == 302
    with app.app_context():
        record = db.session.scalar(select(WorkSession))
        session_id = record.id
        assert record.start == datetime(2026, 1, 10, 9, tzinfo=UTC)
        assert record.end == datetime(2026, 1, 10, 10, tzinfo=UTC)
        assert record.version == 1

    missing_reason = local_form(ids["worker"], start="2026-01-10T09:30:00", end="2026-01-10T10:30:00", version="1", reason="")
    response = client.post(f"/picagens/{session_id}/editar", data=missing_reason)
    assert response.status_code == 400
    changed = local_form(ids["worker"], start="2026-01-10T09:30:00", end="2026-01-10T10:30:00", version="1", reason="Corrected clock time")
    response = client.post(f"/picagens/{session_id}/editar", data=changed)
    assert response.status_code == 302

    response = client.post(f"/picagens/{session_id}/apagar", data={"version": "2", "reason": "  "})
    assert response.status_code == 400
    with app.app_context():
        assert db.session.get(WorkSession, session_id).voided_at is None
    response = client.post(f"/picagens/{session_id}/apagar", data={"version": "2", "reason": "Duplicate entry"})
    assert response.status_code == 302

    with app.app_context():
        record = db.session.get(WorkSession, session_id)
        events = db.session.scalars(select(AttendanceAudit).where(AttendanceAudit.session_id == session_id).order_by(AttendanceAudit.id)).all()
        assert record is not None and record.voided_at.tzinfo is not None
        assert record.edited_by_id == ids["admin"] and record.version == 3
        assert [event.action for event in events] == ["manual", "correct", "void"]
        assert [event.actor_id for event in events] == [ids["admin"]] * 3
        assert events[0].reason == "Synthetic correction" and events[0].before is None
        assert events[0].after["start"].endswith("+00:00")
        assert events[1].reason == "Corrected clock time"
        assert events[1].before["version"] == 1 and events[1].after["version"] == 2
        assert events[1].after["start"] == "2026-01-10T09:30:00+00:00"
        assert events[2].reason == "Duplicate entry"
        assert events[2].before["version"] == 2 and events[2].after["version"] == 3
        assert events[2].after["voided_at"].endswith("+00:00")
        assert record.duration.total_seconds() > 0  # retained row remains inspectable
        assert record.voided_at is not None and record.end is not None
    index = client.get("/picagens/?user=" + str(ids["worker"]) + "&mes=2026-01")
    assert index.status_code == 200
    assert "Total do mês: <strong>0h00</strong>".encode() in index.data
    assert b"Picagens anuladas" in index.data
    assert client.get(f"/picagens/{session_id}/historico").status_code == 200


def test_invalid_end_overlap_and_stale_version_are_rejected(workflow):
    app, ids = workflow
    client = login(app, "admin@example.invalid", ADMIN_PASSWORD)
    invalid = local_form(ids["worker"], end="not-a-date")
    assert client.post("/picagens/nova", data=invalid).status_code == 400
    with app.app_context():
        assert db.session.scalar(select(db.func.count()).select_from(WorkSession)) == 0

    reversed_interval = local_form(ids["worker"], start="2026-01-10T10:00:00", end="2026-01-10T09:00:00")
    assert client.post("/picagens/nova", data=reversed_interval).status_code == 400
    assert client.post("/picagens/nova", data=local_form(ids["worker"], end="2026-01-10T10:30:00")).status_code == 302
    with app.app_context():
        original = db.session.scalar(select(WorkSession))
        session_id = original.id

    overlap = local_form(ids["worker"], start="2026-01-10T10:00:00", end="2026-01-10T11:00:00")
    assert client.post("/picagens/nova", data=overlap).status_code in (400, 409, 503)
    first_edit = local_form(ids["worker"], start="2026-01-10T08:00:00", end="2026-01-10T09:00:00", version="1", reason="first update")
    assert client.post(f"/picagens/{session_id}/editar", data=first_edit).status_code == 302
    stale = local_form(ids["worker"], start="2026-01-10T07:00:00", end="2026-01-10T08:00:00", version="1", reason="stale update")
    assert client.post(f"/picagens/{session_id}/editar", data=stale).status_code == 409
    with app.app_context():
        record = db.session.get(WorkSession, session_id)
        assert record.start == datetime(2026, 1, 10, 8, tzinfo=UTC)
        assert record.version == 2


def test_employee_cannot_manage_or_view_other_users_attendance(workflow):
    app, ids = workflow
    with app.app_context():
        add_session(ids["worker"], datetime(2026, 1, 10, 8, tzinfo=UTC), datetime(2026, 1, 10, 8, 30, tzinfo=UTC), "worker-only-sentinel")
        session_id = add_session(ids["other"], datetime(2026, 1, 10, 9, tzinfo=UTC), datetime(2026, 1, 10, 10, tzinfo=UTC), "other-only-sentinel")
    client = login(app, "worker@example.invalid", WORKER_PASSWORD)

    own_page = client.get(f"/picagens/?user={ids['other']}&mes=2026-01")
    assert own_page.status_code == 200
    assert b"Synthetic Worker" in own_page.data
    assert b"Other Worker" not in own_page.data
    assert b"other-only-sentinel" not in own_page.data
    assert b"worker-only-sentinel" in own_page.data
    own_csv = client.get(f"/picagens/exportar?user={ids['other']}&mes=2026-01")
    assert own_csv.status_code == 200
    assert b"other-only-sentinel" not in own_csv.data
    assert b"worker-only-sentinel" in own_csv.data
    assert b"Synthetic Worker" in own_csv.data

    assert client.get("/picagens/nova").status_code == 403
    assert client.post("/picagens/nova", data=local_form(ids["other"])).status_code == 403
    assert client.get(f"/picagens/{session_id}/editar").status_code == 403
    assert client.post(f"/picagens/{session_id}/editar", data=local_form(ids["other"], version="1")).status_code == 403
    assert client.get(f"/picagens/{session_id}/apagar").status_code == 403
    assert client.post(f"/picagens/{session_id}/apagar", data={"version": "1", "reason": "attempt"}).status_code == 403
    assert client.get(f"/picagens/{session_id}/historico").status_code == 403


def test_month_and_csv_slices_clip_overnight_at_inclusive_day_edges(workflow):
    app, ids = workflow
    with app.app_context():
        add_session(ids["worker"], datetime(2026, 1, 31, 23, 30, tzinfo=UTC), datetime(2026, 2, 1, 0, 30, tzinfo=UTC))
    client = login(app, "worker@example.invalid", WORKER_PASSWORD)

    january = client.get("/picagens/?mes=2026-01")
    february = client.get("/picagens/?mes=2026-02")
    assert "Total do mês: <strong>0h30</strong>".encode() in january.data
    assert b"31/01/2026" in january.data
    assert "Total do mês: <strong>0h30</strong>".encode() in february.data
    assert b"01/02/2026" in february.data

    jan_csv = client.get("/picagens/exportar?mes=2026-01").data.decode("utf-8-sig")
    feb_csv = client.get("/picagens/exportar?mes=2026-02").data.decode("utf-8-sig")
    jan_rows = list(csv.reader(io.StringIO(jan_csv), delimiter=";"))
    feb_rows = list(csv.reader(io.StringIO(feb_csv), delimiter=";"))
    assert jan_rows[1][1:4] == ["2026-01-31", "2026-01-31T23:30:00+00:00", "2026-02-01T00:00:00+00:00"]
    assert feb_rows[1][1:4] == ["2026-02-01", "2026-02-01T00:00:00+00:00", "2026-02-01T00:30:00+00:00"]


def test_dst_repeated_time_explicit_folds_roundtrip_through_http_and_csv(workflow):
    app, ids = workflow
    client = login(app, "admin@example.invalid", ADMIN_PASSWORD)
    form = local_form(
        ids["worker"], start="2026-10-25T01:30:00", end="2026-10-25T01:30:00",
        start_fold="0", end_fold="1", reason="DST repeated hour",
    )
    response = client.post("/picagens/nova", data=form)
    assert response.status_code == 302
    with app.app_context():
        record = db.session.scalar(select(WorkSession))
        assert record.start == datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
        assert record.end == datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
    page = client.get("/picagens/?user=" + str(ids["worker"]) + "&mes=2026-10")
    assert page.status_code == 200
    assert b"01:30:00 +0100" in page.data and b"01:30:00 +0000" in page.data
    assert b"1h00" in page.data
    exported = client.get("/picagens/exportar?mes=2026-10&user=" + str(ids["worker"])).data.decode("utf-8-sig")
    assert "2026-10-25T01:30:00+01:00" in exported
    assert "2026-10-25T01:30:00+00:00" in exported


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_audit_rows_are_immutable_at_database_level(workflow, operation):
    app, ids = workflow
    with app.app_context():
        session_id = add_session(ids["worker"], datetime(2026, 1, 10, 9, tzinfo=UTC), datetime(2026, 1, 10, 10, tzinfo=UTC))
        audit = AttendanceAudit(session_id=session_id, actor_id=ids["admin"], action="manual", reason="immutable test", before=None, after={"synthetic": True})
        db.session.add(audit)
        db.session.commit()
        audit_id = audit.id
        with pytest.raises(IntegrityError):
            if operation == "update":
                db.session.execute(db.update(AttendanceAudit).where(AttendanceAudit.id == audit_id).values(reason="tampered"))
            else:
                db.session.execute(db.delete(AttendanceAudit).where(AttendanceAudit.id == audit_id))
        db.session.rollback()
        assert db.session.get(AttendanceAudit, audit_id).reason == "immutable test"


def test_attendance_exports_escape_formulas_and_html_is_not_cached(workflow):
    app, ids = workflow
    with app.app_context():
        db.session.get(User, ids['worker']).name = '=SUM(1,2)'
        add_session(ids['worker'], datetime(2026, 1, 10, 9, tzinfo=UTC), datetime(2026, 1, 10, 10, tzinfo=UTC), '  @SUM(1,2)')
    client = login(app, 'worker@example.invalid', WORKER_PASSWORD)
    assert client.get('/picagens/?mes=2026-01').headers['Cache-Control'] == 'no-store'
    assert client.get('/').headers['Cache-Control'] == 'no-store'
    rows = list(csv.reader(io.StringIO(client.get('/picagens/exportar?mes=2026-01').data.decode('utf-8-sig')), delimiter=';'))
    assert rows[1][0].startswith("'=") and rows[1][-1].startswith("'  @")


def test_note_only_correction_does_not_round_clock_timestamp(workflow):
    app, ids = workflow
    with app.app_context():
        session_id = add_session(ids['worker'], datetime(2026, 1, 10, 9, 0, 0, 123456, tzinfo=UTC), datetime(2026, 1, 10, 10, 0, 0, 654321, tzinfo=UTC))
    client = login(app, 'admin@example.invalid', ADMIN_PASSWORD)
    assert client.get(f'/picagens/{session_id}/editar').status_code == 200
    response = client.post(f'/picagens/{session_id}/editar', data=local_form(ids['worker'], start='2026-01-10T09:00', end='2026-01-10T10:00', version='1', note='Only the note changed'))
    assert response.status_code == 302
    with app.app_context():
        record = db.session.get(WorkSession, session_id)
        assert record.start.microsecond == 123456 and record.end.microsecond == 654321


@pytest.mark.parametrize('start,end', [('2026-03-29T01:30:00', '2026-03-29T03:00:00'), ('2026-10-25T01:30:00', '2026-10-25T02:30:00')])
def test_admin_cannot_submit_dst_gap_or_unresolved_repeated_hour(workflow, start, end):
    app, ids = workflow
    client = login(app, 'admin@example.invalid', ADMIN_PASSWORD)
    assert client.post('/picagens/nova', data=local_form(ids['worker'], start=start, end=end)).status_code == 400
    with app.app_context():
        assert WorkSession.query.count() == AttendanceAudit.query.count() == 0


@pytest.mark.parametrize('unchanged', [True, False])
def test_edit_keeps_original_dst_occurrence_but_requires_choice_for_changed_hour(workflow, unchanged):
    app, ids = workflow
    original = datetime(2026, 10, 25, 1, 30, 0, 123456, tzinfo=UTC) if unchanged else datetime(2026, 1, 10, 9, tzinfo=UTC)
    with app.app_context():
        session_id = add_session(ids['worker'], original, datetime(2026, 10, 25, 2, 30, tzinfo=UTC))
    client = login(app, 'admin@example.invalid', ADMIN_PASSWORD)
    response = client.post(f'/picagens/{session_id}/editar', data=local_form(ids['worker'], start='2026-10-25T01:30:00', end='2026-10-25T02:30:00', version='1'))
    assert response.status_code == (302 if unchanged else 400)
    with app.app_context():
        assert db.session.get(WorkSession, session_id).start == original
        assert AttendanceAudit.query.count() == (1 if unchanged else 0)


@pytest.mark.parametrize('value', ['0001-01-02T09:00', '1899-12-31T09:00', '9999-01-01T09:00'])
def test_manual_attendance_rejects_dates_outside_readable_reports(workflow, value):
    app, ids = workflow
    client = login(app, 'admin@example.invalid', ADMIN_PASSWORD)
    response = client.post('/picagens/nova', data={'user_id':ids['worker'], 'start':value,
        'reason':'Range validation test'})
    assert response.status_code == 400
    with app.app_context():
        assert WorkSession.query.count() == AttendanceAudit.query.count() == 0
