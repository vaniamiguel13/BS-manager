"""Retained leave decisions, schedules, annual allowances and revocable sessions."""
import secrets
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

revision = '0003_staff'
down_revision = '0002_attendance'
branch_labels = depends_on = None


def upgrade():
    c = op.get_bind()
    bad = c.execute(sa.text('''SELECT count(*) FROM leave_request WHERE end_date < start_date
      OR status NOT IN ('pendente','aprovado','rejeitado','cancelado')
      OR kind NOT IN ('ferias','falta','baixa','formacao','teletrabalho','outro')''')).scalar()
    overlap = c.execute(sa.text("""SELECT count(*) FROM leave_request a JOIN leave_request b
      ON a.id < b.id AND a.user_id=b.user_id AND a.start_date <= b.end_date AND a.end_date >= b.start_date
      WHERE a.status IN ('pendente','aprovado') AND b.status IN ('pendente','aprovado')""")).scalar()
    if bad or overlap:
        raise RuntimeError('Resolve invalid legacy leave requests before upgrading.')
    with op.batch_alter_table('user') as b:
        b.add_column(sa.Column('session_token', sa.String(64), nullable=False, server_default=''))
        b.add_column(sa.Column('working_weekdays', sa.String(13), nullable=False, server_default='0,1,2,3,4'))
    for user_id in c.execute(sa.text('SELECT id FROM "user"')).scalars():
        c.execute(sa.text('UPDATE "user" SET session_token=:token WHERE id=:id'), {'id':user_id, 'token':secrets.token_hex(32)})
    op.create_index('ix_user_session_token', 'user', ['session_token'], unique=True)
    with op.batch_alter_table('leave_request') as b:
        b.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        b.add_column(sa.Column('working_weekdays', sa.String(13), nullable=False, server_default='0,1,2,3,4'))
        b.create_check_constraint('ck_leave_dates', 'end_date >= start_date')
        b.create_check_constraint('ck_leave_status', "status IN ('pendente','aprovado','rejeitado','cancelado')")
        b.create_check_constraint('ck_leave_kind', "kind IN ('ferias','falta','baixa','formacao','teletrabalho','outro')")
    op.create_table('leave_allowance', sa.Column('user_id',sa.Integer(),sa.ForeignKey('user.id'),primary_key=True),
        sa.Column('year',sa.Integer(),primary_key=True), sa.Column('days',sa.Integer(),nullable=False),
        sa.CheckConstraint('days >= 0 AND days <= 366',name='ck_allowance_days'))
    op.create_table('login_throttle',sa.Column('key',sa.String(64),primary_key=True),
        sa.Column('failures',sa.Integer(),nullable=False),sa.Column('window_start',sa.DateTime(timezone=True),nullable=False),
        sa.Column('blocked_until',sa.DateTime(timezone=True)))
    op.create_table('leave_audit',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('leave_id',sa.Integer(),sa.ForeignKey('leave_request.id'),nullable=False),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('user.id')),sa.Column('action',sa.String(20),nullable=False),
        sa.Column('recorded_at',sa.DateTime(timezone=True),nullable=False),sa.Column('before',sa.JSON()),sa.Column('after',sa.JSON(),nullable=False))
    op.create_index('ix_leave_audit_leave_id','leave_audit',['leave_id'])
    table=sa.table('leave_audit',sa.column('leave_id',sa.Integer),sa.column('actor_id',sa.Integer),sa.column('action',sa.String),sa.column('recorded_at',sa.DateTime(timezone=True)),sa.column('after',sa.JSON))
    for row in c.execute(sa.text('SELECT * FROM leave_request')).mappings():
        c.execute(table.insert().values(leave_id=row['id'],actor_id=None,action='imported',recorded_at=datetime.now(timezone.utc),
             after={k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items()}))
    if c.dialect.name == 'postgresql':
        op.execute('''ALTER TABLE leave_request ADD CONSTRAINT excl_leave_overlap EXCLUDE USING gist
          ((int8range(user_id::bigint,user_id::bigint,'[]')) WITH &&,
          (daterange(start_date,end_date,'[]')) WITH &&) WHERE (status IN ('pendente','aprovado'))''')
        op.execute('''CREATE FUNCTION leave_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
           BEGIN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='Leave history is immutable'; END; $$''')
        op.execute('CREATE TRIGGER leave_audit_immutable BEFORE UPDATE OR DELETE ON leave_audit FOR EACH ROW EXECUTE FUNCTION leave_audit_immutable()')
    else:
        for action in ('INSERT','UPDATE'):
            op.execute(f'''CREATE TRIGGER leave_overlap_{action.lower()} BEFORE {action} ON leave_request
               WHEN NEW.status IN ('pendente','aprovado') AND EXISTS (SELECT 1 FROM leave_request r
               WHERE {('r.id != NEW.id' if action=='UPDATE' else '1=1')} AND r.user_id=NEW.user_id
               AND r.status IN ('pendente','aprovado') AND r.start_date <= NEW.end_date AND r.end_date >= NEW.start_date)
               BEGIN SELECT RAISE(ABORT,'Leave requests overlap'); END''')
        for action in ('UPDATE','DELETE'):
            op.execute(f"CREATE TRIGGER leave_audit_{action.lower()} BEFORE {action} ON leave_audit BEGIN SELECT RAISE(ABORT,'Leave history is immutable'); END")


def downgrade():
    c=op.get_bind()
    if c.execute(sa.text('SELECT count(*) FROM leave_request')).scalar() or c.execute(sa.text('SELECT count(*) FROM "user"')).scalar():
        raise RuntimeError('Data-bearing staff workflow downgrade refused; use a verified backup.')
    if c.dialect.name=='postgresql':
        op.execute('DROP FUNCTION leave_audit_immutable() CASCADE')
        op.execute('ALTER TABLE leave_request DROP CONSTRAINT excl_leave_overlap')
    else:
        for name in ('leave_overlap_insert','leave_overlap_update','leave_audit_update','leave_audit_delete'):
            op.execute('DROP TRIGGER '+name)
    for name in ('leave_audit','leave_allowance','login_throttle'):op.drop_table(name)
    with op.batch_alter_table('leave_request') as b:
        for name in ('ck_leave_dates','ck_leave_status','ck_leave_kind'):b.drop_constraint(name,type_='check')
        b.drop_column('version'); b.drop_column('working_weekdays')
    op.drop_index('ix_user_session_token', table_name='user')
    with op.batch_alter_table('user') as b:
        b.drop_column('session_token'); b.drop_column('working_weekdays')
