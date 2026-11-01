import os
import secrets
from pathlib import Path
from datetime import timedelta
from zoneinfo import ZoneInfo

import click
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate, upgrade
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.engine import URL
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from alembic.script import ScriptDirectory
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_overrides=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    database_url = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "bs-manager.db")
    )
    if not os.environ.get("DATABASE_URL") and os.environ.get("DATABASE_HOST"):
        database_url = URL.create(
            "postgresql+psycopg", username=os.environ["DATABASE_USER"],
            password=os.environ["DATABASE_PASSWORD"], host=os.environ["DATABASE_HOST"],
            database=os.environ.get("DATABASE_NAME", "bsmanager"),
        ).render_as_string(hide_password=False)
    # Usar o driver psycopg 3 também para URLs "postgres://" ou "postgresql://" (Render, Railway, etc.).
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            database_url = "postgresql+psycopg://" + database_url[len(prefix):]

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        MAX_CONTENT_LENGTH=128 * 1024,
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_DURATION=timedelta(days=7),
        REMEMBER_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        APP_TIMEZONE=os.environ.get("APP_TIMEZONE", "Europe/Lisbon"),
        COMPANY_NAME=os.environ.get("COMPANY_NAME", "BS Manager"),
        DEFAULT_VACATION_DAYS=int(os.environ.get("DEFAULT_VACATION_DAYS", "22")),
        # Feriados extra (municipais, tolerâncias), formato "MM-DD", separados por vírgula.
        EXTRA_HOLIDAYS=os.environ.get("EXTRA_HOLIDAYS", ""),
    )
    if config_overrides:
        app.config.update(config_overrides)

    secret_key = app.config["SECRET_KEY"]
    if not secret_key and (app.debug or app.testing):
        # Development and test sessions use an ephemeral key, never a public default.
        secret_key = app.config["SECRET_KEY"] = secrets.token_hex(32)
    if not isinstance(secret_key, (str, bytes)) or len(secret_key.strip()) < 32:
        raise RuntimeError(
            "Set SECRET_KEY to a randomly generated value of at least 32 characters "
            "before starting the application."
        )

    ZoneInfo(app.config["APP_TIMEZONE"])
    db.init_app(app)
    migrate.init_app(app, db, directory=str(Path(app.root_path).parent / "migrations"))
    csrf.init_app(app)
    from . import i18n
    i18n.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicie sessão para continuar."
    login_manager.localize_callback = i18n.gettext
    login_manager.login_message_category = "info"

    from . import models  # noqa: F401
    from .routes import admin, attendance, auth, calendar, dashboard, leave, tasks

    for module in (auth, dashboard, attendance, tasks, leave, calendar, admin):
        app.register_blueprint(module.bp)

    from .utils import register_template_helpers

    register_template_helpers(app)
    _register_error_handlers(app)

    _register_cli(app)

    @app.after_request
    def response_security(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Cache-Control'] = 'no-store'
        # Inline template scripts/styles remain in the prototype UI; external
        # calendar assets are served locally. No third-party connections required.
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.get("/health/ready")
    def readiness():
        try:
            with db.engine.connect() as connection:
                current = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
            expected = set(ScriptDirectory(str(Path(app.root_path).parent / "migrations")).get_heads())
            ready = current == expected
        except SQLAlchemyError:
            ready = False
        return {"status": "ok" if ready else "not-ready"}, 200 if ready else 503, {"Cache-Control": "no-store"}

    return app


def _bootstrap_admin(app):
    """Cria o primeiro administrador a partir de ADMIN_EMAIL/ADMIN_PASSWORD se não houver utilizadores."""
    from .models import User

    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email and not password:
        return
    if not email or not email.strip() or not password or len(password) < 12:
        raise click.ClickException("Set both ADMIN_EMAIL and an ADMIN_PASSWORD of at least 12 characters, or leave both empty.")
    if db.session.query(User.id).first():
        return
    admin = User(
        name=os.environ.get("ADMIN_NAME", "Administrador"), email=email.strip().lower(),
        is_admin=True, vacation_days=app.config["DEFAULT_VACATION_DAYS"],
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    app.logger.info("Initial administrator created.")


def _register_error_handlers(app):
    from flask import render_template

    messages = {
        403: "Não tem permissão para aceder a esta página.",
        404: "A página que procura não existe.",
        400: "Pedido inválido. Atualize a página e tente novamente.",
    }
    for code, message in messages.items():
        app.register_error_handler(
            code, lambda e, c=code, m=message: (render_template("error.html", code=c, message=m), c)
        )


def _register_cli(app):
    from .models import User

    @app.cli.command("init-db")
    def init_db():
        """Apply migrations and optionally create the first administrator from ADMIN_* settings."""
        upgrade()
        _bootstrap_admin(app)
        click.echo("Database initialized at the latest migration.")

    @app.cli.command("reset-password")
    @click.option("--email", prompt="Email")
    @click.password_option()
    def reset_password(email, password):
        """Operator recovery: reset an existing account and revoke all sessions."""
        if not 12 <= len(password) <= 1024:
            raise click.ClickException('Use a password of 12–1024 characters.')
        user = User.query.filter_by(email=email.strip().lower()).first()
        if user is None:
            raise click.ClickException('Account not found.')
        user.set_password(password)
        from .models import LoginThrottle
        import hashlib
        bucket = db.session.get(LoginThrottle, hashlib.sha256(user.email.encode()).hexdigest())
        if bucket:
            from .attendance_time import utc_now
            bucket.failures, bucket.blocked_until, bucket.window_start = 0, None, utc_now()
        db.session.commit()
        click.echo('Password reset; existing sessions revoked. Account activation unchanged.')

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Nome")
    @click.option("--email", prompt="Email")
    @click.password_option()
    def create_admin(name, email, password):
        """Cria (ou promove) um utilizador administrador."""
        email = email.strip().lower()
        if not name.strip() or len(name.strip()) > 120 or '@' not in email or len(email) > 255 or not 12 <= len(password) <= 1024:
            raise click.ClickException('Provide a valid name/email and a password of 12–1024 characters.')
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(name=name, email=email, vacation_days=app.config["DEFAULT_VACATION_DAYS"])
            db.session.add(user)
        user.is_admin = True
        user.active = True
        user.set_password(password)
        db.session.commit()
        click.echo(f"Administrador {email} pronto.")
