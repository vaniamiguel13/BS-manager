import csv
import io
from collections import OrderedDict
from datetime import datetime, time, timedelta

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import User, WorkSession
from ..utils import admin_required, now, parse_datetime, parse_month

bp = Blueprint("attendance", __name__, url_prefix="/picagens")


def _selected_user():
    """Admins podem consultar qualquer colaborador via ?user=ID; os restantes só a si próprios."""
    user_id = request.values.get("user", type=int)
    if current_user.is_admin and user_id:
        return db.get_or_404(User, user_id)
    return current_user


def _month_sessions(user, first, following):
    return (
        WorkSession.query.filter(
            WorkSession.user_id == user.id,
            WorkSession.start >= datetime.combine(first, time.min),
            WorkSession.start < datetime.combine(following, time.min),
        )
        .order_by(WorkSession.start)
        .all()
    )


@bp.route("/entrada", methods=["POST"])
@login_required
def clock_in():
    if current_user.open_session():
        flash("Já tem uma entrada registada. Registe primeiro a saída.", "error")
    else:
        db.session.add(
            WorkSession(user_id=current_user.id, start=now(), note=request.form.get("note", "").strip()[:255])
        )
        db.session.commit()
        flash(f"Entrada registada às {now():%H:%M}.", "success")
    return redirect(request.referrer or url_for("dashboard.index"))


@bp.route("/saida", methods=["POST"])
@login_required
def clock_out():
    session = current_user.open_session()
    if not session:
        flash("Não existe nenhuma entrada em aberto.", "error")
    else:
        session.end = max(now(), session.start)
        note = request.form.get("note", "").strip()
        if note:
            session.note = (f"{session.note} | {note}" if session.note else note)[:255]
        db.session.commit()
        flash(f"Saída registada às {session.end:%H:%M}.", "success")
    return redirect(request.referrer or url_for("dashboard.index"))


@bp.route("/")
@login_required
def index():
    user = _selected_user()
    first, following = parse_month(request.args.get("mes"))
    sessions = _month_sessions(user, first, following)

    days = OrderedDict()
    for s in sessions:
        days.setdefault(s.start.date(), []).append(s)
    total = sum((s.duration for s in sessions), timedelta())

    return render_template(
        "attendance/index.html",
        user=user,
        users=User.query.order_by(User.name).all() if current_user.is_admin else [],
        first=first,
        prev_month=(first - timedelta(days=1)).strftime("%Y-%m"),
        next_month=following.strftime("%Y-%m"),
        days=days,
        total=total,
    )


@bp.route("/exportar")
@login_required
def export():
    first, following = parse_month(request.args.get("mes"))
    if current_user.is_admin and request.args.get("todos"):
        users = User.query.order_by(User.name).all()
    else:
        users = [_selected_user()]

    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Colaborador", "Data", "Entrada", "Saída", "Horas", "Nota"])
    for user in users:
        for s in _month_sessions(user, first, following):
            writer.writerow([
                user.name,
                s.start.strftime("%Y-%m-%d"),
                s.start.strftime("%H:%M"),
                s.end.strftime("%H:%M") if s.end else "",
                f"{s.hours:.2f}".replace(".", ","),
                s.note or "",
            ])
    filename = f"picagens-{first:%Y-%m}.csv"
    # BOM para o Excel reconhecer UTF-8.
    return Response(
        "﻿" + out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/nova", methods=["GET", "POST"])
@bp.route("/<int:session_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def edit(session_id=None):
    session = db.session.get(WorkSession, session_id) if session_id else None
    if session_id and session is None:
        abort(404)

    if request.method == "POST":
        user_id = request.form.get("user_id", type=int)
        start = parse_datetime(request.form.get("start"))
        end = parse_datetime(request.form.get("end"))
        if not start or not db.session.get(User, user_id or 0):
            flash("Indique o colaborador e a hora de entrada.", "error")
        elif end and end < start:
            flash("A saída não pode ser anterior à entrada.", "error")
        else:
            if session is None:
                session = WorkSession()
                db.session.add(session)
            session.user_id = user_id
            session.start = start
            session.end = end
            session.note = request.form.get("note", "").strip()[:255]
            session.edited_by_id = current_user.id
            db.session.commit()
            flash("Picagem guardada.", "success")
            return redirect(url_for("attendance.index", user=user_id, mes=start.strftime("%Y-%m")))

    return render_template(
        "attendance/edit.html",
        session=session,
        users=User.query.order_by(User.name).all(),
        preselected=request.args.get("user", type=int),
    )


@bp.route("/<int:session_id>/apagar", methods=["POST"])
@login_required
@admin_required
def delete(session_id):
    session = db.get_or_404(WorkSession, session_id)
    user_id, month = session.user_id, session.start.strftime("%Y-%m")
    db.session.delete(session)
    db.session.commit()
    flash("Picagem apagada.", "success")
    return redirect(url_for("attendance.index", user=user_id, mes=month))
