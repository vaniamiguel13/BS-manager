from datetime import date, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager
from .holidays import is_working_day
from .utils import now


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

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.active

    def open_session(self):
        return WorkSession.query.filter_by(user_id=self.id, end=None).first()

    def vacation_used(self, year, include_pending=True):
        statuses = [LeaveRequest.APPROVED] + ([LeaveRequest.PENDING] if include_pending else [])
        requests = LeaveRequest.query.filter(
            LeaveRequest.user_id == self.id,
            LeaveRequest.kind == "ferias",
            LeaveRequest.status.in_(statuses),
        ).all()
        return sum(r.working_days(year) for r in requests)

    def vacation_balance(self, year):
        return self.vacation_days - self.vacation_used(year)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class WorkSession(db.Model):
    """Um par de picagens: entrada (start) e saída (end). `end` vazio = a trabalhar."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    start = db.Column(db.DateTime, nullable=False, index=True)
    end = db.Column(db.DateTime)
    note = db.Column(db.String(255), default="")
    edited_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    user = db.relationship("User", back_populates="sessions", foreign_keys=[user_id])
    edited_by = db.relationship("User", foreign_keys=[edited_by_id])

    @property
    def duration(self):
        return (self.end or now()) - self.start

    @property
    def hours(self):
        return self.duration.total_seconds() / 3600


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
        return sum(1 for d in self.dates() if is_working_day(d) and (year is None or d.year == year))

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
