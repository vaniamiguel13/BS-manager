from datetime import timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
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
    start = parse_date((request.args.get("start") or "")[:10], today().replace(day=1))
    end = parse_date((request.args.get("end") or "")[:10], start + timedelta(days=42))
    result = []

    for year in range(start.year, end.year + 1):
        for d, name in holidays(year).items():
            if start <= d < end:
                result.append({
                    "title": "", "start": d.isoformat(), "allDay": True,
                    "display": "background", "color": "#fca5a5", "kind": "feriado",
                })
                result.append({
                    "title": f"🎉 {name}", "start": d.isoformat(), "allDay": True,
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
        result.append({
            "title": f"{leave.user.name} – {leave.kind_label}" + (" (pendente)" if pending else ""),
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
@login_required
def create_event():
    title = request.form.get("title", "").strip()
    all_day = bool(request.form.get("all_day"))
    if all_day:
        start_d = parse_date(request.form.get("start_date"))
        end_d = parse_date(request.form.get("end_date")) or start_d
        start = parse_datetime(f"{start_d} 00:00") if start_d else None
        end = parse_datetime(f"{end_d} 00:00") if end_d else None
    else:
        start = parse_datetime(request.form.get("start"))
        end = parse_datetime(request.form.get("end"))

    if not title or not start:
        flash("Indique o título e o início do evento.", "error")
    elif end and end < start:
        flash("O fim não pode ser anterior ao início.", "error")
    else:
        db.session.add(Event(
            title=title[:200],
            description=request.form.get("description", "").strip(),
            start=start,
            end=end,
            all_day=all_day,
            created_by_id=current_user.id,
        ))
        db.session.commit()
        flash("Evento criado.", "success")
    return redirect(url_for("calendar.index"))


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
