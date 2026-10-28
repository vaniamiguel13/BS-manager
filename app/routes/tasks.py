import csv
import io
from datetime import timedelta

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import TaskEntry, User
from ..utils import parse_date, parse_month, today

bp = Blueprint("tasks", __name__, url_prefix="/tarefas")


def _filtered_query():
    first, following = parse_month(request.args.get("mes"))
    query = TaskEntry.query.filter(TaskEntry.date >= first, TaskEntry.date < following)
    user_id = request.args.get("user", type=int)
    if current_user.is_admin:
        if user_id:
            query = query.filter(TaskEntry.user_id == user_id)
    else:
        query = query.filter(TaskEntry.user_id == current_user.id)
    project = request.args.get("projeto", "").strip()
    if project:
        query = query.filter(TaskEntry.project == project)
    return first, following, query.order_by(TaskEntry.date.desc(), TaskEntry.id.desc())


def _get_own_or_admin(task_id):
    task = db.get_or_404(TaskEntry, task_id)
    if task.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return task


@bp.route("/")
@login_required
def index():
    first, following, query = _filtered_query()
    entries = query.all()
    projects = [p for (p,) in db.session.query(TaskEntry.project).distinct().order_by(TaskEntry.project) if p]
    return render_template(
        "tasks/index.html",
        entries=entries,
        total=sum(e.hours for e in entries),
        first=first,
        prev_month=(first - timedelta(days=1)).strftime("%Y-%m"),
        next_month=following.strftime("%Y-%m"),
        projects=projects,
        users=User.query.order_by(User.name).all() if current_user.is_admin else [],
    )


@bp.route("/nova", methods=["GET", "POST"])
@bp.route("/<int:task_id>/editar", methods=["GET", "POST"])
@login_required
def edit(task_id=None):
    task = _get_own_or_admin(task_id) if task_id else None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        date = parse_date(request.form.get("date"))
        try:
            hours = float(request.form.get("hours", "0").replace(",", ".") or 0)
        except ValueError:
            hours = -1
        if not title or not date:
            flash("Indique pelo menos a data e o título da tarefa.", "error")
        elif not 0 <= hours <= 24:
            flash("As horas devem estar entre 0 e 24.", "error")
        else:
            if task is None:
                task = TaskEntry(user_id=current_user.id)
                db.session.add(task)
            task.date = date
            task.title = title[:200]
            task.project = request.form.get("project", "").strip()[:120]
            task.description = request.form.get("description", "").strip()
            task.hours = hours
            db.session.commit()
            flash("Tarefa guardada.", "success")
            return redirect(url_for("tasks.index", mes=date.strftime("%Y-%m")))

    projects = [p for (p,) in db.session.query(TaskEntry.project).distinct() if p]
    return render_template("tasks/edit.html", task=task, projects=sorted(projects), default_date=today())


@bp.route("/<int:task_id>/apagar", methods=["POST"])
@login_required
def delete(task_id):
    task = _get_own_or_admin(task_id)
    month = task.date.strftime("%Y-%m")
    db.session.delete(task)
    db.session.commit()
    flash("Tarefa apagada.", "success")
    return redirect(url_for("tasks.index", mes=month))


@bp.route("/exportar")
@login_required
def export():
    first, _, query = _filtered_query()
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Colaborador", "Data", "Projeto", "Tarefa", "Descrição", "Horas"])
    for e in query.all():
        writer.writerow([
            e.user.name, e.date.isoformat(), e.project, e.title, e.description,
            f"{e.hours:.2f}".replace(".", ","),
        ])
    return Response(
        "﻿" + out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tarefas-{first:%Y-%m}.csv"},
    )
