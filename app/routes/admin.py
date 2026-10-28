from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import User
from ..utils import admin_required, today

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/utilizadores")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.active.desc(), User.name).all()
    return render_template("admin/users.html", users=all_users, year=today().year)


@bp.route("/utilizadores/novo", methods=["GET", "POST"])
@bp.route("/utilizadores/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id=None):
    user = db.get_or_404(User, user_id) if user_id else None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        is_admin = bool(request.form.get("is_admin"))
        active = bool(request.form.get("active"))
        try:
            vacation_days = int(request.form.get("vacation_days", ""))
        except ValueError:
            vacation_days = current_app.config["DEFAULT_VACATION_DAYS"]

        clash = User.query.filter(User.email == email, User.id != (user.id if user else 0)).first()
        errors = []
        if not name or "@" not in email:
            errors.append("Indique um nome e um email válidos.")
        if clash:
            errors.append("Já existe um utilizador com esse email.")
        if (user is None or password) and len(password) < 8:
            errors.append("A palavra-passe deve ter pelo menos 8 caracteres.")
        if user is not None and user.id == current_user.id and (not is_admin or not active):
            errors.append("Não pode remover o seu próprio acesso de administrador.")

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            if user is None:
                user = User()
                db.session.add(user)
            user.name = name
            user.email = email
            user.is_admin = is_admin
            user.active = active
            user.vacation_days = max(0, vacation_days)
            color = request.form.get("color", "")
            if len(color) == 7 and color.startswith("#"):
                user.color = color
            if password:
                user.set_password(password)
            db.session.commit()
            flash(f"Utilizador {user.name} guardado.", "success")
            return redirect(url_for("admin.users"))

    return render_template(
        "admin/user_edit.html",
        user=user,
        default_vacation_days=current_app.config["DEFAULT_VACATION_DAYS"],
    )
