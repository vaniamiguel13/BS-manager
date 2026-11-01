from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from ..i18n import flash, gettext as _
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError

from .. import db
from ..models import LeaveAudit, LeaveRequest, User
from ..services import leave as operations
from ..utils import admin_required, parse_date, today

bp = Blueprint('leave', __name__, url_prefix='/ferias')


def page(status=200):
    year = request.args.get('ano', type=int) or today().year
    if not 1900 <= year <= 9998:
        abort(400)
    selected = request.args.get('user', type=int) if current_user.is_admin else None
    user = db.get_or_404(User, selected) if selected else current_user
    requests_ = LeaveRequest.query.filter(LeaveRequest.user_id == user.id,
        LeaveRequest.start_date <= parse_date(f'{year}-12-31'), LeaveRequest.end_date >= parse_date(f'{year}-01-01')).order_by(LeaveRequest.start_date.desc()).all()
    pending = LeaveRequest.query.filter_by(status=LeaveRequest.PENDING).order_by(LeaveRequest.start_date).all() if current_user.is_admin else []
    return render_template('leave/index.html', year=year, user=user,
        users=User.query.order_by(User.name).all() if current_user.is_admin else [],
        requests=requests_, pending=pending, used_approved=user.vacation_used(year, False),
        used_total=user.vacation_used(year), kinds=LeaveRequest.KINDS), status


def failure(error):
    db.session.rollback()
    status = error.status if isinstance(error, operations.LeaveError) else (503 if isinstance(error, OperationalError) else 409)
    flash(str(error) if isinstance(error, operations.LeaveError) else 'Conflito no pedido. Recarregue a página.', 'error')
    return page(status)


@bp.route('/')
@login_required
def index():
    return page()


@bp.route('/pedir', methods=['POST'])
@login_required
def create():
    try:
        start = parse_date(request.form.get('start_date'))
        raw_end = request.form.get('end_date', '')
        end = parse_date(raw_end) if raw_end else start
        record = operations.create(current_user.id, request.form.get('kind', ''), start, end,
                                   request.form.get('reason', '').strip())
        db.session.commit()
        days = record.working_days()
        flash(_('Pedido submetido ({days} dia de trabalho). Aguarda aprovação.' if days == 1 else
                'Pedido submetido ({days} dias de trabalho). Aguarda aprovação.', days=days), 'success')
    except (operations.LeaveError, IntegrityError, OperationalError, StaleDataError) as error:
        return failure(error)
    return redirect(url_for('leave.index', ano=start.year))


@bp.route('/prever', methods=['POST'])
@login_required
def preview():
    """An informational snapshot for the signed-in employee; never reserves days."""
    start = parse_date(request.form.get('start_date'))
    raw_end = request.form.get('end_date', '')
    end = parse_date(raw_end) if raw_end else start
    try:
        record = operations.draft(current_user, request.form.get('kind', ''), start, end)
        years = []
        for year in range(start.year, end.year + 1):
            days = record.working_days(year)
            available = current_user.vacation_balance(year)
            years.append({'year': year, 'days': days, 'available': available,
                          'remaining': available - days if record.kind == 'ferias' else available})
        return jsonify(working_days=record.working_days(), years=years, vacation=record.kind == 'ferias')
    except operations.LeaveError as error:
        return jsonify(error=str(error)), error.status


@bp.route('/<int:leave_id>/cancelar', methods=['POST'])
@login_required
def cancel(leave_id):
    record = db.get_or_404(LeaveRequest, leave_id)
    if record.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    try:
        operations.transition(current_user, record, 'cancelar', request.form.get('review_note', '').strip(),
                              request.form.get('version', type=int))
        db.session.commit()
        flash('Pedido cancelado; histórico preservado.', 'success')
    except (operations.LeaveError, IntegrityError, OperationalError, StaleDataError) as error:
        return failure(error)
    return redirect(url_for('leave.index', ano=record.start_date.year, user=record.user_id))


@bp.route('/<int:leave_id>/rever', methods=['POST'])
@login_required
@admin_required
def review(leave_id):
    record = db.get_or_404(LeaveRequest, leave_id)
    try:
        operations.transition(current_user, record, request.form.get('decision'), request.form.get('review_note', '').strip(),
                              request.form.get('version', type=int))
        db.session.commit()
        flash('Decisão guardada com histórico.', 'success')
    except (operations.LeaveError, IntegrityError, OperationalError, StaleDataError) as error:
        return failure(error)
    return redirect(url_for('leave.index', ano=record.start_date.year, user=record.user_id))


@bp.route('/<int:leave_id>/historico')
@login_required
def history(leave_id):
    record = db.get_or_404(LeaveRequest, leave_id)
    if record.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template('leave/history.html', record=record, kinds=LeaveRequest.KINDS,
        events=LeaveAudit.query.filter_by(leave_id=record.id).order_by(LeaveAudit.id).all())
