import csv
import io
import math
from datetime import timedelta

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for
from ..i18n import flash, gettext as _
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


def _available_projects():
    query = db.session.query(TaskEntry.project).distinct()
    if not current_user.is_admin:
        query = query.filter(TaskEntry.user_id == current_user.id)
    return sorted(p for (p,) in query if p)


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
    projects = _available_projects()
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
    submitted = request.form if request.method == "POST" else None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        task_date = parse_date(request.form.get("date"))
        raw_date = request.form.get("date", "")
        try:
            hours = float(request.form.get("hours", "0").replace(",", ".") or 0)
        except (TypeError, ValueError):
            hours = math.nan
        description = request.form.get("description", "").strip()
        project = request.form.get("project", "").strip()
        target_user_id = (request.form.get("user_id", type=int) if "user_id" in request.form else (task.user_id if task else current_user.id)) if current_user.is_admin else current_user.id
        errors = []
        if not task_date or not 1900 <= task_date.year <= 9998 or not raw_date or raw_date != task_date.isoformat():
            errors.append("Indique uma data válida para a tarefa.")
        if not title:
            errors.append("Indique o título da tarefa.")
        if not math.isfinite(hours) or not 0 <= hours <= 24:
            errors.append("As horas devem ser um número finito entre 0 e 24.")
        if len(description) > 10000:
            errors.append("A descrição não pode exceder 10000 caracteres.")
        if len(project) > 120:
            errors.append("O projeto não pode exceder 120 caracteres.")
        if len(title) > 200:
            errors.append("O título não pode exceder 200 caracteres.")
        if not target_user_id or db.session.get(User, target_user_id) is None:
            errors.append("Escolha um colaborador válido.")
        if errors:
            for message in errors:
                flash(message, "error")
        else:
            if task is None:
                task = TaskEntry(user_id=target_user_id)
                db.session.add(task)
            elif current_user.is_admin:
                task.user_id = target_user_id
            task.date = task_date
            task.title = title
            task.project = project
            task.description = description
            task.hours = hours
            db.session.commit()
            flash("Tarefa guardada.", "success")
            return redirect(url_for("tasks.index", mes=task_date.strftime("%Y-%m"), user=task.user_id))
        projects = _available_projects()
        return render_template("tasks/edit.html", task=task, projects=projects, default_date=today(), submitted=submitted,
                               users=User.query.order_by(User.name).all() if current_user.is_admin else []), 400

    projects = _available_projects()
    return render_template("tasks/edit.html", task=task, projects=projects, default_date=today(), submitted=submitted,
                           users=User.query.order_by(User.name).all() if current_user.is_admin else [])


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
    first, _following, query = _filtered_query()
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow([_(label) for label in ["Colaborador", "Data", "Projeto", "Tarefa", "Descrição", "Horas"]])
    for e in query.all():
        writer.writerow([
            _csv_text(e.user.name), e.date.isoformat(), _csv_text(e.project), _csv_text(e.title), _csv_text(e.description),
            f"{e.hours:.2f}".replace(".", ","),
        ])
    return Response(
        "﻿" + out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tarefas-{first:%Y-%m}.csv", "Cache-Control": "no-store"},
    )


def _csv_text(value):
    value = value or ""
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else value
