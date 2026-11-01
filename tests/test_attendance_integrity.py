from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from flask_migrate import upgrade, downgrade
from sqlalchemy import text, bindparam, DateTime
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import create_app, db
from app.attendance_time import local_to_utc
from app.models import AttendanceAudit, User, WorkSession
from app.services import attendance

UTC = timezone.utc


@pytest.fixture
def app(database_url):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': database_url})
    with app.app_context():
        upgrade()
        user = User(name='Synthetic employee', email='staff@example.invalid')
        user.set_password('synthetic-password')
        db.session.add(user)
        db.session.commit()
    return app


def instant(hour):
    return datetime(2026, 10, 1, hour, tzinfo=UTC)


def test_database_rejects_overlaps_and_accepts_adjacent_intervals(app):
    with app.app_context():
        user = User.query.one()
        db.session.add(WorkSession(user_id=user.id, start=instant(9), end=instant(10)))
        db.session.commit()
        for start, end in [(instant(9), instant(11)), (instant(8), instant(10)), (instant(8), None), (instant(10), instant(10))]:
            db.session.add(WorkSession(user_id=user.id, start=start, end=end))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()
        db.session.add(WorkSession(user_id=user.id, start=instant(10), end=instant(11)))
        db.session.commit()
        assert WorkSession.query.count() == 2


def test_database_rejects_second_open_session(app):
    with app.app_context():
        user_id = User.query.one().id
        db.session.add(WorkSession(user_id=user_id, start=instant(9)))
        db.session.commit()
        db.session.add(WorkSession(user_id=user_id, start=instant(10)))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert WorkSession.query.count() == 1


def test_void_history_is_retained_and_excluded_from_open_session(app):
    with app.app_context():
        user = User.query.one()
        record, _ = attendance.clock_in(user.id)
        db.session.commit()
        attendance.void(user.id, record, record.version, 'Synthetic correction of mistaken entry')
        db.session.commit()
        assert user.open_session() is None
        assert WorkSession.query.count() == 1
        assert AttendanceAudit.query.count() == 2
        before_count = AttendanceAudit.query.count()
        with pytest.raises(attendance.AttendanceError):
            attendance.void(user.id, record, record.version, 'Repeated void')
        db.session.rollback()
        assert AttendanceAudit.query.count() == before_count


def test_postgres_competing_clock_ins_create_one_record_and_audit(app):
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('Row-lock concurrency is verified on PostgreSQL')
        user_id = User.query.one().id
    barrier = Barrier(2)
    def request():
        with app.app_context():
            barrier.wait(timeout=10)
            record, created = attendance.clock_in(user_id)
            db.session.commit()
            return record.id, created
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: request(), range(2)))
    assert results[0][0] == results[1][0]
    assert sum(created for _, created in results) == 1
    with app.app_context():
        assert WorkSession.query.count() == AttendanceAudit.query.count() == 1


def test_postgres_direct_competing_closed_inserts_cannot_overlap(app):
    with app.app_context():
        engine = db.engine
        if engine.dialect.name != 'postgresql':
            pytest.skip('Concurrent exclusion enforcement is verified on PostgreSQL')
        user_id = User.query.one().id
    barrier = Barrier(2)
    def insert():
        with Session(engine) as session:
            barrier.wait(timeout=10)
            session.add(WorkSession(user_id=user_id, start=instant(9), end=instant(11)))
            try:
                session.commit()
                return True
            except (IntegrityError, OperationalError) as error:
                session.rollback()
                if isinstance(error, OperationalError) and getattr(error.orig, 'sqlstate', None) != '40P01':
                    raise
                return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: insert(), range(2)))
    assert sorted(results) == [False, True]


def test_migration_converts_existing_local_rows_and_baselines_history(database_url):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': database_url})
    with app.app_context():
        upgrade(revision='0001_initial')
        db.session.execute(text('''INSERT INTO "user" (id,name,email,password_hash,is_admin,active,vacation_days,color,created_at)
            VALUES (1,'Synthetic','migration@example.invalid','not-a-real-hash',true,true,22,'#123456',:created)''').bindparams(bindparam('created', type_=DateTime())), {'created': datetime(2026, 7, 1)})
        db.session.execute(text('''INSERT INTO work_session (user_id,start,"end",note)
            VALUES (1,:start,:end,'Preserved legacy note')''').bindparams(bindparam('start', type_=DateTime()), bindparam('end', type_=DateTime())), {'start': datetime(2026, 7, 1, 9), 'end': datetime(2026, 7, 1, 10)})
        db.session.commit()
        upgrade()
        record = WorkSession.query.one()
        assert record.start == datetime(2026, 7, 1, 8, tzinfo=UTC)
        assert record.duration == timedelta(hours=1)
        assert AttendanceAudit.query.one().actor_id is None
        assert AttendanceAudit.query.one().action == 'imported'
        result = app.test_cli_runner().invoke(args=['db', 'check'])
        assert result.exit_code == 0, result.output
        with pytest.raises(SystemExit):
            downgrade(revision='0001_initial')


def test_migration_refuses_ambiguous_legacy_wall_times_without_guessing(database_url):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': database_url})
    with app.app_context():
        upgrade(revision='0001_initial')
        db.session.execute(text('''INSERT INTO "user" (id,name,email,password_hash,is_admin,active,vacation_days,color,created_at)
            VALUES (1,'Synthetic','migration@example.invalid','not-a-real-hash',true,true,22,'#123456',:created)''').bindparams(bindparam('created', type_=DateTime())), {'created': datetime(2026, 10, 1)})
        db.session.execute(text('''INSERT INTO work_session (user_id,start,"end") VALUES (1,:start,:end)''').bindparams(bindparam('start', type_=DateTime()), bindparam('end', type_=DateTime())),
                           {'start': datetime(2026, 10, 25, 1, 30), 'end': datetime(2026, 10, 25, 2, 30)})
        db.session.commit()
        with pytest.raises(SystemExit):
            upgrade()
        db.session.rollback()
        assert db.session.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0001_initial'


def test_postgres_competing_clock_outs_record_one_transition(app):
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('Row-lock concurrency is verified on PostgreSQL')
        user_id = User.query.one().id
        attendance.clock_in(user_id)
        db.session.commit()
    barrier = Barrier(2)
    def request():
        with app.app_context():
            barrier.wait(timeout=10)
            result = attendance.clock_out(user_id)
            db.session.commit()
            return result is not None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: request(), range(2)))
    assert sorted(results) == [False, True]
    with app.app_context():
        assert WorkSession.query.one().end is not None
        assert AttendanceAudit.query.count() == 2


def test_postgres_competing_admin_intervals_do_not_create_two_audits(app):
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            pytest.skip('Row-lock concurrency is verified on PostgreSQL')
        user_id = User.query.one().id
    barrier = Barrier(2)
    def request():
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                attendance.correct(user_id, user_id, instant(9), instant(11), '', 'Synthetic concurrent correction')
                db.session.commit()
                return True
            except IntegrityError:
                db.session.rollback()
                return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: request(), range(2)))
    assert sorted(results) == [False, True]
    with app.app_context():
        assert WorkSession.query.count() == AttendanceAudit.query.count() == 1
