import csv
import io
from collections import OrderedDict
from datetime import datetime, timedelta

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for
from ..i18n import flash, gettext as _
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError

from .. import db
from ..models import AttendanceAudit, User, WorkSession
from ..attendance_time import local_to_utc, period_bounds, split_sessions, to_local, utc_now
from ..services import attendance as operations
from ..utils import admin_required, parse_month

bp = Blueprint('attendance', __name__, url_prefix='/picagens')


def _selected_user():
    user_id = request.values.get('user', type=int)
    return db.get_or_404(User, user_id) if current_user.is_admin and user_id else current_user


def sessions_between(user_id, first, following, voided=False):
    start, end = period_bounds(first, following)
    query = WorkSession.query.filter(WorkSession.user_id == user_id, WorkSession.start < end,
                                     db.or_(WorkSession.end.is_(None), WorkSession.end > start))
    if voided:
        query = query.filter(db.or_(WorkSession.end > start, db.and_(WorkSession.end.is_(None), WorkSession.voided_at > start)))
    query = query.filter(WorkSession.voided_at.is_not(None) if voided else WorkSession.voided_at.is_(None))
    return query.order_by(WorkSession.start).all()


def slices_between(user_id, first, following, at=None):
    return split_sessions(sessions_between(user_id, first, following), first, following, at=at)


def _failed(error):
    db.session.rollback()
    if isinstance(error, operations.AttendanceError):
        flash(str(error), 'error')
        return error.status_code
    flash('Conflito nas picagens. Verifique sobreposições e recarregue a página.', 'error')
    return 503 if isinstance(error, OperationalError) else 409


@bp.route('/entrada', methods=['POST'])
@login_required
def clock_in():
    try:
        record, created = operations.clock_in(current_user.id, request.form.get('note', '').strip())
        db.session.commit()
        flash('Entrada registada.' if created else 'Já tem uma entrada em aberto.', 'success' if created else 'error')
    except (IntegrityError, OperationalError, StaleDataError, operations.AttendanceError) as error:
        status = _failed(error)
        return render_template('error.html', code=status, message='Não foi possível registar a entrada. Recarregue a página.'), status
    return redirect(url_for('dashboard.index'))


@bp.route('/saida', methods=['POST'])
@login_required
def clock_out():
    try:
        record = operations.clock_out(current_user.id, request.form.get('note', '').strip())
        db.session.commit()
        flash('Saída registada.' if record else 'Não existe nenhuma entrada em aberto.', 'success' if record else 'error')
    except (IntegrityError, OperationalError, StaleDataError, operations.AttendanceError) as error:
        status = _failed(error)
        return render_template('error.html', code=status, message='Não foi possível registar a saída. Recarregue a página.'), status
    return redirect(url_for('dashboard.index'))


@bp.route('/')
@login_required
def index():
    user = _selected_user()
    first, following = parse_month(request.args.get('mes'))
    rows = slices_between(user.id, first, following)
    days = OrderedDict()
    for row in rows:
        days.setdefault(row.day, []).append(row)
    return render_template('attendance/index.html', user=user,
        users=User.query.order_by(User.name).all() if current_user.is_admin else [], first=first,
        prev_month=(first-timedelta(days=1)).strftime('%Y-%m'), next_month=following.strftime('%Y-%m'),
        days=days, total=sum((row.duration for row in rows), timedelta()),
        voided=sessions_between(user.id, first, following, voided=True) if current_user.is_admin else [])


def _csv_text(value):
    value = value or ''
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value


@bp.route('/exportar')
@login_required
def export():
    first, following = parse_month(request.args.get('mes'))
    users = User.query.order_by(User.name).all() if current_user.is_admin and request.args.get('todos') else [_selected_user()]
    at = utc_now()
    out = io.StringIO()
    writer = csv.writer(out, delimiter=';')
    writer.writerow([_(label) for label in ['Colaborador', 'Data', 'Entrada', 'Saída', 'Horas', 'Nota']])
    for user in users:
        for row in slices_between(user.id, first, following, at=at):
            writer.writerow([_csv_text(user.name), row.day.isoformat(), to_local(row.start).isoformat(),
                             to_local(row.end).isoformat(), f'{row.hours:.6f}'.replace('.', ','), _csv_text(row.session.note)])
    return Response('\ufeff'+out.getvalue(), mimetype='text/csv', headers={
        'Content-Disposition': f'attachment; filename=picagens-{first:%Y-%m}.csv', 'Cache-Control': 'no-store'})


def _input_instant(field, record):
    value = request.form.get(field, '')
    if field == 'end' and not value:
        return None
    fold = request.form.get(field+'_fold', '')
    if fold not in ('', '0', '1'):
        raise ValueError('Escolha uma ocorrência válida para a hora repetida.')
    try:
        wall_time = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(_('Indique uma data e hora válidas.')) from error
    if not 1900 <= wall_time.year <= 9998:
        raise ValueError(_('Escolha uma data entre 1900 e 9998.'))
    original = getattr(record, field) if record else None
    if original and not fold and wall_time == to_local(original).replace(tzinfo=None, microsecond=0):
        return original  # An unchanged wall time keeps its original DST occurrence and precision.
    instant = local_to_utc(value, fold=int(fold) if fold else None)
    if not 1900 <= to_local(instant).year <= 9998:
        raise ValueError(_('Escolha uma data entre 1900 e 9998.'))
    if original and instant == original.replace(microsecond=0):
        return original  # Editing only a note must not silently round clock timestamps.
    return instant


@bp.route('/nova', methods=['GET', 'POST'])
@bp.route('/<int:session_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(session_id=None):
    record = db.get_or_404(WorkSession, session_id) if session_id else None
    if record and record.voided_at:
        abort(409)
    status = 200
    if request.method == 'POST':
        try:
            start, end = _input_instant('start', record), _input_instant('end', record)
            record = operations.correct(current_user.id, request.form.get('user_id', type=int) or 0,
                start, end, request.form.get('note', '').strip(), request.form.get('reason', ''),
                session_id=session_id, version=request.form.get('version', type=int))
            db.session.commit()
            flash('Picagem guardada com histórico.', 'success')
            return redirect(url_for('attendance.index', user=record.user_id, mes=to_local(record.start).strftime('%Y-%m')))
        except operations.AttendanceError as error:
            status = _failed(error)
        except ValueError as error:
            db.session.rollback()
            flash(str(error), 'error')
            status = 400
        except (IntegrityError, OperationalError, StaleDataError) as error:
            status = _failed(error)
    return render_template('attendance/edit.html', session=record, users=User.query.order_by(User.name).all(),
                           preselected=(request.form.get('user_id', type=int) if request.method == 'POST' else request.args.get('user', type=int))), status


@bp.route('/<int:session_id>/apagar', methods=['GET', 'POST'])
@login_required
@admin_required
def delete(session_id):
    record = db.get_or_404(WorkSession, session_id)
    status = 200
    if request.method == 'POST':
        try:
            operations.void(current_user.id, record, request.form.get('version', type=int), request.form.get('reason', ''))
            db.session.commit()
            flash('Picagem anulada. O registo e o histórico foram preservados.', 'success')
            return redirect(url_for('attendance.index', user=record.user_id, mes=to_local(record.start).strftime('%Y-%m')))
        except (IntegrityError, OperationalError, StaleDataError, operations.AttendanceError) as error:
            status = _failed(error)
    return render_template('attendance/void.html', session=record), status


@bp.route('/<int:session_id>/historico')
@login_required
@admin_required
def history(session_id):
    record = db.get_or_404(WorkSession, session_id)
    events = AttendanceAudit.query.filter_by(session_id=record.id).order_by(AttendanceAudit.id).all()
    response = Response(render_template('attendance/history.html', session=record, events=events))
    response.headers['Cache-Control'] = 'no-store'
    return response


@bp.app_template_filter('attendance_local')
def attendance_local(value):
    return to_local(value) if value else None


@bp.app_template_filter('attendance_input')
def attendance_input(value):
    return to_local(value).strftime('%Y-%m-%dT%H:%M:%S') if value else ''


@bp.after_app_request
def attendance_no_store(response):
    if request.blueprint in {'attendance', 'dashboard'}:
        response.headers['Cache-Control'] = 'no-store'
    return response
