import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

from app import create_app, db
from app.models import User

TABLES = {"user", "work_session", "task_entry", "leave_request", "event", "attendance_audit", "leave_audit", "leave_allowance", "login_throttle"}


@pytest.fixture
def app(database_url):
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": database_url})


def test_app_startup_does_not_create_schema_or_seed_admin(database_url, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.invalid")
    monkeypatch.setenv("ADMIN_PASSWORD", "synthetic-test-password")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": database_url})
    with app.app_context():
        assert inspect(db.engine).get_table_names() == []


def test_initial_schema_matches_models_and_repeated_upgrades_preserve_data(app):
    with app.app_context():
        upgrade()
        assert set(inspect(db.engine).get_table_names()) == TABLES | {"alembic_version"}
        assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003_staff"
        user = User(name="Synthetic employee", email="staff@example.invalid")
        user.set_password("synthetic-test-password")
        db.session.add(user)
        db.session.commit()
        upgrade()
        assert User.query.one().email == "staff@example.invalid"
    result = app.test_cli_runner().invoke(args=["db", "check"])
    assert result.exit_code == 0, result.output


def test_migration_round_trip_on_disposable_database(app):
    with app.app_context():
        upgrade()
        downgrade(revision="base")
        assert not TABLES.intersection(inspect(db.engine).get_table_names())
        upgrade()
        assert TABLES.issubset(inspect(db.engine).get_table_names())


def test_init_db_bootstraps_admin_once_and_keeps_existing_password(app, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "ADMIN@example.invalid")
    monkeypatch.setenv("ADMIN_PASSWORD", "synthetic-first-password")
    runner = app.test_cli_runner()
    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        user = User.query.one()
        assert user.is_admin and user.email == "admin@example.invalid"
        assert user.check_password("synthetic-first-password")
    monkeypatch.setenv("ADMIN_PASSWORD", "synthetic-changed-password")
    assert runner.invoke(args=["init-db"]).exit_code == 0
    with app.app_context():
        assert User.query.one().check_password("synthetic-first-password")


def test_init_db_without_admin_settings_leaves_accounts_empty(app):
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert User.query.count() == 0


@pytest.mark.parametrize('email,password', [('admin@example.invalid', ''), ('', 'synthetic-valid-password'), ('admin@example.invalid', 'short')])
def test_init_db_rejects_incomplete_or_weak_bootstrap(app, monkeypatch, email, password):
    monkeypatch.setenv('ADMIN_EMAIL', email)
    monkeypatch.setenv('ADMIN_PASSWORD', password)
    result = app.test_cli_runner().invoke(args=['init-db'])
    assert result.exit_code != 0
    with app.app_context():
        assert User.query.count() == 0
