from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest
from flask_migrate import upgrade
from sqlalchemy import update, delete
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import User, LeaveRequest, LeaveAudit, LeaveAllowance, LoginThrottle
from app.services import leave as leave_service
from app.services.authentication import MAX_FAILURES

PASSWORD='synthetic-password-12345'


@pytest.fixture
def staff(database_url):
    app=create_app({'TESTING':True,'WTF_CSRF_ENABLED':False,'SQLALCHEMY_DATABASE_URI':database_url})
    with app.app_context():
        upgrade()
        people=[User(name=name,email=name+'@example.invalid',is_admin=(name=='admin')) for name in ('admin','worker','other')]
        for user in people:user.set_password(PASSWORD)
        db.session.add_all(people);db.session.commit()
        ids={u.name:u.id for u in people}
    yield app,ids
    with app.app_context():db.session.remove();db.engine.dispose()


def login(app,name='worker',password=PASSWORD):
    client=app.test_client();response=client.post('/login',data={'email':name+'@example.invalid','password':password})
    return client,response


def request_leave(client,start='2026-12-21',end='2026-12-23',kind='ferias'):
    return client.post('/ferias/pedir',data={'kind':kind,'start_date':start,'end_date':end,'reason':'Sensitive original reason'})


def test_leave_privacy_calendar_dashboard_history_and_admin_review(staff):
    app,ids=staff;owner,_=login(app);admin,_=login(app,'admin');other,_=login(app,'other')
    assert request_leave(owner,kind='baixa').status_code==302
    with app.app_context():record_id=LeaveRequest.query.one().id
    endpoint='/calendario/eventos?start=2026-12-01&end=2027-01-01'
    assert all('worker' not in e['title'] for e in other.get(endpoint).json)
    assert owner.get(f'/ferias/{record_id}/historico').status_code==200
    assert other.get(f'/ferias/{record_id}/historico').status_code==403
    assert other.post(f'/ferias/{record_id}/cancelar').status_code==403
    assert other.post(f'/ferias/{record_id}/rever',data={'decision':'aprovar'}).status_code==403
    assert admin.post(f'/ferias/{record_id}/rever',data={'decision':'aprovar','review_note':'Approved synthetic'}).status_code==302
    events=other.get(endpoint).json
    assert any(e['title']=='worker – Indisponível' for e in events)
    assert 'Baixa' not in other.get(endpoint).text and 'Sensitive' not in other.get(endpoint).text
    assert any('Baixa médica' in e['title'] for e in owner.get(endpoint).json)
    # Dashboard query uses company today; future fixture is within a synthetic 30-day window.
    import app.routes.dashboard as dashboard
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(dashboard,'today',lambda:date(2026,12,1))
        assert 'Baixa médica' not in other.get('/').text
        assert 'Indisponível' in other.get('/').text
        assert 'Baixa médica' in admin.get('/').text
    assert 'Approved synthetic' in owner.get(f'/ferias/{record_id}/historico').text


@pytest.mark.parametrize('start,end,kind', [('2026-12-21','bad','ferias'),('bad','','ferias'),('2026-12-23','2026-12-21','ferias'),('2026-12-21','','unknown'),('2026-12-25','','ferias'),('2026-12-26','2026-12-27','ferias'),('2026-01-01','2030-01-01','ferias')])
def test_invalid_leave_never_creates_history(staff,start,end,kind):
    app,ids=staff;client,_=login(app)
    assert request_leave(client,start,end,kind).status_code==400
    with app.app_context():assert LeaveRequest.query.count()==LeaveAudit.query.count()==0


def test_leave_reservation_year_split_schedule_snapshot_and_cancellation(staff):
    app,ids=staff;client,_=login(app);admin,_=login(app,'admin')
    with app.app_context():
        user=db.session.get(User,ids['worker']);user.working_weekdays='0,2,4'
        db.session.add_all([LeaveAllowance(user_id=user.id,year=2026,days=1),LeaveAllowance(user_id=user.id,year=2027,days=1)])
        db.session.commit()
    assert request_leave(client,'2026-12-30','2027-01-04').status_code==302
    with app.app_context():
        record=LeaveRequest.query.one();record_id=record.id
        assert record.working_days(2026)==1 and record.working_days(2027)==1
        assert record.user.vacation_balance(2026)==record.user.vacation_balance(2027)==0
        record.user.working_weekdays='0,1,2,3,4';db.session.commit()
        assert record.working_days(2026)==1
    assert request_leave(client,'2027-01-05','2027-01-05').status_code==409
    assert admin.post(f'/ferias/{record_id}/rever',data={'decision':'aprovar','version':'1'}).status_code==302
    assert admin.post(f'/ferias/{record_id}/rever',data={'decision':'rejeitar','version':'1'}).status_code==409
    assert admin.post(f'/ferias/{record_id}/cancelar',data={'version':'2','review_note':'Synthetic cancellation'}).status_code==302
    with app.app_context():
        assert [r.action for r in LeaveAudit.query.order_by(LeaveAudit.id)]==['request','aprovar','cancelar']
        assert db.session.get(User,ids['worker']).vacation_balance(2027)==1
        assert LeaveRequest.query.one().status=='cancelado'


@pytest.mark.parametrize('mutation',['update','delete'])
def test_leave_history_is_immutable(staff,mutation):
    app,ids=staff;client,_=login(app);request_leave(client)
    with app.app_context():
        event=LeaveAudit.query.one()
        with pytest.raises(IntegrityError):
            command=update(LeaveAudit).where(LeaveAudit.id==event.id).values(action='changed') if mutation=='update' else delete(LeaveAudit).where(LeaveAudit.id==event.id)
            db.session.execute(command);db.session.commit()
        db.session.rollback();assert LeaveAudit.query.one().action=='request'


def test_leave_approval_rechecks_changed_allowance_and_self_approval_allowed(staff):
    app,ids=staff;client,_=login(app);admin,_=login(app,'admin')
    request_leave(client)
    with app.app_context():
        record_id=LeaveRequest.query.one().id
        db.session.add(LeaveAllowance(user_id=ids['worker'],year=2026,days=0));db.session.commit()
    assert admin.post(f'/ferias/{record_id}/rever',data={'decision':'aprovar'}).status_code==409
    assert admin.post(f'/ferias/{record_id}/rever',data={'decision':'rejeitar'}).status_code==302
    assert request_leave(admin).status_code==302
    with app.app_context():record_id=LeaveRequest.query.filter_by(user_id=ids['admin']).one().id
    assert admin.post(f'/ferias/{record_id}/rever',data={'decision':'aprovar'}).status_code==302


def test_postgres_competing_leave_requests_cannot_overspend_annual_balance(staff):
    app,ids=staff
    with app.app_context():
        if db.engine.dialect.name!='postgresql':pytest.skip('PostgreSQL transaction locking')
        db.session.add(LeaveAllowance(user_id=ids['worker'],year=2026,days=1));db.session.commit()
    barrier=Barrier(2)
    def submit(day):
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                leave_service.create(ids['worker'],'ferias',day,day,'Concurrent synthetic')
                db.session.commit();return True
            except leave_service.LeaveError:
                db.session.rollback();return False
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,[date(2026,12,21),date(2026,12,22)]))
    assert sorted(results)==[False,True]
    with app.app_context():assert LeaveRequest.query.count()==LeaveAudit.query.count()==1


def test_password_changes_revoke_other_active_and_remembered_sessions(staff):
    app,ids=staff;first,_=login(app);second,_=login(app)
    response=first.post('/perfil',data={'action':'password','current_password':PASSWORD,'new_password':'updated-password-12345','confirm_password':'updated-password-12345'})
    assert response.status_code==302
    assert first.get('/').status_code==200
    assert second.get('/').status_code==302
    _,old=login(app,password=PASSWORD);assert old.status_code==200
    _,new=login(app,password='updated-password-12345');assert new.status_code==302


def test_operator_recovery_resets_password_revokes_sessions_and_clears_lockout(staff):
    app,ids=staff;client,_=login(app)
    for _ in range(MAX_FAILURES):login(app,password='incorrect')
    result=app.test_cli_runner().invoke(args=['reset-password','--email','worker@example.invalid'],input='new-synthetic-password\nnew-synthetic-password\n')
    assert result.exit_code==0,result.output
    assert client.get('/').status_code==302
    assert login(app,password='new-synthetic-password')[1].status_code==302


def test_login_throttle_is_shared_between_application_instances(staff):
    app,ids=staff
    for _ in range(MAX_FAILURES):login(app,password='incorrect')
    second=create_app({**app.config,'TESTING':True})
    assert login(second)[1].status_code==429
    with app.app_context():
        record=LoginThrottle.query.one();record.window_start-=timedelta(minutes=16);record.blocked_until-=timedelta(minutes=16);db.session.commit()
    assert login(second)[1].status_code==302


def test_account_deactivation_and_reset_do_not_resurrect_old_sessions(staff):
    app,ids=staff;client,_=login(app);admin,_=login(app,'admin')
    data={'name':'worker','email':'worker@example.invalid','vacation_days':'22','color':'#112233'}
    assert admin.post(f"/admin/utilizadores/{ids['worker']}",data=data).status_code==302
    assert client.get('/').status_code==302
    data['active']='1'
    assert admin.post(f"/admin/utilizadores/{ids['worker']}",data=data).status_code==302
    assert client.get('/').status_code==302
    assert login(app)[1].status_code==302
    data.update(password='replacement-password-123')
    assert admin.post(f"/admin/utilizadores/{ids['worker']}",data=data).status_code==302
    assert login(app,password='replacement-password-123')[1].status_code==302


@pytest.mark.parametrize('payload',[{'color':'#badxxx'},{'vacation_days':'NaN'},{'schedule_present':'1'}, {'password':'short'}, {'email':'invalid'}])
def test_invalid_admin_fields_are_rejected_without_account_change(staff,payload):
    app,ids=staff;admin,_=login(app,'admin')
    data={'name':'worker','email':'worker@example.invalid','vacation_days':'22','active':'1','color':'#112233',**payload}
    assert admin.post(f"/admin/utilizadores/{ids['worker']}",data=data).status_code==400
    with app.app_context():assert db.session.get(User,ids['worker']).email=='worker@example.invalid'


def test_security_headers_and_calendar_ranges(staff):
    app,ids=staff;client,_=login(app)
    for url in ['/','/ferias/','/tarefas/','/calendario/eventos']:
        response=client.get(url)
        assert response.headers['Cache-Control']=='no-store'
        assert response.headers['X-Frame-Options']=='DENY'
        assert response.headers['X-Content-Type-Options']=='nosniff'
    assert client.get('/calendario/eventos?start=2026-01-01&end=2040-01-01').status_code==400
    assert client.get('/calendario/eventos?start=2026-12-01&end=2026-01-01').status_code==400


def test_admin_cannot_reduce_default_entitlement_below_reserved_days(staff):
    app,ids=staff;client,_=login(app);admin,_=login(app,'admin');request_leave(client)
    data={'name':'worker','email':'worker@example.invalid','active':'1','vacation_days':'1','color':'#112233'}
    assert admin.post(f"/admin/utilizadores/{ids['worker']}",data=data).status_code==400
    with app.app_context():assert db.session.get(User,ids['worker']).vacation_days==22


def test_postgres_simultaneous_successful_logins_both_succeed(staff):
    app,ids=staff
    with app.app_context():
        if db.engine.dialect.name!='postgresql':pytest.skip('PostgreSQL transaction locking')
    # Existing bucket exercises the waiting-on-another-authentication path.
    login(app,password='incorrect')
    barrier=Barrier(2)
    def attempt(_):
        barrier.wait(timeout=10)
        return login(app)[1].status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert list(pool.map(attempt,range(2)))==[302,302]


@pytest.mark.parametrize('data',[{'title':'Bad end','start':'2026-10-29T10:00','end':'bad'}, {'title':'Reverse','start':'2026-10-29T11:00','end':'2026-10-29T10:00'},{'title':'Invalid all day','all_day':'1','start_date':'2026-10-29','end_date':'bad'},{'title':'Boundary','all_day':'1','start_date':'9999-12-31'}])
def test_calendar_invalid_input_is_retained_with_validation(staff,data):
    app,ids=staff;client,_=login(app)
    result=client.post('/calendario/evento',data=data)
    assert result.status_code==400
    assert data['title'] in result.text


def test_old_remember_cookie_is_rejected_after_password_reset(staff):
    app,ids=staff
    remembered=app.test_client()
    assert remembered.post('/login',data={'email':'worker@example.invalid','password':PASSWORD,'remember':'1'}).status_code==302
    assert remembered.get_cookie('remember_token') is not None
    remembered.delete_cookie('session')
    assert remembered.get('/').status_code==200
    admin,_=login(app,'admin')
    assert admin.post(f"/admin/utilizadores/{ids['worker']}",data={'name':'worker','email':'worker@example.invalid','vacation_days':'22','color':'#112233','active':'1','password':'changed-remember-password'}).status_code==302
    remembered.delete_cookie('session')
    assert remembered.get('/').status_code==302


def test_leave_estimate_counts_schedule_holidays_and_split_years_without_saving(staff):
    app, ids = staff
    client, _ = login(app)
    with app.app_context():
        user = db.session.get(User, ids['worker'])
        user.working_weekdays = '0,2,4'
        db.session.add_all([LeaveAllowance(user_id=user.id, year=2026, days=5),
                            LeaveAllowance(user_id=user.id, year=2027, days=3)])
        db.session.commit()
    payload = {'kind': 'ferias', 'start_date': '2026-12-30', 'end_date': '2027-01-04'}
    response = client.post('/ferias/prever', data=payload)
    assert response.status_code == 200
    assert response.json == {'working_days': 2, 'vacation': True, 'years': [
        {'year': 2026, 'days': 1, 'available': 5, 'remaining': 4},
        {'year': 2027, 'days': 1, 'available': 3, 'remaining': 2},
    ]}
    with app.app_context():
        assert LeaveRequest.query.count() == LeaveAudit.query.count() == 0
    assert client.post('/ferias/pedir', data=payload).status_code == 302
    with app.app_context():
        record = LeaveRequest.query.one()
        assert record.working_days() == 2


def test_leave_estimate_uses_signed_in_user_and_does_not_discount_other_types(staff):
    app, ids = staff
    client, _ = login(app)
    with app.app_context():
        db.session.get(User, ids['other']).vacation_days = 0
        db.session.commit()
    payload = {'kind': 'baixa', 'start_date': '2026-12-21', 'user_id': ids['other']}
    response = client.post('/ferias/prever', data=payload)
    assert response.status_code == 200
    assert response.json['vacation'] is False
    assert response.json['years'] == [{'year': 2026, 'days': 1, 'available': 22, 'remaining': 22}]
    assert response.headers['Cache-Control'] == 'no-store'
    assert app.test_client().post('/ferias/prever', data=payload).status_code == 302


@pytest.mark.parametrize('payload,code', [
    ({'kind': 'ferias', 'start_date': 'bad'}, 400),
    ({'kind': 'ferias', 'start_date': '2026-12-21', 'end_date': 'bad'}, 400),
    ({'kind': 'ferias', 'start_date': '2026-12-25'}, 400),
    ({'kind': 'unknown', 'start_date': '2026-12-21'}, 400),
    ({'kind': 'ferias', 'start_date': '2026-01-01', 'end_date': '2030-01-01'}, 400),
    ({'kind': 'ferias', 'start_date': '2026-12-21', 'end_date': '2026-12-23'}, 409),
])
def test_leave_estimate_enforces_submission_rules_without_audit_writes(staff, payload, code):
    app, ids = staff
    client, _ = login(app)
    with app.app_context():
        db.session.get(User, ids['worker']).vacation_days = 1
        db.session.commit()
    response = client.post('/ferias/prever', data=payload)
    assert response.status_code == code and response.json['error']
    with app.app_context():
        assert LeaveRequest.query.count() == LeaveAudit.query.count() == 0


def test_leave_estimate_detects_reserved_overlap_and_requires_csrf(staff):
    import re
    app, ids = staff
    client, _ = login(app)
    assert request_leave(client).status_code == 302
    payload = {'kind': 'ferias', 'start_date': '2026-12-21'}
    response = client.post('/ferias/prever', data=payload)
    assert response.status_code == 409 and 'sobrepõe' in response.json['error']
    with app.app_context():
        assert LeaveRequest.query.count() == LeaveAudit.query.count() == 1
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/ferias/prever', data=payload).status_code == 400
    page = client.get('/ferias/').text
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)
    response = client.post('/ferias/prever', data={**payload, 'csrf_token': token})
    assert response.status_code == 409 and 'sobrepõe' in response.json['error']


@pytest.mark.parametrize('payload', [
    {'name': 'x' * 121, 'color': '#112233'},
    {'name': ' ', 'color': '#112233'},
    {'name': 'New name', 'color': 'invalid'},
])
def test_invalid_profile_is_retained_and_never_reports_success(staff, payload):
    app, ids = staff
    client, _ = login(app)
    response = client.post('/perfil', data={'action': 'profile', **payload})
    assert response.status_code == 400
    assert 'Perfil atualizado.' not in response.text
    if payload['color'] == 'invalid':
        assert 'New name' in response.text
    with app.app_context():
        user = db.session.get(User, ids['worker'])
        assert user.name == 'worker' and user.color != '#112233'
