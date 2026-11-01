from datetime import datetime

import pytest
from flask_migrate import upgrade

from app import create_app, db
from app.models import Event, User


@pytest.fixture
def calendar_app(database_url):
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False,
                      'SQLALCHEMY_DATABASE_URI': database_url})
    with app.app_context():
        upgrade()
        for name in ('owner', 'colleague', 'admin'):
            user = User(name=name, email=name+'@example.invalid', is_admin=name == 'admin')
            user.set_password('synthetic-calendar-password')
            db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def login(app, name):
    client = app.test_client()
    assert client.post('/login', data={'email': name+'@example.invalid',
                                      'password': 'synthetic-calendar-password'}).status_code == 302
    return client


def add_event(app, client):
    assert client.post('/calendario/evento', data={
        'title': 'Original meeting', 'start': '2026-10-30T10:00:25',
        'end': '2026-10-30T11:00:25', 'description': 'Original description',
    }).status_code == 302
    with app.app_context():
        return Event.query.one().id


def test_event_owner_and_admin_can_edit_without_replacing_author(calendar_app):
    app = calendar_app
    owner, admin = login(app, 'owner'), login(app, 'admin')
    event_id = add_event(app, owner)
    path = f'/calendario/evento/{event_id}/editar'
    form = owner.get(path)
    assert form.status_code == 200
    assert '2026-10-30T10:00:25' in form.text
    assert owner.post(path, data={
        'title': 'Moved meeting', 'start': '2026-10-31T14:00', 'description': 'New description',
    }).status_code == 302
    assert admin.get(path).status_code == 200
    assert admin.post(path, data={
        'title': 'Team offsite', 'all_day': '1',
        'start_date': '2026-11-02', 'end_date': '2026-11-03',
    }).status_code == 302
    with app.app_context():
        record = Event.query.one()
        assert record.id == event_id and record.created_by.name == 'owner'
        assert record.all_day and record.end == datetime(2026, 11, 3)
    feed = owner.get('/calendario/eventos?start=2026-11-01&end=2026-12-01').json
    updated = next(event for event in feed if event.get('id') == event_id)
    assert updated['title'] == 'Team offsite' and updated['end'] == '2026-11-04'


def test_colleague_cannot_edit_or_delete_another_event(calendar_app):
    app = calendar_app
    owner, colleague = login(app, 'owner'), login(app, 'colleague')
    event_id = add_event(app, owner)
    path = f'/calendario/evento/{event_id}/editar'
    assert colleague.get(path).status_code == 403
    assert colleague.post(path, data={'title': 'Unauthorized'}).status_code == 403
    assert colleague.post(f'/calendario/evento/{event_id}/apagar').status_code == 403
    feed = colleague.get('/calendario/eventos?start=2026-10-01&end=2026-11-01').json
    assert next(event for event in feed if event.get('id') == event_id)['canEdit'] is False
    with app.app_context():
        assert Event.query.one().title == 'Original meeting'


def test_invalid_event_edit_preserves_inputs_and_original_record(calendar_app):
    app = calendar_app
    client = login(app, 'owner')
    event_id = add_event(app, client)
    response = client.post(f'/calendario/evento/{event_id}/editar', data={
        'title': 'Retained title', 'start': '2026-10-30T12:00',
        'end': '2026-10-30T11:00', 'description': 'Retained description',
    })
    assert response.status_code == 400
    assert 'Retained title' in response.text and 'Retained description' in response.text
    with app.app_context():
        record = Event.query.one()
        assert record.title == 'Original meeting' and record.start.hour == 10


@pytest.mark.parametrize('query', [
    'start=9999-12-31', 'start=bad&end=2026-11-01',
    'start=2026-10-01&end=bad', 'start=0001-01-01',
])
def test_invalid_calendar_range_is_a_client_error(calendar_app, query):
    assert login(calendar_app, 'owner').get('/calendario/eventos?'+query).status_code == 400


@pytest.mark.parametrize('path', ['/picagens/', '/picagens/exportar', '/tarefas/', '/tarefas/exportar'])
@pytest.mark.parametrize('month', ['9999-12', '0001-01'])
def test_out_of_range_report_month_is_a_client_error(calendar_app, path, month):
    assert login(calendar_app, 'owner').get(path+'?mes='+month).status_code == 400


@pytest.mark.parametrize('value', ['0001-01-02T10:00', '1899-12-31T10:00', '9999-01-01T10:00'])
def test_event_rejects_dates_outside_readable_calendar(calendar_app, value):
    client = login(calendar_app, 'owner')
    assert client.post('/calendario/evento', data={'title':'Out of range', 'start':value}).status_code == 400
    with calendar_app.app_context():
        assert Event.query.count() == 0


def test_calendar_reads_last_supported_day_with_exclusive_next_year(calendar_app):
    client = login(calendar_app, 'owner')
    assert client.post('/calendario/evento', data={'title':'Last supported day',
        'all_day':'1', 'start_date':'9998-12-31'}).status_code == 302
    response = client.get('/calendario/eventos?start=9998-12-01&end=9999-01-04')
    assert response.status_code == 200
    assert any(item['title'] == 'Last supported day' for item in response.json)
