"""Small explicit PT/EN catalog for the staff interface; no record translation."""
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from flask import Blueprint, abort, current_app, flash as flask_flash, has_request_context, redirect, request, url_for


CATALOG = {}
for path in sorted((Path(__file__).parent / 'translations').glob('*.en.json')):
    CATALOG.update(json.loads(path.read_text(encoding='utf-8')))

bp = Blueprint('language', __name__)

CLIENT_MESSAGES = [
    'Sessão expirada', 'Guarda as tuas observações e volta a iniciar sessão.',
    'Revê as datas', 'Não foi possível calcular este período. Atualiza a página e tenta novamente.',
    'Este tipo de ausência não desconta dias do saldo de férias.',
    '{year}: {days} dia de férias · {remaining} dia disponível após o pedido.',
    '{year}: {days} dia de férias · {remaining} dias disponíveis após o pedido.',
    '{year}: {days} dias de férias · {remaining} dia disponível após o pedido.',
    '{year}: {days} dias de férias · {remaining} dias disponíveis após o pedido.',
    '{days} dia de trabalho', '{days} dias de trabalho', 'Resumo indisponível',
    'Podes continuar a preencher. As datas e o saldo serão verificados ao submeter.',
    'Escolhe as datas', 'Vamos contar os teus dias de trabalho e mostrar o efeito no saldo.',
    'A calcular…', 'A verificar os dias de trabalho, feriados e saldo disponível.',
]


def get_language():
    choice = request.cookies.get('bs_language') if has_request_context() else None
    return choice if choice in ('pt', 'en') else 'pt'


def gettext(message, **values):
    text = CATALOG.get(message, message) if get_language() == 'en' else message
    return text.format(**values) if values else text


def flash(message, category='message'):
    flask_flash(gettext(message), category)


def language_return_url():
    if request.url_rule and 'GET' in request.url_rule.methods:
        return request.full_path if request.query_string else request.path
    index = f'{request.blueprint}.index'
    return url_for(index) if index in current_app.view_functions else '/'


@bp.post('/language')
def change_language():
    language = request.form.get('language')
    if language not in ('pt', 'en'):
        abort(400)
    target = request.form.get('next', '/')
    decoded = unquote(target)
    if (not decoded.startswith('/') or decoded.startswith('//') or '\\' in decoded
            or any(ord(c) < 32 for c in decoded) or urlsplit(decoded).netloc):
        target = '/'
    response = redirect(target)
    response.set_cookie('bs_language', language, max_age=365 * 24 * 60 * 60,
                        secure=current_app.config['SESSION_COOKIE_SECURE'],
                        httponly=True, samesite='Lax')
    return response


def init_app(app):
    app.register_blueprint(bp)
    app.jinja_env.globals['_'] = gettext
    app.jinja_env.globals['language_return_url'] = language_return_url

    @app.context_processor
    def language_context():
        language = get_language()
        return {'language': language, 'html_language': 'pt-PT' if language == 'pt' else 'en',
                'client_messages': {key: gettext(key) for key in CLIENT_MESSAGES}}

    @app.after_request
    def language_headers(response):
        response.headers['Content-Language'] = 'pt-PT' if get_language() == 'pt' else 'en'
        response.vary.add('Cookie')
        return response
