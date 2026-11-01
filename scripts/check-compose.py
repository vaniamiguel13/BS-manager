#!/usr/bin/env python3
"""Exercise only a uniquely named disposable Compose project with synthetic data."""
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import urllib.parse
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = 'bs-manager-check-' + uuid4().hex[:12]
    password = secrets.token_hex(20)
    with tempfile.TemporaryDirectory(prefix=project + '-') as directory:
        env_file = Path(directory) / 'test.env'
        values = {'SECRET_KEY': secrets.token_hex(32), 'POSTGRES_OWNER_PASSWORD': secrets.token_hex(32),
                  'POSTGRES_PASSWORD': secrets.token_hex(32), 'ADMIN_EMAIL': 'admin@example.invalid',
                  'ADMIN_PASSWORD': password, 'WEB_PORT': '0', 'BS_MANAGER_IMAGE': project}
        env_file.touch(mode=0o600)
        env_file.write_text(''.join(key + '=' + value + '\n' for key, value in values.items()))
        environment = {key: value for key, value in os.environ.items()
                       if key not in values and not key.startswith('COMPOSE_')}
        command = ['docker', 'compose', '--project-name', project, '--env-file', str(env_file),
                   '-f', str(ROOT / 'docker-compose.yml')]

        def compose(*args, input=None):
            result = subprocess.run(command + list(args), cwd=ROOT, env=environment,
                                    input=input, text=True, capture_output=True, timeout=600)
            if result.returncode:
                # Redact generated credentials before printing bounded failure diagnostics.
                diagnostic = (result.stderr + result.stdout)[-6000:]
                for key in ('SECRET_KEY', 'POSTGRES_PASSWORD', 'POSTGRES_OWNER_PASSWORD', 'ADMIN_PASSWORD'):
                    diagnostic = diagnostic.replace(values[key], '[redacted]')
                raise RuntimeError('Compose operation failed: ' + args[0] + ' (exit ' + str(result.returncode) + ')\n' + diagnostic)
            return result.stdout.strip()

        def sql(query):
            return compose('exec', '-T', 'db', 'psql', '-U', 'bsmanager_owner', '-d', 'bsmanager', '-Atc', query)

        def web_python(source):
            return compose('exec', '-T', 'web', 'python', '-c', source)

        def check_http():
            address = compose('port', 'web', '8000').splitlines()[0]
            assert address.startswith('127.0.0.1:'), 'Web port is not loopback-only'
            base = 'http://' + address
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            with opener.open(base + '/health/ready', timeout=10) as response:
                assert json.load(response) == {'status': 'ok'}
            with opener.open(base + '/login', timeout=10) as response:
                html = response.read().decode()
            token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
            data = urllib.parse.urlencode({'email': values['ADMIN_EMAIL'], 'password': password, 'csrf_token': token}).encode()
            with opener.open(base + '/login', data=data, timeout=10) as response:
                assert urllib.parse.urlsplit(response.url).path == '/', 'Synthetic admin login failed'

        try:
            print('Building isolated synthetic Compose project...', flush=True)
            compose('build', 'web')
            compose('up', '-d', '--wait', 'db')
            assert sql("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'") == '0'
            compose('run', '--rm', '-T', 'migrate')
            compose('up', '-d', '--wait', 'web')
            check_http()
            assert web_python("from app import create_app,db; from sqlalchemy import text; a=create_app(); c=a.app_context(); c.push(); print(db.session.execute(text('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')).scalar())") == 'False'
            web_python("from app import create_app,db; from app.models import User,TaskEntry; from datetime import date; a=create_app(); c=a.app_context(); c.push(); u=User.query.one(); db.session.add(TaskEntry(user_id=u.id,date=date(2026,10,29),title='Synthetic persistence sentinel',hours=1.25)); db.session.commit()")
            expected = sql('SELECT count(*) FROM "user"') + ':' + sql('SELECT title FROM task_entry')
            compose('run', '--rm', '-T', 'migrate')
            compose('run', '--rm', '-T', 'migrate', 'flask', '--app', 'wsgi', 'db', 'check')
            assert sql('SELECT count(*) FROM "user"') + ':' + sql('SELECT title FROM task_entry') == expected
            compose('up', '-d', '--wait', '--force-recreate', 'web')
            check_http()
            compose('down')  # Keep this project's volume to prove database-container replacement.
            compose('up', '-d', '--wait')
            check_http()
            assert sql('SELECT count(*) FROM "user"') + ':' + sql('SELECT title FROM task_entry') == expected
            config = json.loads(compose('config', '--format', 'json'))
            assert not config['services']['db'].get('ports')
            assert 'caddy' not in config['services']
            # Exercise the prepared HTTPS overlay without publishing a route.
            command.extend(['-f', str(ROOT / 'docker-compose.pilot.yml')])
            compose('up', '-d', '--wait', '--force-recreate', 'web')
            assert web_python("from app import create_app; a=create_app(); print(a.config['SESSION_COOKIE_SECURE'])") == 'True'
            assert web_python("import os; print(os.statvfs('/app').f_flag & os.ST_RDONLY != 0)") == 'True'
            address = compose('port', 'web', '8000').splitlines()[0]
            with urllib.request.urlopen('http://' + address + '/login', timeout=10) as response:
                assert 'Secure' in response.headers.get('Set-Cookie', '')
                assert response.headers['Strict-Transport-Security'] == 'max-age=31536000'
            with urllib.request.urlopen('http://' + address + '/health/ready', timeout=10) as response:
                assert response.status == 200
            print('PASS: fresh init, real CSRF/login, restricted DB role, repeated migrations, schema check, web/database replacement data persistence and read-only HTTPS-cookie overlay.', flush=True)
        finally:
            compose('down', '--volumes', '--remove-orphans')
            # Remove only the image explicitly named for this isolated check.
            subprocess.run(['docker', 'image', 'rm', project], capture_output=True, text=True)


if __name__ == '__main__':
    main()
