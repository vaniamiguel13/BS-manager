from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .. import db
from ..models import LeaveRequest
from ..utils import admin_required, now, parse_date, today

bp = Blueprint("leave", __name__, url_prefix="/ferias")

ACTIVE = (LeaveRequest.PENDING, LeaveRequest.APPROVED)


@bp.route("/")
@login_required
def index():
    year = request.args.get("ano", type=int) or today().year
    requests_ = (
        LeaveRequest.query.filter_by(user_id=current_user.id)
        .order_by(LeaveRequest.start_date.desc())
        .all()
    )
    pending = (
        LeaveRequest.query.filter_by(status=LeaveRequest.PENDING).order_by(LeaveRequest.start_date).all()
        if current_user.is_admin
        else []
    )
    return render_template(
        "leave/index.html",
        year=year,
        requests=requests_,
        pending=pending,
        used_approved=current_user.vacation_used(year, include_pending=False),
        used_total=current_user.vacation_used(year),
        kinds=LeaveRequest.KINDS,
    )


@bp.route("/pedir", methods=["POST"])
@login_required
def create():
    kind = request.form.get("kind", "ferias")
    start = parse_date(request.form.get("start_date"))
    end = parse_date(request.form.get("end_date")) or start
    reason = request.form.get("reason", "").strip()[:500]

    if kind not in LeaveRequest.KINDS or not start:
        flash("Indique o tipo e a data de início.", "error")
        return redirect(url_for("leave.index"))
    if end < start:
        flash("A data de fim não pode ser anterior à de início.", "error")
        return redirect(url_for("leave.index"))

    leave = LeaveRequest(user_id=current_user.id, kind=kind, start_date=start, end_date=end, reason=reason)
    if leave.working_days() == 0:
        flash("O período escolhido não inclui dias úteis.", "error")
        return redirect(url_for("leave.index"))

    existing = LeaveRequest.query.filter(
        LeaveRequest.user_id == current_user.id, LeaveRequest.status.in_(ACTIVE)
    ).all()
    if any(r.overlaps(start, end) for r in existing):
        flash("Já tem um pedido que se sobrepõe a estas datas.", "error")
        return redirect(url_for("leave.index"))

    if kind == "ferias":
        for year in {d.year for d in leave.dates()}:
            if leave.working_days(year) > current_user.vacation_balance(year):
                flash(f"Não tem dias de férias suficientes em {year}.", "error")
                return redirect(url_for("leave.index"))

    db.session.add(leave)
    db.session.commit()
    flash(f"Pedido submetido ({leave.working_days()} dia(s) úteis). Aguarda aprovação.", "success")
    return redirect(url_for("leave.index"))


@bp.route("/<int:leave_id>/cancelar", methods=["POST"])
@login_required
def cancel(leave_id):
    leave = db.get_or_404(LeaveRequest, leave_id)
    if leave.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    if leave.status not in ACTIVE:
        flash("Este pedido já não pode ser cancelado.", "error")
    elif leave.status == LeaveRequest.APPROVED and leave.start_date <= today() and not current_user.is_admin:
        flash("Férias já iniciadas só podem ser canceladas por um administrador.", "error")
    else:
        leave.status = LeaveRequest.CANCELLED
        db.session.commit()
        flash("Pedido cancelado.", "success")
    return redirect(request.referrer or url_for("leave.index"))


@bp.route("/<int:leave_id>/rever", methods=["POST"])
@login_required
@admin_required
def review(leave_id):
    leave = db.get_or_404(LeaveRequest, leave_id)
    decision = request.form.get("decision")
    if leave.status != LeaveRequest.PENDING or decision not in ("aprovar", "rejeitar"):
        flash("Pedido inválido.", "error")
    else:
        leave.status = LeaveRequest.APPROVED if decision == "aprovar" else LeaveRequest.REJECTED
        leave.reviewer_id = current_user.id
        leave.reviewed_at = now()
        leave.review_note = request.form.get("review_note", "").strip()[:500]
        db.session.commit()
        flash(f"Pedido de {leave.user.name} {leave.status}.", "success")
    return redirect(request.referrer or url_for("leave.index"))
