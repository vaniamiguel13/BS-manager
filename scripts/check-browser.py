#!/usr/bin/env python3
"""Run browser acceptance against a private, disposable loopback-only fixture."""
import os
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from datetime import timedelta

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import create_app,db
from app.models import User
from app.services import leave
from app.utils import today
from app.holidays import holidays
from flask_migrate import upgrade
from werkzeug.serving import make_server


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--responsive', action='store_true', help='Check responsive navigation, report alignment and themes')
    options=parser.parse_args()
    # Do not inherit operator database/bootstrap settings.
    for key in ('DATABASE_URL','DATABASE_HOST','DATABASE_USER','DATABASE_PASSWORD','DATABASE_NAME','ADMIN_EMAIL','ADMIN_PASSWORD','ADMIN_NAME','SECRET_KEY'):
        os.environ.pop(key,None)
    with tempfile.TemporaryDirectory(prefix='bs-manager-browser-') as folder:
        app=create_app({'TESTING':True,'SECRET_KEY':os.urandom(32).hex(),'SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(Path(folder)/'test.db')})
        with app.app_context():
            upgrade()
            for name in ('admin','worker','colleague','availability'):
                user=User(name='Synthetic '+name,email=name+'@example.invalid',is_admin=name=='admin')
                user.set_password('browser-synthetic-password')
                db.session.add(user)
            db.session.commit()
            availability_user=User.query.filter_by(email='availability@example.invalid').one()
            admin=User.query.filter_by(email='admin@example.invalid').one()
            weekdays={int(day) for day in availability_user.working_weekdays.split(',')}
            start=today()+timedelta(days=2)
            while start.weekday() not in weekdays or start in holidays(start.year):
                start+=timedelta(days=1)
            record=leave.create(availability_user.id,'baixa',start,start,'Private synthetic medical detail')
            leave.transition(admin,record,'aprovar','Synthetic approval');db.session.commit()
        server=make_server('127.0.0.1',0,app,threaded=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            env={**os.environ,'BS_BROWSER_BASE':f'http://127.0.0.1:{server.server_port}'}
            result=subprocess.run(['node',str(ROOT/('scripts/responsive-check.cjs' if options.responsive else 'scripts/browser-check.cjs'))],env=env,cwd=ROOT)
            return result.returncode
        finally:
            server.shutdown();thread.join(timeout=10)
            with app.app_context():db.session.remove();db.engine.dispose()


if __name__=='__main__':raise SystemExit(main())
