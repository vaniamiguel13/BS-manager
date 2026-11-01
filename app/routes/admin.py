import hashlib
import re
import secrets

from flask import Blueprint, current_app, redirect, render_template, request, url_for
from ..i18n import flash, gettext as _
from flask_login import current_user, login_required, login_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from .. import db
from ..models import LeaveAllowance, LeaveRequest, LoginThrottle, User
from ..utils import admin_required, today

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/utilizadores')
@login_required
@admin_required
def users():
    return render_template('admin/users.html', users=User.query.order_by(User.active.desc(), User.name).all(), year=today().year)


@bp.route('/utilizadores/novo', methods=['GET', 'POST'])
@bp.route('/utilizadores/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id=None):
    user = db.get_or_404(User, user_id) if user_id else None
    status = 200
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        is_admin, active = bool(request.form.get('is_admin')), bool(request.form.get('active'))
        color = request.form.get('color', user.color if user else '#3b82f6')
        weekdays = request.form.getlist('working_weekdays') if 'schedule_present' in request.form else (user.working_weekdays if user else '0,1,2,3,4').split(',')
        errors = []
        try:
            vacation_days = int(request.form.get('vacation_days', ''))
            if not 0 <= vacation_days <= 366:
                raise ValueError
        except ValueError:
            vacation_days = 0
            errors.append('Indique um direito anual entre 0 e 366 dias.')
        allowance_year = request.form.get('allowance_year', '').strip()
        allowance_days = request.form.get('allowance_days', '').strip()
        override = None
        if allowance_days:
            try:
                override = (int(allowance_year), int(allowance_days))
                if not 1900 <= override[0] <= 9998 or not 0 <= override[1] <= 366:
                    raise ValueError
            except ValueError:
                errors.append('Indique um ano e saldo anual válidos.')
        if not name or len(name) > 120 or len(email) > 255 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            errors.append('Indique um nome e email válidos.')
        if (user is None or password) and not 12 <= len(password) <= 1024:
            errors.append('A palavra-passe deve ter entre 12 e 1024 caracteres.')
        if not weekdays or any(day not in tuple(str(i) for i in range(7)) for day in weekdays):
            errors.append('Selecione pelo menos um dia de trabalho válido.')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            errors.append('Escolha uma cor válida.')
        if user and user.id == current_user.id and (not is_admin or not active):
            errors.append('Não pode remover o seu próprio acesso de administrador.')
        if errors:
            for error in errors: flash(error, 'error')
            status = 400
        else:
            try:
                # One common lock serializes account administration and protects
                # the final administrator even during competing edits.
                db.session.execute(select(User).where(User.is_admin.is_(True)).order_by(User.id).with_for_update()).all()
                if user:
                    db.session.refresh(user, with_for_update=True)
                clash = User.query.filter(User.email == email, User.id != (user.id if user else 0)).first()
                if clash:
                    raise ValueError('Já existe um utilizador com esse email.')
                if user and user.active and user.is_admin and not (active and is_admin) and User.query.filter_by(active=True, is_admin=True).count() <= 1:
                    raise ValueError('Tem de manter pelo menos um administrador ativo.')
                if user and override and override[1] < user.vacation_used(override[0]):
                    raise ValueError('O direito anual não pode ser inferior aos dias já reservados.')
                if user:
                    requests_ = LeaveRequest.query.filter(LeaveRequest.user_id == user.id,
                        LeaveRequest.kind == 'ferias', LeaveRequest.status.in_(('pendente','aprovado'))).all()
                    years = {year for record in requests_ for year in range(record.start_date.year, record.end_date.year+1)}
                    for year in years:
                        if (override and override[0] == year) or db.session.get(LeaveAllowance, (user.id, year)):
                            continue
                        if vacation_days < user.vacation_used(year):
                            raise ValueError(_('O direito anual não cobre os dias reservados em {year}.', year=year))
                if user is None:
                    user = User()
                    db.session.add(user)
                elif (user.email, user.active, user.is_admin) != (email, active, is_admin):
                    user.session_token = secrets.token_hex(32)
                user.name, user.email, user.is_admin, user.active = name, email, is_admin, active
                user.vacation_days, user.working_weekdays, user.color = vacation_days, ','.join(sorted(set(weekdays))), color
                if password:
                    user.set_password(password)
                    bucket = db.session.get(LoginThrottle, hashlib.sha256(email.encode()).hexdigest())
                    if bucket:
                        from ..attendance_time import utc_now
                        bucket.failures, bucket.blocked_until, bucket.window_start = 0, None, utc_now()
                db.session.flush()
                if override:
                    allowance = db.session.get(LeaveAllowance, (user.id, override[0]))
                    if allowance is None:
                        allowance = LeaveAllowance(user_id=user.id, year=override[0])
                        db.session.add(allowance)
                    allowance.days = override[1]
                db.session.commit()
                if user.id == current_user.id:
                    login_user(user, fresh=True)
                flash('Utilizador guardado. Alterações de acesso/palavra-passe revogam sessões anteriores.', 'success')
                return redirect(url_for('admin.users'))
            except (ValueError, IntegrityError, OperationalError) as error:
                db.session.rollback()
                flash(str(error) if isinstance(error, ValueError) else 'Conflito ao guardar. Recarregue a página.', 'error')
                status = 400 if isinstance(error, ValueError) else 409
    return render_template('admin/user_edit.html', user=user,
        default_vacation_days=current_app.config['DEFAULT_VACATION_DAYS'],
        allowances=LeaveAllowance.query.filter_by(user_id=user.id).order_by(LeaveAllowance.year).all() if user else []), status
