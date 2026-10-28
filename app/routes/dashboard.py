from datetime import datetime, time, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..models import LeaveRequest, TaskEntry, WorkSession
from ..utils import today

bp = Blueprint("dashboard", __name__)


def worked_between(user_id, start, end):
    sessions = WorkSession.query.filter(
        WorkSession.user_id == user_id, WorkSession.start >= start, WorkSession.start < end
    ).all()
    return sum((s.duration for s in sessions), timedelta())


@bp.route("/")
@login_required
def index():
    d = today()
    day_start = datetime.combine(d, time.min)
    week_start = day_start - timedelta(days=d.weekday())

    upcoming = (
        LeaveRequest.query.filter(
            LeaveRequest.status == LeaveRequest.APPROVED,
            LeaveRequest.end_date >= d,
            LeaveRequest.start_date <= d + timedelta(days=30),
        )
        .order_by(LeaveRequest.start_date)
        .all()
    )
    pending_reviews = (
        LeaveRequest.query.filter_by(status=LeaveRequest.PENDING).count() if current_user.is_admin else 0
    )
    today_tasks = TaskEntry.query.filter_by(user_id=current_user.id, date=d).all()
    today_sessions = (
        WorkSession.query.filter(WorkSession.user_id == current_user.id, WorkSession.start >= day_start)
        .order_by(WorkSession.start)
        .all()
    )

    return render_template(
        "dashboard.html",
        open_session=current_user.open_session(),
        today_sessions=today_sessions,
        worked_today=worked_between(current_user.id, day_start, day_start + timedelta(days=1)),
        worked_week=worked_between(current_user.id, week_start, week_start + timedelta(days=7)),
        balance=current_user.vacation_balance(d.year),
        upcoming=upcoming,
        pending_reviews=pending_reviews,
        today_tasks=today_tasks,
    )
