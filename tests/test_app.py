from datetime import date, datetime, timedelta

import pytest

from app import create_app, db
from app.holidays import easter, holidays, is_working_day
from app.models import Event, LeaveRequest, TaskEntry, User, WorkSession


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
    })
    with app.app_context():
        db.create_all()
        admin = User(name="Ana Admin", email="admin@ex.pt", is_admin=True, vacation_days=22)
        admin.set_password("password123")
        worker = User(name="Rui Colaborador", email="rui@ex.pt", vacation_days=22)
        worker.set_password("password123")
        db.session.add_all([admin, worker])
        db.session.commit()
    yield app


def login(client, email="rui@ex.pt", password="password123"):
    return client.post("/login", data={"email": email, "password": password})


@pytest.fixture
def worker(app):
    client = app.test_client()
    login(client)
    return client


@pytest.fixture
def admin(app):
    client = app.test_client()
    login(client, "admin@ex.pt")
    return client


def test_holidays():
    assert easter(2026) == date(2026, 4, 5)
    assert easter(2027) == date(2027, 3, 28)
    h = holidays(2026)
    assert date(2026, 4, 3) in h  # Sexta-feira Santa
    assert date(2026, 6, 4) in h  # Corpo de Deus
    assert not is_working_day(date(2026, 12, 25))
    assert not is_working_day(date(2026, 10, 31))  # sábado
    assert is_working_day(date(2026, 10, 28))


def test_login_required_and_bad_login(app):
    client = app.test_client()
    assert client.get("/").status_code == 302
    resp = login(client, password="wrong")
    assert "inválidos" in resp.get_data(as_text=True)


def test_open_redirect_blocked(app):
    client = app.test_client()
    resp = client.post("/login?next=//evil.com", data={"email": "rui@ex.pt", "password": "password123"})
    assert resp.headers["Location"] == "/"


def test_clock_in_out(app, worker):
    assert worker.get("/").status_code == 200
    worker.post("/picagens/entrada")
    worker.post("/picagens/entrada")  # duplicado é ignorado
    with app.app_context():
        assert WorkSession.query.count() == 1
        assert WorkSession.query.first().end is None
    worker.post("/picagens/saida", data={"note": "fim"})
    with app.app_context():
        s = WorkSession.query.first()
        assert s.end is not None and s.note == "fim"
    assert worker.get("/picagens/").status_code == 200
    csv = worker.get("/picagens/exportar").get_data(as_text=True)
    assert "Rui Colaborador" in csv


def test_worker_cannot_edit_sessions(worker):
    assert worker.get("/picagens/nova").status_code == 403
    assert worker.get("/admin/utilizadores").status_code == 403


def test_admin_manual_session(app, admin):
    with app.app_context():
        rui = User.query.filter_by(email="rui@ex.pt").one()
    resp = admin.post("/picagens/nova", data={
        "user_id": rui.id, "start": "2026-10-01T09:00", "end": "2026-10-01T13:30", "note": "esqueceu-se",
    })
    assert resp.status_code == 302
    with app.app_context():
        s = WorkSession.query.one()
        assert s.hours == 4.5 and s.edited_by_id is not None
    page = admin.get(f"/picagens/?user={rui.id}&mes=2026-10").get_data(as_text=True)
    assert "4h30" in page


def test_tasks_crud_and_permissions(app, worker, admin):
    worker.post("/tarefas/nova", data={
        "date": "2026-10-27", "title": "Relatório", "project": "Cliente X", "hours": "2,5", "description": "x",
    })
    with app.app_context():
        task = TaskEntry.query.one()
        assert task.hours == 2.5
        task_id = task.id
    assert "Relatório" in worker.get("/tarefas/?mes=2026-10").get_data(as_text=True)
    assert "Relatório" in admin.get("/tarefas/?mes=2026-10").get_data(as_text=True)

    other = admin  # admin pode editar; outro colaborador não
    with app.app_context():
        u = User(name="Outro", email="o@ex.pt")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    c = app.test_client()
    login(c, "o@ex.pt")
    assert c.post(f"/tarefas/{task_id}/apagar").status_code == 403
    assert "Relatório" not in c.get("/tarefas/?mes=2026-10").get_data(as_text=True)
    assert other.post(f"/tarefas/{task_id}/apagar").status_code == 302
    with app.app_context():
        assert TaskEntry.query.count() == 0


def test_leave_flow(app, worker, admin):
    # 2026-12-21 (seg) a 2026-12-31 (qui): 8 dias úteis (25 de dezembro é feriado)
    worker.post("/ferias/pedir", data={"kind": "ferias", "start_date": "2026-12-21", "end_date": "2026-12-31"})
    with app.app_context():
        leave = LeaveRequest.query.one()
        assert leave.working_days() == 8
        assert leave.user.vacation_balance(2026) == 14
        leave_id = leave.id

    # Sobreposição é recusada
    worker.post("/ferias/pedir", data={"kind": "falta", "start_date": "2026-12-30"})
    with app.app_context():
        assert LeaveRequest.query.count() == 1

    # Colaborador não pode aprovar
    assert worker.post(f"/ferias/{leave_id}/rever", data={"decision": "aprovar"}).status_code == 403
    admin.post(f"/ferias/{leave_id}/rever", data={"decision": "aprovar"})
    with app.app_context():
        assert db.session.get(LeaveRequest, leave_id).status == LeaveRequest.APPROVED

    events = admin.get("/calendario/eventos?start=2026-12-01&end=2027-01-01").get_json()
    assert any("Rui Colaborador" in e["title"] for e in events)
    assert any(e["title"].endswith("Natal") for e in events)


def test_leave_insufficient_balance(app, worker):
    worker.post("/ferias/pedir", data={"kind": "ferias", "start_date": "2026-01-05", "end_date": "2026-03-31"})
    with app.app_context():
        assert LeaveRequest.query.count() == 0


def test_pending_leave_hidden_from_colleagues(app, worker):
    worker.post("/ferias/pedir", data={"kind": "ferias", "start_date": "2026-11-16", "end_date": "2026-11-17"})
    with app.app_context():
        u = User(name="Outro", email="o@ex.pt")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    c = app.test_client()
    login(c, "o@ex.pt")
    events = c.get("/calendario/eventos?start=2026-11-01&end=2026-12-01").get_json()
    assert not any("Rui" in e["title"] for e in events)


def test_calendar_events(app, worker):
    worker.post("/calendario/evento", data={"title": "Reunião", "start": "2026-11-03T10:00", "end": "2026-11-03T11:00"})
    worker.post("/calendario/evento", data={"title": "Offsite", "all_day": "1", "start_date": "2026-11-05", "end_date": "2026-11-06"})
    events = worker.get("/calendario/eventos?start=2026-11-01&end=2026-12-01").get_json()
    titles = {e["title"]: e for e in events}
    assert titles["Reunião"]["start"] == "2026-11-03T10:00:00"
    assert titles["Offsite"]["end"] == "2026-11-07"
    assert worker.get("/calendario/").status_code == 200
    with app.app_context():
        assert Event.query.count() == 2


def test_admin_user_management(app, admin):
    resp = admin.post("/admin/utilizadores/novo", data={
        "name": "Nova Pessoa", "email": "Nova@Ex.pt", "password": "segredo123", "vacation_days": "25", "active": "1",
    })
    assert resp.status_code == 302
    c = app.test_client()
    assert login(c, "nova@ex.pt", "segredo123").status_code == 302
    assert c.get("/").status_code == 200

    # Admin não se pode despromover a si próprio
    with app.app_context():
        me = User.query.filter_by(email="admin@ex.pt").one()
    admin.post(f"/admin/utilizadores/{me.id}", data={"name": "Ana", "email": "admin@ex.pt", "active": "1", "vacation_days": "22"})
    with app.app_context():
        assert db.session.get(User, me.id).is_admin


def test_inactive_user_cannot_login(app):
    with app.app_context():
        u = User.query.filter_by(email="rui@ex.pt").one()
        u.active = False
        db.session.commit()
    c = app.test_client()
    login(c)
    assert c.get("/").status_code == 302


def test_all_pages_render(admin):
    for url in ["/", "/picagens/", "/tarefas/", "/tarefas/nova", "/ferias/", "/calendario/",
                "/admin/utilizadores", "/admin/utilizadores/novo", "/perfil", "/picagens/nova"]:
        assert admin.get(url).status_code == 200, url


def test_login_lockout_after_repeated_failures(app):
    from app.routes import auth

    auth._failures.clear()
    client = app.test_client()
    for _ in range(auth.MAX_FAILURES):
        login(client, password="errada")
    resp = login(client)  # palavra-passe certa, mas bloqueado
    assert resp.status_code == 429
    assert client.get("/").status_code == 302
    auth._failures.clear()
    assert login(client).status_code == 302
