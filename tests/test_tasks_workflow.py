import csv
import io
from datetime import date

import pytest
from flask_migrate import upgrade
from sqlalchemy import select

from app import create_app, db
from app.models import TaskEntry, User


ADMIN_PASSWORD = "synthetic-admin-password"
WORKER_PASSWORD = "synthetic-worker-password"


@pytest.fixture
def task_app(database_url):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "synthetic-test-secret-key-with-32-characters",
        "SQLALCHEMY_DATABASE_URI": database_url,
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
    assert client.post("/login", data={"email": email, "password": password}).status_code == 302
    return client


def task_form(**overrides):
    form = {"date": "2026-03-10", "project": "Synthetic Project", "title": "Synthetic task",
            "description": "Synthetic detail", "hours": "1.5"}
    form.update(overrides)
    return form


def add_task(user_id, **overrides):
    values = {"date": date(2026, 3, 10), "project": "Synthetic Project", "title": "Synthetic task",
              "description": "Synthetic detail", "hours": 1.5}
    values.update(overrides)
    task = TaskEntry(user_id=user_id, **values)
    db.session.add(task)
    db.session.commit()
    return task.id


def test_employee_crud_own_scope_and_project_suggestions_are_private(task_app):
    app, ids = task_app
    with app.app_context():
        own_id = add_task(ids["worker"], project="Worker Private Project")
        add_task(ids["other"], project="Other Private Project")
    client = login(app, "worker@example.invalid", WORKER_PASSWORD)

    index = client.get("/tarefas/?mes=2026-03")
    assert b"Worker Private Project" in index.data
    assert b"Other Private Project" not in index.data
    create_page = client.get("/tarefas/nova")
    assert b"Worker Private Project" in create_page.data
    assert b"Other Private Project" not in create_page.data

    assert client.get(f"/tarefas/{own_id}/editar").status_code == 200
    assert client.post("/tarefas/nova", data=task_form(project="Own new project")).status_code == 302
    with app.app_context():
        created = db.session.scalar(select(TaskEntry).where(TaskEntry.title == "Synthetic task", TaskEntry.project == "Own new project"))
        assert created.user_id == ids["worker"]

    assert client.post(f"/tarefas/{own_id}/editar", data=task_form(title="Updated by worker")).status_code == 302
    with app.app_context():
        assert db.session.get(TaskEntry, own_id).title == "Updated by worker"
    assert client.post(f"/tarefas/{own_id}/apagar").status_code == 302
    with app.app_context():
        assert db.session.get(TaskEntry, own_id) is None


def test_employee_cannot_read_modify_delete_or_export_other_employee_tasks(task_app):
    app, ids = task_app
    with app.app_context():
        other_id = add_task(ids["other"], project="Other Confidential Project", title="Other Confidential Task",
                            description="other-private-sentinel")
        add_task(ids["worker"], project="Own Project", title="Own Task", description="own-sentinel")
    client = login(app, "worker@example.invalid", WORKER_PASSWORD)

    assert client.get(f"/tarefas/{other_id}/editar").status_code == 403
    assert client.post(f"/tarefas/{other_id}/editar", data=task_form(title="Tampered")).status_code == 403
    assert client.post(f"/tarefas/{other_id}/apagar").status_code == 403
    index = client.get("/tarefas/?mes=2026-03&user=" + str(ids["other"]))
    assert b"other-private-sentinel" not in index.data and b"Other Confidential Project" not in index.data
    exported = client.get("/tarefas/exportar?mes=2026-03&user=" + str(ids["other"]))
    assert exported.status_code == 200
    assert b"other-private-sentinel" not in exported.data and b"Other Confidential Task" not in exported.data


def test_admin_filters_users_projects_and_can_create_for_selected_employee(task_app):
    app, ids = task_app
    with app.app_context():
        add_task(ids["worker"], project="Worker Project", title="Worker entry")
        add_task(ids["other"], project="Other Project", title="Other entry")
    client = login(app, "admin@example.invalid", ADMIN_PASSWORD)

    all_rows = client.get("/tarefas/?mes=2026-03")
    assert b"Worker entry" in all_rows.data and b"Other entry" in all_rows.data
    filtered = client.get("/tarefas/?mes=2026-03&user=" + str(ids["worker"]) + "&projeto=Worker%20Project")
    assert b"Worker entry" in filtered.data and b"Other entry" not in filtered.data
    create_page = client.get("/tarefas/nova")
    assert b"Worker Project" in create_page.data and b"Other Project" in create_page.data
    assert client.post("/tarefas/nova", data=task_form(user_id="999999")).status_code == 400
    assert client.post("/tarefas/nova", data=task_form(user_id=str(ids["other"]), title="Admin entered")).status_code == 302
    with app.app_context():
        record = db.session.scalar(select(TaskEntry).where(TaskEntry.title == "Admin entered"))
        assert record.user_id == ids["other"]


@pytest.mark.parametrize("form", [
    task_form(date=""), task_form(date="not-a-date"), task_form(hours="NaN"), task_form(hours="Infinity"),
    task_form(hours="-0.1"), task_form(hours="24.1"), task_form(title=" "),
    task_form(description="x" * 10001), task_form(project="x" * 121), task_form(title="x" * 201),
])
def test_invalid_worklog_fields_return_400_and_preserve_submission(task_app, form):
    app, _ = task_app
    client = login(app, "worker@example.invalid", WORKER_PASSWORD)
    response = client.post("/tarefas/nova", data=form)
    assert response.status_code == 400
    assert form.get("project", "Synthetic Project").encode()[:80] in response.data
    with app.app_context():
        assert db.session.scalar(select(db.func.count()).select_from(TaskEntry)) == 0


def test_admin_edit_redirects_to_updated_employee_and_month(task_app):
    app, ids = task_app
    with app.app_context():
        task_id = add_task(ids["worker"], date=date(2026, 2, 1))
    client = login(app, "admin@example.invalid", ADMIN_PASSWORD)
    response = client.post(f"/tarefas/{task_id}/editar", data=task_form(user_id=str(ids["other"]), date="2026-04-30"))
    assert response.status_code == 302
    from urllib.parse import urlsplit, parse_qs
    redirect = parse_qs(urlsplit(response.headers['Location']).query)
    assert redirect == {'mes': ['2026-04'], 'user': [str(ids['other'])]}
    with app.app_context():
        updated = db.session.get(TaskEntry, task_id)
        assert updated.user_id == ids["other"] and updated.date == date(2026, 4, 30)


def test_export_filters_and_formula_escapes_all_user_text_and_disables_caching(task_app):
    app, ids = task_app
    with app.app_context():
        add_task(ids["worker"], project="=2+2", title="+cmd", description="@SUM(1,1)")
        add_task(ids["other"], project="Other Project", title="Other task", description="-unsafe")
    admin = login(app, "admin@example.invalid", ADMIN_PASSWORD)
    all_response = admin.get("/tarefas/exportar?mes=2026-03")
    assert all_response.headers["Cache-Control"] == "no-store"
    rows = list(csv.reader(io.StringIO(all_response.data.decode("utf-8-sig")), delimiter=";"))
    exported_rows = {row[3]: row for row in rows[1:]}
    assert exported_rows["'+cmd"][2:5] == ["'=2+2", "'+cmd", "'@SUM(1,1)"]
    assert exported_rows["Other task"][4] == "'-unsafe"

    worker = login(app, "worker@example.invalid", WORKER_PASSWORD)
    filtered = worker.get("/tarefas/exportar?mes=2026-03&projeto=%3D2%2B2")
    filtered_rows = list(csv.reader(io.StringIO(filtered.data.decode("utf-8-sig")), delimiter=";"))
    assert len(filtered_rows) == 2
    assert filtered_rows[1][2:5] == ["'=2+2", "'+cmd", "'@SUM(1,1)"]


@pytest.mark.parametrize('value', ['0001-01-01', '1899-12-31', '9999-01-01'])
def test_task_rejects_dates_outside_readable_reports(task_app, value):
    app, ids = task_app
    client = login(app, 'worker@example.invalid', WORKER_PASSWORD)
    assert client.post('/tarefas/nova', data=task_form(date=value)).status_code == 400
    with app.app_context():
        assert TaskEntry.query.count() == 0
