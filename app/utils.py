from datetime import date, datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from flask import abort, current_app, has_app_context
from flask_login import current_user

MONTHS = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def now():
    """Hora local (sem tzinfo) no fuso horário da empresa, independente do fuso do servidor."""
    tz = current_app.config["APP_TIMEZONE"] if has_app_context() else "Europe/Lisbon"
    return datetime.now(ZoneInfo(tz)).replace(tzinfo=None, microsecond=0)


def today():
    return now().date()


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def parse_month(value):
    """Converte 'AAAA-MM' em (primeiro dia, primeiro dia do mês seguinte). Por omissão: mês atual."""
    try:
        first = datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except (TypeError, ValueError):
        first = today().replace(day=1)
    following = (first + timedelta(days=32)).replace(day=1)
    return first, following


def parse_date(value, default=None):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def parse_datetime(value, default=None):
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except (TypeError, ValueError):
            continue
    return default


def format_hours(value):
    """Formata horas (float ou timedelta) como '7h05'."""
    if isinstance(value, timedelta):
        value = value.total_seconds() / 3600
    total_minutes = int(round((value or 0) * 60))
    sign = "-" if total_minutes < 0 else ""
    h, m = divmod(abs(total_minutes), 60)
    return f"{sign}{h}h{m:02d}"


def register_template_helpers(app):
    app.jinja_env.filters["hours"] = format_hours
    app.jinja_env.filters["d"] = lambda v: v.strftime("%d/%m/%Y") if v else ""
    app.jinja_env.filters["dt"] = lambda v: v.strftime("%d/%m/%Y %H:%M") if v else ""
    app.jinja_env.filters["t"] = lambda v: v.strftime("%H:%M") if v else ""

    @app.context_processor
    def inject_globals():
        return {
            "company_name": app.config["COMPANY_NAME"],
            "today": today(),
            "month_name": lambda m: MONTHS[m - 1],
        }

    @app.template_filter("month_label")
    def month_label(d: date):
        return f"{MONTHS[d.month - 1]} {d.year}"
