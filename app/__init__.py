import os

import click
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_overrides=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    database_url = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "bs-manager.db")
    )
    # Usar o driver psycopg 3 também para URLs "postgres://" ou "postgresql://" (Render, Railway, etc.).
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            database_url = "postgresql+psycopg://" + database_url[len(prefix):]

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        REMEMBER_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        APP_TIMEZONE=os.environ.get("APP_TIMEZONE", "Europe/Lisbon"),
        COMPANY_NAME=os.environ.get("COMPANY_NAME", "BS Manager"),
        DEFAULT_VACATION_DAYS=int(os.environ.get("DEFAULT_VACATION_DAYS", "22")),
        # Feriados extra (municipais, tolerâncias), formato "MM-DD", separados por vírgula.
        EXTRA_HOLIDAYS=os.environ.get("EXTRA_HOLIDAYS", ""),
    )
    if config_overrides:
        app.config.update(config_overrides)

    if app.config["SECRET_KEY"] == "dev-change-me" and not app.debug and not app.testing:
        app.logger.warning("SECRET_KEY não definida! Defina-a antes de usar em produção.")

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicie sessão para continuar."
    login_manager.login_message_category = "info"

    from . import models  # noqa: F401
    from .routes import admin, attendance, auth, calendar, dashboard, leave, tasks

    for module in (auth, dashboard, attendance, tasks, leave, calendar, admin):
        app.register_blueprint(module.bp)

    from .utils import register_template_helpers

    register_template_helpers(app)
    _register_error_handlers(app)

    with app.app_context():
        db.create_all()
        _bootstrap_admin(app)

    _register_cli(app)
    return app


def _bootstrap_admin(app):
    """Cria o primeiro administrador a partir de ADMIN_EMAIL/ADMIN_PASSWORD se não houver utilizadores."""
    from .models import User

    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password or db.session.query(User.id).first():
        return
    admin = User(
        name=os.environ.get("ADMIN_NAME", "Administrador"),
        email=email.strip().lower(),
        is_admin=True,
        vacation_days=app.config["DEFAULT_VACATION_DAYS"],
    )
    admin.set_password(password)
    db.session.add(admin)
    try:
        db.session.commit()
    except IntegrityError:
        # Outro processo (worker) criou-o ao mesmo tempo.
        db.session.rollback()
        return
    app.logger.info("Administrador inicial criado: %s", admin.email)


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

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Nome")
    @click.option("--email", prompt="Email")
    @click.password_option()
    def create_admin(name, email, password):
        """Cria (ou promove) um utilizador administrador."""
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(name=name, email=email, vacation_days=app.config["DEFAULT_VACATION_DAYS"])
            db.session.add(user)
        user.is_admin = True
        user.active = True
        user.set_password(password)
        db.session.commit()
        click.echo(f"Administrador {email} pronto.")
