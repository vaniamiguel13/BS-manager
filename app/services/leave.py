"""Transactional leave requests, reserved balances and retained decisions."""
from datetime import date

from .. import db
from ..i18n import gettext as _
from ..attendance_time import utc_now
from ..models import LeaveAudit, LeaveRequest, User
from ..utils import today, now
from .attendance import lock_users

ACTIVE = (LeaveRequest.PENDING, LeaveRequest.APPROVED)


class LeaveError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(_(message))
        self.status = status


def snapshot(record):
    return {key: value.isoformat() if isinstance(value, date) else value for key in
            ('user_id', 'kind', 'start_date', 'end_date', 'reason', 'status', 'reviewer_id',
             'reviewed_at', 'review_note', 'working_weekdays', 'version')
            for value in (getattr(record, key),)}


def audit(record, actor_id, action, before):
    db.session.flush()
    db.session.add(LeaveAudit(leave_id=record.id, actor_id=actor_id, action=action,
                             before=before, after=snapshot(record), recorded_at=utc_now()))
    db.session.flush()


def validate_active(record, user=None):
    user = user if user is not None else record.user
    others = LeaveRequest.query.filter(LeaveRequest.user_id == record.user_id,
        LeaveRequest.status.in_(ACTIVE), LeaveRequest.id != (record.id or 0)).all()
    if any(other.overlaps(record.start_date, record.end_date) for other in others):
        raise LeaveError('Já existe um pedido ativo que se sobrepõe a estas datas.', 409)
    if record.kind == 'ferias':
        for year in range(record.start_date.year, record.end_date.year + 1):
            used = sum(other.working_days(year) for other in others if other.kind == 'ferias')
            if used + record.working_days(year) > user.entitlement(year):
                raise LeaveError(_('Não tem dias de férias suficientes em {year}.', year=year), 409)


def draft(user, kind, start, end, reason=''):
    """Validate an unsaved request for preview or transactional submission."""
    if kind not in LeaveRequest.KINDS or start is None or end is None or end < start:
        raise LeaveError('Indique um tipo e um período válidos.')
    if end.year > 9998 or (end - start).days > 730:
        raise LeaveError('O período não pode ultrapassar dois anos.')
    if len(reason) > 500:
        raise LeaveError('O motivo não pode ultrapassar 500 caracteres.')
    record = LeaveRequest(user_id=user.id, kind=kind, start_date=start, end_date=end,
                          reason=reason, status=LeaveRequest.PENDING,
                          working_weekdays=user.working_weekdays)
    # Avoid autoflush of an incomplete/new request during balance queries.
    with db.session.no_autoflush:
        if not record.working_days():
            raise LeaveError('O período escolhido não inclui dias de trabalho configurados.')
        validate_active(record, user)
    return record


def create(user_id, kind, start, end, reason):
    lock_users(user_id)
    user = db.session.get(User, user_id)
    record = draft(user, kind, start, end, reason)
    record.user = user
    db.session.add(record)
    audit(record, user_id, 'request', None)
    return record


def transition(actor, record, action, note='', version=None):
    if action not in ('aprovar', 'rejeitar', 'cancelar') or len(note) > 500:
        raise LeaveError('Decisão ou nota inválida.')
    if action != 'cancelar' and not actor.is_admin:
        raise LeaveError('Não tem permissão para rever pedidos.', 403)
    if action == 'cancelar' and record.user_id != actor.id and not actor.is_admin:
        raise LeaveError('Não tem permissão para cancelar este pedido.', 403)
    lock_users(record.user_id)
    db.session.refresh(record, with_for_update=True)
    if version is not None and version != record.version:
        raise LeaveError('O pedido foi alterado. Recarregue a página.', 409)
    if record.status not in ACTIVE or (action != 'cancelar' and record.status != LeaveRequest.PENDING):
        raise LeaveError('Este pedido já não aceita esta decisão.', 409)
    if action == 'cancelar' and record.status == LeaveRequest.APPROVED and record.start_date <= today() and not actor.is_admin:
        raise LeaveError('Ausências já iniciadas só podem ser canceladas por um administrador.', 409)
    if action == 'aprovar':
        validate_active(record)  # Entitlements may have changed since submission.
    before = snapshot(record)
    record.status = {'aprovar': LeaveRequest.APPROVED, 'rejeitar': LeaveRequest.REJECTED,
                     'cancelar': LeaveRequest.CANCELLED}[action]
    record.reviewer_id, record.reviewed_at, record.review_note = actor.id, now(), note
    audit(record, actor.id, action, before)
    return record
