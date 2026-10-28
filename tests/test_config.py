from pathlib import Path

import pytest

from app import create_app


@pytest.fixture
def config(tmp_path, monkeypatch):
    for name in ("SECRET_KEY", "ADMIN_EMAIL", "ADMIN_PASSWORD", "FLASK_DEBUG"):
        monkeypatch.delenv(name, raising=False)
    return {
        "DEBUG": False,
        "TESTING": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'config.db'}",
    }


@pytest.mark.parametrize("key", [None, "", " " * 64, "dev-change-me", "too-short"])
def test_production_rejects_missing_or_unsafe_secret(config, monkeypatch, key):
    if key is not None:
        monkeypatch.setenv("SECRET_KEY", key)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config)


def test_production_uses_configured_secret_and_keeps_csrf_enabled(config, monkeypatch):
    key = "synthetic-configuration-test-key-1234567890"
    monkeypatch.setenv("SECRET_KEY", key)
    app = create_app(config)
    assert app.secret_key == key
    assert app.test_client().post("/login", data={}).status_code == 400


def test_explicit_config_can_supply_secret(config):
    key = b"synthetic-config-override-test-key-1234567890"
    app = create_app({**config, "SECRET_KEY": key})
    assert app.secret_key == key


@pytest.mark.parametrize("mode", ["DEBUG", "TESTING"])
def test_development_and_tests_get_independent_ephemeral_keys(config, mode):
    first = create_app({**config, mode: True})
    second = create_app({**config, mode: True})
    assert len(first.secret_key) >= 32
    assert first.secret_key != second.secret_key


def test_public_default_cannot_sign_an_admin_session(config):
    from flask import Flask

    from app import db
    from app.models import User

    app = create_app({**config, "TESTING": True})
    with app.app_context():
        admin = User(name="Synthetic admin", email="admin@example.invalid", is_admin=True)
        admin.set_password("synthetic-test-password")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    old_config = Flask("public-default")
    old_config.secret_key = "dev-change-me"
    signer = old_config.session_interface.get_signing_serializer(old_config)
    cookie = signer.dumps({"_user_id": str(admin_id), "_fresh": True})
    client = app.test_client()
    client.set_cookie("session", cookie)
    assert client.get("/admin/utilizadores").status_code == 302


def test_documented_debug_cli_starts_without_configured_secret(config, monkeypatch):
    from click.testing import CliRunner
    from flask.cli import cli

    captured = {}

    def capture_server(host, port, application, **kwargs):
        captured["app"] = application

    monkeypatch.setattr("flask.cli.run_simple", capture_server)
    monkeypatch.setenv("DATABASE_URL", config["SQLALCHEMY_DATABASE_URI"])
    # Track restoration of the variable that Flask's debug option changes.
    monkeypatch.setenv("FLASK_DEBUG", "0")
    wsgi_path = Path(__file__).resolve().parents[1] / "wsgi.py"
    result = CliRunner().invoke(cli, ["--app", str(wsgi_path), "run", "--debug", "--no-reload"])
    assert result.exit_code == 0, result.output
    assert captured["app"].debug
    assert len(captured["app"].secret_key) >= 32
