import json
from datetime import date, datetime, time
from pathlib import Path

import pytest
from flask_migrate import upgrade

from app import create_app, db
from app.attendance_time import local_to_utc
from app.models import TaskEntry, User
from app.routes import dashboard
from app.services import attendance


PASSWORD = "synthetic-interface-password"


@pytest.fixture
def ui_app(database_url):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "synthetic-test-secret-key-with-32-characters",
        "SQLALCHEMY_DATABASE_URI": database_url,
    })
    with app.app_context():
        upgrade()
        users = {key: User(name=f"Synthetic {key}", email=f"{key}@example.invalid", is_admin=key == "admin")
                 for key in ("admin", "worker", "other")}
        for user in users.values():
            user.set_password(PASSWORD)
        db.session.add_all(users.values())
        db.session.commit()
        ids = {key: user.id for key, user in users.items()}
    yield app, ids
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def login(app, key):
    client = app.test_client()
    assert client.post("/login", data={"email": f"{key}@example.invalid", "password": PASSWORD}).status_code == 302
    return client


def add_session(ids, day, start, end):
    attendance.correct(ids["admin"], ids["worker"], local_to_utc(datetime.combine(day, start), fold=0),
                       local_to_utc(datetime.combine(day, end), fold=0), "", "Synthetic record.")
    db.session.commit()


def test_dashboard_week_chart_totals_each_local_day(ui_app):
    app, ids = ui_app
    with app.app_context():
        add_session(ids, date(2026, 3, 9), time(9), time(12, 30))
        add_session(ids, date(2026, 3, 10), time(9), time(11))
        add_session(ids, date(2026, 3, 2), time(9), time(17))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(dashboard, "today", lambda: date(2026, 3, 11))
        page = login(app, "worker").get("/").get_data(as_text=True)
    assert '<span class="week-value">3h30</span>' in page
    assert '<span class="week-value">2h00</span>' in page
    assert "5h30" in page
    assert "8h00" not in page
    assert page.count('class="week-value"') == 7


def test_clocked_in_indicator_follows_open_session(ui_app):
    app, _ = ui_app
    client = login(app, "worker")
    assert 'class="nav-live"' not in client.get("/tarefas/").get_data(as_text=True)
    assert client.post("/picagens/entrada").status_code == 302
    assert 'class="nav-live"' in client.get("/tarefas/").get_data(as_text=True)
    assert 'class="nav-live"' not in login(app, "other").get("/tarefas/").get_data(as_text=True)
    assert client.post("/picagens/saida").status_code == 302
    assert 'class="nav-live"' not in client.get("/tarefas/").get_data(as_text=True)


@pytest.mark.parametrize("target,expected", [
    ("/", "/"),
    ("https://example.invalid/", None),
    ("//example.invalid/", None),
    ("/\\example.invalid", None),
])
def test_quick_task_returns_only_to_local_pages(ui_app, target, expected):
    app, ids = ui_app
    client = login(app, "worker")
    response = client.post("/tarefas/nova", data={"date": "2026-03-10", "title": "Synthetic quick task",
                                                 "hours": "0.5", "project": "", "next": target})
    assert response.status_code == 302
    location = response.headers["Location"]
    if expected:
        assert location == expected
    else:
        assert location.startswith("/tarefas/") and "example.invalid" not in location
    with app.app_context():
        assert TaskEntry.query.filter_by(user_id=ids["worker"], title="Synthetic quick task").count() == 1


def test_duplicate_prefills_own_task_and_refuses_other_users(ui_app):
    app, ids = ui_app
    with app.app_context():
        own = TaskEntry(user_id=ids["worker"], date=date(2026, 3, 10), project="Synthetic Project",
                        title="Synthetic original", hours=1.5, description="Synthetic detail")
        foreign = TaskEntry(user_id=ids["other"], date=date(2026, 3, 10), project="Private Project",
                            title="Private original", hours=2)
        db.session.add_all([own, foreign])
        db.session.commit()
        own_id, foreign_id = own.id, foreign.id
    client = login(app, "worker")
    page = client.get(f"/tarefas/nova?de={own_id}").get_data(as_text=True)
    assert 'value="Synthetic original"' in page and 'value="Synthetic Project"' in page
    assert 'value="2026-03-10"' not in page
    assert client.get(f"/tarefas/nova?de={foreign_id}").status_code == 403
    assert client.get("/tarefas/nova?de=999999").status_code == 404
    assert login(app, "admin").get(f"/tarefas/nova?de={foreign_id}").status_code == 200
    with app.app_context():
        assert TaskEntry.query.count() == 2


def test_project_summary_counts_only_visible_tasks(ui_app):
    app, ids = ui_app
    with app.app_context():
        db.session.add_all([
            TaskEntry(user_id=ids["worker"], date=date(2026, 3, 10), project="Alpha", title="A", hours=1.5),
            TaskEntry(user_id=ids["worker"], date=date(2026, 3, 11), project="Alpha", title="B", hours=2),
            TaskEntry(user_id=ids["worker"], date=date(2026, 3, 11), project="", title="C", hours=0.5),
            TaskEntry(user_id=ids["other"], date=date(2026, 3, 10), project="Zeta other", title="D", hours=7),
            TaskEntry(user_id=ids["worker"], date=date(2026, 4, 1), project="Next month", title="E", hours=3),
        ])
        db.session.commit()
    page = login(app, "worker").get("/tarefas/?mes=2026-03").get_data(as_text=True)
    assert '<span class="project-name">Alpha</span>' in page and "3h30" in page
    assert '<span class="project-name">Sem projeto</span>' in page
    assert "Zeta other" not in page
    assert '<span class="project-name">Next month</span>' not in page
    assert "4h00" in page


def test_manifest_and_icons_are_served_and_linked(ui_app):
    app, _ = ui_app
    client = app.test_client()
    response = client.get("/static/manifest.webmanifest")
    assert response.status_code == 200
    assert response.mimetype == "application/manifest+json"
    manifest = json.loads(response.get_data(as_text=True))
    assert manifest["name"] == "Management" and manifest["display"] == "standalone" and manifest["start_url"] == "/"
    for icon in manifest["icons"]:
        image = client.get("/static/" + icon["src"])
        assert image.status_code == 200 and image.mimetype == "image/png"
        assert image.data[:8] == b"\x89PNG\r\n\x1a\n"
    login_page = client.get("/login").get_data(as_text=True)
    assert 'rel="manifest" href="/static/manifest.webmanifest" crossorigin="use-credentials"' in login_page
    assert 'rel="apple-touch-icon" href="/static/brand/icon-180.png"' in login_page
    assert "serviceWorker" not in login_page


def test_new_interface_strings_have_english_translations():
    catalog = json.loads((Path(__file__).resolve().parents[1] / "app/translations/templates.en.json").read_text())
    for source in ("A trabalhar", "Horas por dia", "Registo rápido de tarefa", "O que fez?", "Adicionar", "Fora hoje",
                   "A seguir", "Mês atual", "Dias trabalhados", "Média por dia", "Horas por projeto", "Sem projeto",
                   "Duplicar", "Seg", "Dom"):
        assert catalog.get(source) and catalog[source] != source, source
