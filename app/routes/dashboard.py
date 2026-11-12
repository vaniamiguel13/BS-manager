from datetime import datetime, time, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .. import db
from ..models import LeaveRequest, TaskEntry
from ..utils import WEEKDAYS, today
from .attendance import slices_between

bp = Blueprint("dashboard", __name__)


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
    week_rows = slices_between(current_user.id, week_start.date(), week_start.date() + timedelta(days=7))
    per_day = {}
    for row in week_rows:
        per_day[row.day] = per_day.get(row.day, timedelta()) + row.duration
    # Bars scale to a full working day unless a longer day was recorded.
    scale = max([timedelta(hours=8), *per_day.values()])
    week = [
        {"date": day, "label": WEEKDAYS[day.weekday()], "duration": per_day.get(day, timedelta()),
         "percent": round(100 * per_day.get(day, timedelta()) / scale), "is_today": day == d}
        for day in (week_start.date() + timedelta(days=i) for i in range(7))
    ]
    projects = sorted(p for (p,) in db.session.query(TaskEntry.project).filter_by(user_id=current_user.id).distinct() if p)

    return render_template(
        "dashboard.html",
        open_session=current_user.open_session(),
        today_sessions=[row for row in week_rows if row.day == d],
        worked_today=per_day.get(d, timedelta()),
        worked_week=sum(per_day.values(), timedelta()),
        week=week,
        day=d,
        balance=current_user.vacation_balance(d.year),
        out_today=[item for item in upcoming if item.start_date <= d],
        out_soon=[item for item in upcoming if item.start_date > d],
        pending_reviews=pending_reviews,
        today_tasks=today_tasks,
        projects=projects,
    )
