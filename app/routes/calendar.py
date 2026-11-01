from datetime import timedelta

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from ..i18n import flash, gettext as _
from flask_login import current_user, login_required

from .. import db
from ..holidays import holidays
from ..models import Event, LeaveRequest
from ..utils import parse_date, parse_datetime, today

bp = Blueprint("calendar", __name__, url_prefix="/calendario")


@bp.route("/")
@login_required
def index():
    return render_template("calendar/index.html")


@bp.route("/eventos")
@login_required
def events():
    """Fonte JSON para o FullCalendar: feriados, ausências e eventos da equipa."""
    start = parse_date(request.args["start"][:10]) if request.args.get("start") else today().replace(day=1)
    if not start or not 1900 <= start.year <= 9998:
        abort(400)
    end = parse_date(request.args["end"][:10]) if request.args.get("end") else start + timedelta(days=42)
    if not end or not start < end or (end-start).days > 732:
        abort(400)
    result = []

    for year in range(start.year, end.year + 1):
        for d, name in holidays(year).items():
            if start <= d < end:
                result.append({
                    "title": "", "start": d.isoformat(), "allDay": True,
                    "display": "background", "color": "#fca5a5", "kind": "feriado",
                })
                result.append({
                    "title": f"🎉 {_(name)}", "start": d.isoformat(), "allDay": True,
                    "color": "#dc2626", "kind": "feriado",
                })

    leaves = LeaveRequest.query.filter(
        LeaveRequest.status.in_((LeaveRequest.APPROVED, LeaveRequest.PENDING)),
        LeaveRequest.start_date < end,
        LeaveRequest.end_date >= start,
    ).all()
    for leave in leaves:
        pending = leave.status == LeaveRequest.PENDING
        # Pedidos pendentes só são visíveis para o próprio e para administradores.
        if pending and leave.user_id != current_user.id and not current_user.is_admin:
            continue
        label = _(leave.kind_label) if current_user.is_admin or leave.user_id == current_user.id else _("Indisponível")
        result.append({
            "title": f"{leave.user.name} – {label}" + (_(" (pendente)") if pending else ""),
            "start": leave.start_date.isoformat(),
            "end": (leave.end_date + timedelta(days=1)).isoformat(),
            "allDay": True,
            "color": leave.user.color,
            "classNames": ["pending"] if pending else [],
            "kind": "ausencia",
        })

    team_events = Event.query.filter(
        Event.start < parse_datetime(f"{end} 00:00"),
        db.or_(Event.end >= parse_datetime(f"{start} 00:00"), Event.start >= parse_datetime(f"{start} 00:00")),
    ).all()
    for ev in team_events:
        item = {
            "id": ev.id,
            "title": ev.title,
            "allDay": ev.all_day,
            "color": "#0f766e",
            "kind": "evento",
            "description": ev.description,
            "author": ev.created_by.name,
            "canEdit": current_user.is_admin or ev.created_by_id == current_user.id,
        }
        if ev.all_day:
            item["start"] = ev.start.date().isoformat()
            item["end"] = ((ev.end or ev.start).date() + timedelta(days=1)).isoformat()
        else:
            item["start"] = ev.start.isoformat()
            if ev.end:
                item["end"] = ev.end.isoformat()
        result.append(item)

    return jsonify(result)


@bp.route("/evento", methods=["POST"])
@bp.route("/evento/<int:event_id>/editar", methods=["GET", "POST"])
@login_required
def create_event(event_id=None):
    event = db.get_or_404(Event, event_id) if event_id else None
    if event and event.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    template = "calendar/edit.html" if event else "calendar/index.html"
    if request.method == "GET":
        return render_template(template, event=event)
    title = request.form.get("title", "").strip()
    all_day = bool(request.form.get("all_day"))
    if all_day:
        start_d = parse_date(request.form.get("start_date"))
        end_d = parse_date(request.form.get("end_date")) if request.form.get("end_date") else start_d
        start = parse_datetime(f"{start_d} 00:00") if start_d else None
        end = parse_datetime(f"{end_d} 00:00") if end_d else None
    else:
        start = parse_datetime(request.form.get("start"))
        end = parse_datetime(request.form.get("end"))

    if len(title) > 200 or len(request.form.get("description", "")) > 10000:
        flash("Título ou descrição demasiado longos.", "error")
        return render_template(template, event=event, event_error=True), 400
    if not title or not start or (not all_day and request.form.get("end") and end is None) or (all_day and request.form.get("end_date") and end_d is None):
        flash("Indique o título e o início do evento.", "error")
    elif end and (end < start or (not all_day and end == start)):
        flash("O fim não pode ser anterior ao início.", "error")
    elif not 1900 <= start.year <= 9998 or (end and ((end-start).days > 730 or not 1900 <= end.year <= 9998)):
        flash("Escolha um período até dois anos, entre 1900 e 9998.", "error")
    else:
        if event is None:
            event = Event(created_by_id=current_user.id)
            db.session.add(event)
        event.title = title
        event.description = request.form.get("description", "").strip()
        event.start, event.end, event.all_day = start, end, all_day
        db.session.commit()
        flash("Evento guardado." if event_id else "Evento criado.", "success")
        return redirect(url_for("calendar.index"))
    return render_template(template, event=event, event_error=True), 400


@bp.route("/evento/<int:event_id>/apagar", methods=["POST"])
@login_required
def delete_event(event_id):
    ev = db.get_or_404(Event, event_id)
    if ev.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(ev)
    db.session.commit()
    flash("Evento apagado.", "success")
    return redirect(url_for("calendar.index"))
