from datetime import date, timedelta
import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager
from .holidays import is_working_day
from .utils import now
from .db_types import UTCDateTime
from .attendance_time import utc_now


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    vacation_days = db.Column(db.Integer, default=22, nullable=False)
    color = db.Column(db.String(7), default="#3b82f6", nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    session_token = db.Column(db.String(64), nullable=False, default=lambda: secrets.token_hex(32), server_default="", index=True, unique=True)
    working_weekdays = db.Column(db.String(13), nullable=False, default="0,1,2,3,4", server_default="0,1,2,3,4")

    def get_id(self):
        return self.session_token

    def entitlement(self, year):
        override = db.session.get(LeaveAllowance, (self.id, year))
        return override.days if override else self.vacation_days

    sessions = db.relationship(
        "WorkSession", back_populates="user", cascade="all, delete-orphan", foreign_keys="WorkSession.user_id"
    )
    tasks = db.relationship("TaskEntry", back_populates="user", cascade="all, delete-orphan")
    leaves = db.relationship(
        "LeaveRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="LeaveRequest.user_id",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.session_token = secrets.token_hex(32)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.active

    def open_session(self):
        return WorkSession.query.filter_by(user_id=self.id, end=None, voided_at=None).first()

    def vacation_used(self, year, include_pending=True):
        statuses = [LeaveRequest.APPROVED] + ([LeaveRequest.PENDING] if include_pending else [])
        requests = LeaveRequest.query.filter(
            LeaveRequest.user_id == self.id,
            LeaveRequest.kind == "ferias",
            LeaveRequest.status.in_(statuses),
        ).all()
        return sum(r.working_days(year) for r in requests)

    def vacation_balance(self, year):
        return self.entitlement(year) - self.vacation_used(year)


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(session_token=user_id, active=True).first() if isinstance(user_id, str) and len(user_id) == 64 else None


class WorkSession(db.Model):
    """UTC attendance interval. Voided rows remain available to administrators."""
    __table_args__ = (
        db.CheckConstraint('"end" IS NULL OR "end" > start', name="ck_work_session_positive"),
        db.Index("uq_work_session_open", "user_id", unique=True,
                 postgresql_where=db.text('"end" IS NULL AND voided_at IS NULL'),
                 sqlite_where=db.text('"end" IS NULL AND voided_at IS NULL')),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    start = db.Column(UTCDateTime(), nullable=False, index=True)
    end = db.Column(UTCDateTime())
    note = db.Column(db.String(255), default="")
    edited_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    voided_at = db.Column(UTCDateTime())
    version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    __mapper_args__ = {"version_id_col": version}
    user = db.relationship("User", back_populates="sessions", foreign_keys=[user_id])
    edited_by = db.relationship("User", foreign_keys=[edited_by_id])

    @property
    def duration(self):
        return max((self.end or utc_now()) - self.start, timedelta())

    @property
    def hours(self):
        return self.duration.total_seconds() / 3600


class AttendanceAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("work_session.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(20), nullable=False)
    recorded_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    reason = db.Column(db.String(500), nullable=False)
    before = db.Column(db.JSON)
    after = db.Column(db.JSON, nullable=False)
    actor = db.relationship("User")


class TaskEntry(db.Model):
    """Registo de uma tarefa realizada (descrição do trabalho feito num dia)."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    project = db.Column(db.String(120), default="")
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    hours = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    user = db.relationship("User", back_populates="tasks")


class LeaveRequest(db.Model):
    __table_args__ = (
        db.CheckConstraint('end_date >= start_date', name='ck_leave_dates'),
        db.CheckConstraint("status IN ('pendente','aprovado','rejeitado','cancelado')", name='ck_leave_status'),
        db.CheckConstraint("kind IN ('ferias','falta','baixa','formacao','teletrabalho','outro')", name='ck_leave_kind'),
    )
    PENDING = "pendente"
    APPROVED = "aprovado"
    REJECTED = "rejeitado"
    CANCELLED = "cancelado"

    KINDS = {
        "ferias": "Férias",
        "falta": "Falta",
        "baixa": "Baixa médica",
        "formacao": "Formação",
        "teletrabalho": "Teletrabalho",
        "outro": "Outro",
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    kind = db.Column(db.String(20), default="ferias", nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(500), default="")
    status = db.Column(db.String(20), default=PENDING, nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    working_weekdays = db.Column(db.String(13), nullable=False, default="0,1,2,3,4", server_default="0,1,2,3,4")
    __mapper_args__ = {"version_id_col": version}
    reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewed_at = db.Column(db.DateTime)
    review_note = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    user = db.relationship("User", back_populates="leaves", foreign_keys=[user_id])
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])

    @property
    def kind_label(self):
        return self.KINDS.get(self.kind, self.kind)

    def dates(self):
        d = self.start_date
        while d <= self.end_date:
            yield d
            d += timedelta(days=1)

    def working_days(self, year=None):
        weekdays = {int(day) for day in (self.working_weekdays or "0,1,2,3,4").split(',')}
        from .holidays import holidays
        return sum(1 for d in self.dates() if d.weekday() in weekdays and d not in holidays(d.year)
                   and (year is None or d.year == year))

    def overlaps(self, start: date, end: date):
        return self.start_date <= end and start <= self.end_date


class Event(db.Model):
    """Evento partilhado no calendário da equipa (reuniões, prazos, etc.)."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    start = db.Column(db.DateTime, nullable=False, index=True)
    end = db.Column(db.DateTime)
    all_day = db.Column(db.Boolean, default=False, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=now, nullable=False)

    created_by = db.relationship("User")


class LeaveAudit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    leave_id = db.Column(db.Integer, db.ForeignKey('leave_request.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(20), nullable=False)
    recorded_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    before = db.Column(db.JSON)
    after = db.Column(db.JSON, nullable=False)
    actor = db.relationship('User')


class LeaveAllowance(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    year = db.Column(db.Integer, primary_key=True)
    days = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.CheckConstraint('days >= 0 AND days <= 366', name='ck_allowance_days'),)


class LoginThrottle(db.Model):
    key = db.Column(db.String(64), primary_key=True)
    failures = db.Column(db.Integer, nullable=False, default=0)
    window_start = db.Column(UTCDateTime(), nullable=False)
    blocked_until = db.Column(UTCDateTime())
