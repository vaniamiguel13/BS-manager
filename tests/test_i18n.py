"""Locale selection must preserve authentication, privacy and entered records."""
import re
from datetime import date, datetime

import pytest
from flask_migrate import upgrade

from app import create_app, db
from app.models import Event, LeaveRequest, TaskEntry, User

PASSWORD = 'synthetic-language-password'


@pytest.fixture
def localized_app(database_url):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': database_url})
    with app.app_context():
        upgrade()
        for name in ('admin', 'employee'):
            user = User(name=name, email=name+'@example.invalid', is_admin=name == 'admin')
            user.set_password(PASSWORD)
            db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def csrf(client, path='/login'):
    response = client.get(path, follow_redirects=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text)[1]


def switch(client, language, target='/'):
    return client.post('/language', data={'language': language, 'next': target,
                                        'csrf_token': csrf(client)})


def login(client, name='employee'):
    return client.post('/login', data={'email': name+'@example.invalid', 'password': PASSWORD,
                                      'csrf_token': csrf(client)})


def test_login_copy_and_persistent_language_before_and_after_login(localized_app):
    client = localized_app.test_client()
    response = client.get('/login')
    assert '<html lang="pt-PT">' in response.text
    assert 'Gestão da equipa' in response.text
    assert 'espaçoda' not in response.text
    assert '<h1>Gestão da equipa</h1>' in response.text
    response = switch(client, 'en', '/login?next=/ferias/')
    assert response.location == '/login?next=/ferias/'
    cookie = response.headers['Set-Cookie']
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie and 'Max-Age=31536000' in cookie
    response = client.get(response.location)
    assert '<html lang="en">' in response.text and 'Team workspace' in response.text
    assert 'Content-Language' in response.headers and response.headers['Content-Language'] == 'en'
    assert 'Cookie' in response.headers['Vary']
    assert 'Sign in to continue.' in client.get('/ferias/', follow_redirects=True).text
    assert login(client).status_code == 302
    assert 'Sign out' in client.get('/').text
    assert 'Sign in' not in client.get('/').text
    assert switch(client, 'pt', '/ferias/?ano=2026').location == '/ferias/?ano=2026'
    assert 'Férias e ausências' in client.get('/ferias/?ano=2026').text
    assert 'Terminar sessão' in client.get('/').text


def test_language_form_requires_csrf_and_rejects_unsupported_choice(localized_app):
    client = localized_app.test_client()
    assert client.get('/language').status_code == 405
    assert client.post('/language', data={'language': 'en'}).status_code == 400
    response = switch(client, 'fr')
    assert response.status_code == 400
    assert 'bs_language' not in response.headers.get('Set-Cookie', '')
    client.set_cookie('bs_language', 'fr')
    assert 'Gestão da equipa' in client.get('/login').text
    localized_app.config['SESSION_COOKIE_SECURE'] = True
    assert 'Secure' in switch(client, 'en').headers['Set-Cookie']


def test_language_redirect_is_local_only(localized_app):
    client = localized_app.test_client()
    for target in ('https://external.invalid', '//external.invalid', '/%2fexternal.invalid',
                   '/\\external.invalid', '/%5cexternal.invalid', '/%0d%0aLocation:x', 'relative'):
        assert switch(client, 'en', target).location == '/'
    assert switch(client, 'en', '/tarefas/?mes=2026-11&projeto=Test').location == '/tarefas/?mes=2026-11&projeto=Test'


def test_english_pages_messages_calendar_and_privacy(localized_app):
    client = localized_app.test_client()
    switch(client, 'en')
    assert login(client, 'admin').status_code == 302
    for path, label in [('/', 'Hello, admin'), ('/picagens/?mes=2026-11', 'November 2026'),
                        ('/tarefas/?mes=2026-11', 'Work logs'), ('/ferias/', 'Leave balance'),
                        ('/calendario/', 'Team calendar'), ('/perfil', 'Current password'),
                        ('/admin/utilizadores', 'Users'), ('/admin/utilizadores/novo', 'New user')]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert label in response.text, (path, label)
        assert 'Sign out' in response.text
    response = client.post('/perfil', data={'action': 'password', 'current_password': 'wrong',
        'new_password': PASSWORD, 'confirm_password': PASSWORD, 'csrf_token': csrf(client, '/perfil')}, follow_redirects=True)
    assert 'The current password is incorrect.' in response.text
    response = client.post('/ferias/prever', data={'kind':'ferias','start_date':'bad',
        'csrf_token':csrf(client, '/ferias/')})
    assert response.status_code == 400 and response.json['error'] == 'Choose a valid leave type and date range.'
    response = client.get('/tarefas/exportar?mes=2026-11')
    assert response.status_code == 200 and 'Employee;Date;Project;Work log;Description;Hours' in response.text
    response = client.get('/picagens/exportar?mes=2026-11')
    assert response.status_code == 200 and 'Employee;Date;Clock-in;Clock-out;Hours;Note' in response.text
    # The language switch on a validation error must return to a GET page.
    response = client.post('/ferias/pedir', data={'kind': 'ferias', 'start_date': 'bad',
        'csrf_token': csrf(client, '/ferias/')})
    assert response.status_code == 400
    assert 'name="next" value="/ferias/"' in response.text
    response = client.get('/calendario/eventos?start=2026-12-01&end=2027-01-01')
    assert any(event['title'] == '🎉 Christmas' for event in response.json)
    # Locale does not grant administrator access to an employee.
    other = localized_app.test_client()
    switch(other, 'en')
    login(other)
    assert other.get('/admin/utilizadores').status_code == 403
    assert 'You do not have permission' in other.get('/admin/utilizadores').text


def test_records_are_not_translated_or_written_by_language_change(localized_app):
    with localized_app.app_context():
        employee = User.query.filter_by(name='employee').one()
        admin = User.query.filter_by(name='admin').one()
        employee_id = employee.id
        db.session.add_all([
            TaskEntry(user_id=employee.id, date=date(2026,11,2), title='Férias',
                      project='Projeto português', description='<script>Notas privadas</script>', hours=2),
            Event(created_by_id=employee.id, title='Férias', start=datetime(2026,11,2,10),
                  description='Reunião em português'),
            LeaveRequest(user_id=admin.id, kind='baixa', start_date=date(2026,12,21),
                         end_date=date(2026,12,21), status='aprovado', reason='Private medical detail'),
        ])
        db.session.commit()
    client = localized_app.test_client()
    login(client)
    switch(client, 'en')
    response = client.get('/tarefas/?mes=2026-11')
    assert 'Férias' in response.text and 'Projeto português' in response.text
    assert '&lt;script&gt;Notas privadas&lt;/script&gt;' in response.text
    events = client.get('/calendario/eventos?start=2026-12-01&end=2027-01-01').json
    assert any(event['title'] == 'admin – Unavailable' for event in events)
    assert 'Private medical detail' not in str(events) and 'Medical leave' not in str(events)
    for language in ('pt', 'en'):
        switch(client, language)
    with localized_app.app_context():
        assert TaskEntry.query.count() == Event.query.count() == LeaveRequest.query.count() == 1
        assert db.session.get(User, employee_id).name == 'employee'
        assert TaskEntry.query.one().title == Event.query.one().title == 'Férias'


def test_english_leave_history_translates_system_values_and_preserves_notes(localized_app):
    client = localized_app.test_client()
    switch(client, 'en')
    login(client, 'admin')
    response = client.post('/ferias/pedir', data={'kind':'formacao', 'start_date':'2026-12-21',
        'reason':'Formação', 'csrf_token':csrf(client, '/ferias/')}, follow_redirects=True)
    assert 'Request submitted (1 working day). Awaiting approval.' in response.text
    with localized_app.app_context():
        record = LeaveRequest.query.one()
        record_id, version = record.id, record.version
    response = client.post(f'/ferias/{record_id}/rever', data={'decision':'aprovar',
        'version':version, 'review_note':'Decisão original', 'csrf_token':csrf(client, '/ferias/')})
    assert response.status_code == 302
    response = client.get(f'/ferias/{record_id}/historico')
    assert response.status_code == 200
    assert 'Approved' in response.text and 'Pending' in response.text and 'Training' in response.text
    assert 'Formação' in response.text and 'Decisão original' in response.text
    switch(client, 'pt')
    assert 'Aprovado' in client.get(f'/ferias/{record_id}/historico').text
