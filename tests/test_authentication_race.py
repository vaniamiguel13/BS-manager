import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from flask_migrate import upgrade

from app import create_app, db
from app.models import User
from app.routes import auth
from app.services import authentication


PASSWORD = 'synthetic-initial-password'
NEW_PASSWORD = 'synthetic-updated-password'


@pytest.fixture
def race_app(database_url):
    app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False,
                      'SQLALCHEMY_DATABASE_URI': database_url})
    with app.app_context():
        upgrade()
        user = User(name='Synthetic employee', email='employee@example.invalid')
        user.set_password(PASSWORD)
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.mark.parametrize('change', ['password', 'role', 'deactivate_reactivate'])
@pytest.mark.parametrize('remember', [False, True])
def test_change_after_verification_revokes_pending_login(race_app, monkeypatch, change, remember):
    original_login = auth.login_user
    changed = False

    def change_before_login(principal, **kwargs):
        nonlocal changed
        if not changed:
            changed = True
            user = User.query.filter_by(email='employee@example.invalid').one()
            if change == 'password':
                user.set_password(NEW_PASSWORD)
            else:
                if change == 'role':
                    user.is_admin = True
                else:
                    user.active = False
                user.session_token = secrets.token_hex(32)
            db.session.commit()
            if change == 'deactivate_reactivate':
                user.active = True
                user.session_token = secrets.token_hex(32)
                db.session.commit()
        return original_login(principal, **kwargs)

    monkeypatch.setattr(auth, 'login_user', change_before_login)
    client = race_app.test_client()
    data = {'email': 'employee@example.invalid', 'password': PASSWORD}
    if remember:
        data['remember'] = '1'
    assert client.post('/login', data=data).status_code == 302
    assert client.get('/').status_code == 302
    if remember:
        client.delete_cookie('session')
        assert client.get('/').status_code == 302

    fresh = race_app.test_client()
    data['password'] = NEW_PASSWORD if change == 'password' else PASSWORD
    assert fresh.post('/login', data=data).status_code == 302
    assert fresh.get('/').status_code == 200


def test_postgres_reset_during_password_verification_revokes_pending_login(race_app, monkeypatch):
    with race_app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('PostgreSQL transaction concurrency')

    verifying = Event()
    reset_finished = Event()
    original_check = authentication.check_password_hash

    def paused_check(password_hash, password):
        valid = original_check(password_hash, password)
        verifying.set()
        if not reset_finished.wait(timeout=10):
            raise TimeoutError('Password reset did not finish')
        return valid

    monkeypatch.setattr(authentication, 'check_password_hash', paused_check)

    def pending_login():
        client = race_app.test_client()
        response = client.post('/login', data={'email': 'employee@example.invalid',
                                               'password': PASSWORD, 'remember': '1'})
        return client, response.status_code

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(pending_login)
        try:
            assert verifying.wait(timeout=10)
            with race_app.app_context():
                user = User.query.filter_by(email='employee@example.invalid').one()
                user.set_password(NEW_PASSWORD)
                db.session.commit()
        finally:
            reset_finished.set()
        client, status = pending.result(timeout=10)

    assert status == 302
    assert client.get('/').status_code == 302
    client.delete_cookie('session')
    assert client.get('/').status_code == 302
    monkeypatch.setattr(authentication, 'check_password_hash', original_check)
    fresh = race_app.test_client()
    assert fresh.post('/login', data={'email': 'employee@example.invalid', 'password': NEW_PASSWORD}).status_code == 302
    assert fresh.get('/').status_code == 200
