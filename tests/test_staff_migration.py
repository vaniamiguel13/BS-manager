from datetime import date, datetime

import pytest
from flask_migrate import upgrade
from sqlalchemy import MetaData, Table, inspect, text
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import LeaveAudit, LeaveRequest, User


@pytest.fixture
def legacy_staff(database_url):
    app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':database_url})
    with app.app_context():
        upgrade(revision='0002_attendance')
        metadata=MetaData()
        users=Table('user',metadata,autoload_with=db.engine)
        leave=Table('leave_request',metadata,autoload_with=db.engine)
        db.session.execute(users.insert().values(id=1,name='Legacy synthetic',email='legacy@example.invalid',
            password_hash=generate_password_hash('synthetic-legacy-password'),is_admin=True,active=True,
            vacation_days=22,color='#112233',created_at=datetime(2026,1,1)))
        db.session.execute(leave.insert().values(id=1,user_id=1,kind='ferias',start_date=date(2026,12,21),
            end_date=date(2026,12,22),reason='Legacy synthetic request',status='pendente',created_at=datetime(2026,10,1)))
        db.session.commit()
    yield app
    with app.app_context():db.session.remove();db.engine.dispose()


def test_staff_upgrade_preserves_legacy_requests_and_marks_unknown_actor(legacy_staff):
    with legacy_staff.app_context():
        upgrade()
        user=User.query.one();request=LeaveRequest.query.one();audit=LeaveAudit.query.one()
        assert len(user.session_token)==64 and user.working_weekdays=='0,1,2,3,4'
        assert user.check_password('synthetic-legacy-password')
        assert request.reason=='Legacy synthetic request' and request.status=='pendente'
        assert request.version==1 and request.working_days()==2
        assert audit.action=='imported' and audit.actor_id is None
        assert audit.after['reason']=='Legacy synthetic request'
        assert legacy_staff.test_cli_runner().invoke(args=['db','check']).exit_code==0


@pytest.mark.parametrize('invalid', ['overlap','reversed'])
def test_staff_upgrade_refuses_invalid_legacy_before_schema_changes(legacy_staff,invalid):
    with legacy_staff.app_context():
        table=Table('leave_request',MetaData(),autoload_with=db.engine)
        if invalid=='overlap':
            db.session.execute(table.insert().values(id=2,user_id=1,kind='falta',start_date=date(2026,12,22),
                end_date=date(2026,12,23),reason='Legacy overlap',status='aprovado',created_at=datetime(2026,10,1)))
        else:
            db.session.execute(table.update().where(table.c.id==1).values(end_date=date(2026,12,20)))
        db.session.commit()
        with pytest.raises(SystemExit):upgrade()
        assert db.session.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0002_attendance'
        assert 'session_token' not in {c['name'] for c in inspect(db.engine).get_columns('user')}
        assert 'leave_audit' not in inspect(db.engine).get_table_names()
