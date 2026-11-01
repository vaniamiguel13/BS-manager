"""UTC attendance, overlap protection and retained correction history.

Revision ID: 0002_attendance
Revises: 0001_initial
"""
from datetime import datetime, timezone
import sqlalchemy as sa
from alembic import op
from flask import current_app
from app.attendance_time import local_to_utc

revision = '0002_attendance'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    old = sa.table('work_session', sa.column('id', sa.Integer), sa.column('user_id', sa.Integer),
                   sa.column('start', sa.DateTime), sa.column('end', sa.DateTime),
                   sa.column('note', sa.String), sa.column('edited_by_id', sa.Integer))
    # Validate every legacy value before changing schema or data. Never guess a DST fold.
    converted = []
    for row in connection.execute(sa.select(old).order_by(old.c.user_id, old.c.start)).mappings():
        try:
            start = local_to_utc(row['start'], timezone_name=current_app.config['APP_TIMEZONE'])
            end = local_to_utc(row['end'], timezone_name=current_app.config['APP_TIMEZONE']) if row['end'] else None
        except ValueError as error:
            raise RuntimeError('Legacy attendance requires explicit DST resolution before migration (record ' + str(row['id']) + ').') from error
        if end is not None and end <= start:
            raise RuntimeError('Legacy attendance has a non-positive interval; resolve it before migration.')
        if converted and converted[-1]['user_id'] == row['user_id']:
            previous = converted[-1]
            if previous['end'] is None or previous['end'] > start:
                raise RuntimeError('Legacy attendance overlaps; resolve it before migration.')
        converted.append({**row, 'start': start, 'end': end, 'legacy_before': {key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}})
    # Store converted UTC wall values before PostgreSQL's explicit AT TIME ZONE cast.
    for row in converted:
        connection.execute(old.update().where(old.c.id == row['id']).values(
            start=row['start'].replace(tzinfo=None), end=row['end'].replace(tzinfo=None) if row['end'] else None))
    with op.batch_alter_table('work_session') as batch:
        batch.alter_column('start', existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True),
                           existing_nullable=False, postgresql_using="start AT TIME ZONE 'UTC'")
        batch.alter_column('end', existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True),
                           existing_nullable=True, postgresql_using='"end" AT TIME ZONE \'UTC\'')
        batch.add_column(sa.Column('voided_at', sa.DateTime(timezone=True)))
        batch.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch.create_check_constraint('ck_work_session_positive', '"end" IS NULL OR "end" > start')
    op.create_index('uq_work_session_open', 'work_session', ['user_id'], unique=True,
                    postgresql_where=sa.text('"end" IS NULL AND voided_at IS NULL'),
                    sqlite_where=sa.text('"end" IS NULL AND voided_at IS NULL'))
    op.create_table('attendance_audit',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('work_session.id'), nullable=False),
        sa.Column('actor_id', sa.Integer(), sa.ForeignKey('user.id')),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('before', sa.JSON()), sa.Column('after', sa.JSON(), nullable=False))
    op.create_index('ix_attendance_audit_session_id', 'attendance_audit', ['session_id'])
    audit = sa.table('attendance_audit', sa.column('session_id', sa.Integer), sa.column('actor_id', sa.Integer),
                     sa.column('action', sa.String), sa.column('recorded_at', sa.DateTime(timezone=True)),
                     sa.column('reason', sa.String), sa.column('before', sa.JSON), sa.column('after', sa.JSON))
    for row in converted:
        snapshot = {key: row[key].isoformat() if row[key] is not None and key in {'start', 'end'} else row[key]
                    for key in ('user_id', 'start', 'end', 'note', 'edited_by_id')}
        connection.execute(audit.insert().values(session_id=row['id'], actor_id=None, action='imported',
            recorded_at=datetime.now(timezone.utc), reason='Legacy baseline converted from '+current_app.config['APP_TIMEZONE']+'; original actor unknown.',
            before=row['legacy_before'], after=snapshot))
    if connection.dialect.name == 'postgresql':
        # Both GiST operands are built-in ranges: no privileged btree_gist extension required.
        op.execute('''ALTER TABLE work_session ADD CONSTRAINT excl_work_session_overlap
          EXCLUDE USING gist ((int8range(user_id::bigint, user_id::bigint, '[]')) WITH &&,
          (tstzrange(start, "end", '[)')) WITH &&) WHERE (voided_at IS NULL)''')
        op.execute('''CREATE FUNCTION attendance_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='Attendance audit records are immutable'; END; $$''')
        op.execute('''CREATE TRIGGER attendance_audit_immutable BEFORE UPDATE OR DELETE ON attendance_audit
            FOR EACH ROW EXECUTE FUNCTION attendance_audit_immutable()''')
    else:
        for action in ('INSERT', 'UPDATE'):
            op.execute(f'''CREATE TRIGGER attendance_overlap_{action.lower()} BEFORE {action} ON work_session
            WHEN NEW.voided_at IS NULL AND EXISTS (SELECT 1 FROM work_session s
              WHERE {('s.id != NEW.id' if action == 'UPDATE' else '1=1')} AND s.user_id=NEW.user_id AND s.voided_at IS NULL
              AND (NEW."end" IS NULL OR s.start < NEW."end") AND (s."end" IS NULL OR s."end" > NEW.start))
            BEGIN SELECT RAISE(ABORT, 'Attendance sessions overlap'); END''')
        for action in ('UPDATE', 'DELETE'):
            op.execute(f'''CREATE TRIGGER attendance_audit_{action.lower()} BEFORE {action} ON attendance_audit
                BEGIN SELECT RAISE(ABORT, 'Attendance audit records are immutable'); END''')


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text('SELECT count(*) FROM work_session')).scalar():
        raise RuntimeError('Attendance downgrade with records is unsafe; use a versioned backup instead.')
    if connection.dialect.name == 'postgresql':
        op.execute('DROP TRIGGER attendance_audit_immutable ON attendance_audit')
        op.execute('DROP FUNCTION attendance_audit_immutable()')
        op.execute('ALTER TABLE work_session DROP CONSTRAINT excl_work_session_overlap')
    else:
        for name in ('attendance_overlap_insert', 'attendance_overlap_update', 'attendance_audit_update', 'attendance_audit_delete'):
            op.execute('DROP TRIGGER '+name)
    op.drop_table('attendance_audit')
    op.drop_index('uq_work_session_open', table_name='work_session')
    with op.batch_alter_table('work_session') as batch:
        batch.drop_constraint('ck_work_session_positive', type_='check')
        batch.drop_column('voided_at')
        batch.drop_column('version')
        batch.alter_column('start', existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(), existing_nullable=False)
        batch.alter_column('end', existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(), existing_nullable=True)
