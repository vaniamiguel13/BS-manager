import time
from collections import defaultdict
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .. import db
from ..models import User

bp = Blueprint("auth", __name__)

# Proteção contra tentativas repetidas: após MAX_FAILURES falhas para o mesmo email,
# o login fica bloqueado durante LOCKOUT_SECONDS. Guardado em memória (um só processo).
MAX_FAILURES = 10
LOCKOUT_SECONDS = 15 * 60
_failures = defaultdict(list)


def _is_locked(email):
    cutoff = time.monotonic() - LOCKOUT_SECONDS
    _failures[email] = [t for t in _failures[email] if t > cutoff]
    return len(_failures[email]) >= MAX_FAILURES


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if _is_locked(email):
            flash("Demasiadas tentativas falhadas. Tente novamente daqui a 15 minutos.", "error")
            return render_template("auth/login.html"), 429
        user = User.query.filter_by(email=email).first()
        if user and user.active and user.check_password(password):
            _failures.pop(email, None)
            login_user(user, remember=bool(request.form.get("remember")))
            next_url = request.args.get("next", "")
            # Só aceitar redirecionamentos internos.
            if not next_url.startswith("/") or urlparse(next_url).netloc:
                next_url = url_for("dashboard.index")
            return redirect(next_url)
        _failures[email].append(time.monotonic())
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
            elif len(new) < 8:
                flash("A nova palavra-passe deve ter pelo menos 8 caracteres.", "error")
            elif new != confirm:
                flash("As palavras-passe não coincidem.", "error")
            else:
                current_user.set_password(new)
                db.session.commit()
                flash("Palavra-passe alterada.", "success")
        elif action == "profile":
            name = request.form.get("name", "").strip()
            color = request.form.get("color", "")
            if name:
                current_user.name = name
            if len(color) == 7 and color.startswith("#"):
                current_user.color = color
            db.session.commit()
            flash("Perfil atualizado.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html")
