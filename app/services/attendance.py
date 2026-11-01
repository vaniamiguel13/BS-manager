from sqlalchemy import select
from .. import db
from ..i18n import gettext as _
from ..models import AttendanceAudit, User, WorkSession
from ..attendance_time import utc_now


class AttendanceError(ValueError):
    def __init__(self, message, status_code=409):
        super().__init__(_(message))
        self.status_code = status_code


def snapshot(record):
    return {key: (value.isoformat() if value is not None and key in {'start', 'end', 'voided_at'} else value)
            for key in ('user_id', 'start', 'end', 'note', 'voided_at', 'version', 'edited_by_id')
            for value in [getattr(record, key)]}


def lock_users(*ids):
    users = db.session.execute(select(User).where(User.id.in_(sorted(set(ids))))
                               .order_by(User.id).with_for_update()
                               .execution_options(populate_existing=True)).scalars().all()
    if len(users) != len(set(ids)):
        raise AttendanceError('Colaborador inválido.', 400)


def record_audit(record, actor_id, action, reason, before):
    db.session.flush()
    db.session.add(AttendanceAudit(session_id=record.id, actor_id=actor_id, action=action,
                                   reason=reason, before=before, after=snapshot(record)))
    db.session.flush()


def clock_in(user_id, note=''):
    lock_users(user_id)
    record = WorkSession.query.filter_by(user_id=user_id, end=None, voided_at=None).first()
    if record:
        return record, False
    record = WorkSession(user_id=user_id, start=utc_now(), note=note[:255])
    db.session.add(record)
    record_audit(record, user_id, 'clock-in', 'Entrada registada pelo colaborador.', None)
    return record, True


def clock_out(user_id, note=''):
    lock_users(user_id)
    record = WorkSession.query.filter_by(user_id=user_id, end=None, voided_at=None).first()
    if not record:
        return None
    before = snapshot(record)
    end = utc_now()
    if end <= record.start:
        raise AttendanceError('A saída tem de ser posterior à entrada.', 400)
    record.end = end
    if note:
        record.note = (' | '.join(filter(None, [record.note, note])))[:255]
    record_audit(record, user_id, 'clock-out', 'Saída registada pelo colaborador.', before)
    return record


def correct(actor_id, user_id, start, end, note, reason, session_id=None, version=None):
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise AttendanceError('Indique um motivo de correção (até 500 caracteres).', 400)
    if end is not None and end <= start:
        raise AttendanceError('A saída tem de ser posterior à entrada.', 400)
    record = db.session.get(WorkSession, session_id) if session_id else None
    if session_id and record is None:
        raise AttendanceError('Picagem inexistente.')
    lock_users(user_id, *([record.user_id] if record else []))
    if record:
        db.session.refresh(record, with_for_update=True)
        if record.voided_at or version != record.version:
            raise AttendanceError('A picagem foi alterada. Recarregue a página antes de guardar.')
    before = snapshot(record) if record else None
    if record is None:
        record = WorkSession()
        db.session.add(record)
    record.user_id, record.start, record.end = user_id, start, end
    record.note, record.edited_by_id = note[:255], actor_id
    if before:
        record.version += 1
    record_audit(record, actor_id, 'correct' if before else 'manual', reason, before)
    return record


def void(actor_id, record, version, reason):
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise AttendanceError('Indique um motivo de anulação (até 500 caracteres).', 400)
    lock_users(record.user_id)
    db.session.refresh(record, with_for_update=True)
    if record.voided_at or version != record.version:
        raise AttendanceError('A picagem foi alterada. Recarregue a página.')
    before = snapshot(record)
    record.voided_at = utc_now()
    record.edited_by_id = actor_id
    record_audit(record, actor_id, 'void', reason, before)
