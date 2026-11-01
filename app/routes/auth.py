import re
from urllib.parse import unquote

from flask import Blueprint, redirect, render_template, request, url_for
from ..i18n import flash
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from ..services.authentication import authenticate

from .. import db
from ..models import User

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(email) > 255 or len(password) > 1024:
            flash("Email ou palavra-passe inválidos.", "error")
            return render_template("auth/login.html"), 400
        try:
            user, locked = authenticate(email, password)
        except SQLAlchemyError:
            db.session.rollback()
            flash("Não foi possível iniciar sessão. Tente novamente.", "error")
            return render_template("auth/login.html"), 503
        if locked:
            flash("Demasiadas tentativas falhadas. Tente novamente daqui a 15 minutos.", "error")
            return render_template("auth/login.html"), 429
        if user:
            login_user(user, remember=bool(request.form.get("remember")))
            next_url = request.args.get("next", "")
            # Reject ambiguous network paths before parsing can fail or normalize them.
            decoded_next = unquote(next_url)
            if (not decoded_next.startswith('/') or decoded_next.startswith('//')
                    or '\\' in decoded_next or any(ord(c) < 32 for c in decoded_next)):
                next_url = url_for("dashboard.index")
            return redirect(next_url)
        flash("Email ou palavra-passe inválidos.", "error")
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sessão terminada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not current_user.check_password(current):
                flash("A palavra-passe atual está incorreta.", "error")
            elif not 12 <= len(new) <= 1024:
                flash("A nova palavra-passe deve ter entre 12 e 1024 caracteres.", "error")
            elif new != confirm:
                flash("As palavras-passe não coincidem.", "error")
            else:
                current_user.set_password(new)
                db.session.commit()
                login_user(current_user, remember=False, fresh=True)
                flash("Palavra-passe alterada.", "success")
        elif action == "profile":
            name = request.form.get("name", "").strip()
            color = request.form.get("color", "")
            if not name or len(name) > 120:
                flash("Indique um nome entre 1 e 120 caracteres.", "error")
                return render_template("auth/profile.html"), 400
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                flash("Escolha uma cor válida para o calendário.", "error")
                return render_template("auth/profile.html"), 400
            current_user.name, current_user.color = name, color
            db.session.commit()
            flash("Perfil atualizado.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html")
