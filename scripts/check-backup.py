#!/usr/bin/env python3
"""Disposable encrypted PostgreSQL backup and restore rehearsal.

Creates and removes only uniquely named Docker resources and temporary files.
No backup, key, database, or container output is printed.
"""

import os
from pathlib import Path
import secrets
import sys
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
POSTGRES_IMAGE = "postgres:17-alpine"
PHASE = "starting"
REDACT = []


class CheckFailure(RuntimeError):
    pass


def run(args, *, input_text=None, check=True, timeout=180):
    result = subprocess.run(args, input=input_text, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        detail = (result.stderr or result.stdout)[-500:]
        for secret in REDACT:
            if secret:
                detail = detail.replace(secret, "[redacted]")
        raise CheckFailure(f"Disposable backup rehearsal failed while {PHASE}: {detail.strip()}")
    return result


def docker(*args, **kwargs):
    return run(["docker", *args], **kwargs)


def wait_postgres(name):
    for _ in range(90):
        result = docker("exec", name, "pg_isready", "-U", "postgres", "-d", "bs_manager", check=False)
        if result.returncode == 0:
            return
        time.sleep(1)
    raise CheckFailure("PostgreSQL did not become ready during backup rehearsal")


def psql(name, database, sql):
    docker("exec", "-i", name, "psql", "-U", "postgres", "-d", database, "-v", "ON_ERROR_STOP=1", input_text=sql)


def query(name, database, sql):
    return docker("exec", name, "psql", "-U", "postgres", "-d", database, "-At", "-v", "ON_ERROR_STOP=1", "-c", sql).stdout.strip()


def main():
    global PHASE
    suffix = secrets.token_hex(6)
    prefix = "bs-manager-backup-check-" + suffix
    image = prefix
    network = prefix + "-net"
    source_name = prefix + "-source"
    target_name = prefix + "-target"
    source_volume = prefix + "-source-data"
    target_volume = prefix + "-target-data"
    password = secrets.token_urlsafe(32)
    REDACT.append(password)
    created_image = False
    created_network = False
    created_volumes = []
    created_containers = []

    try:
        with tempfile.TemporaryDirectory(prefix=prefix + "-") as temporary:
            temp = Path(temporary)
            keys = temp / "keys"
            backups = temp / "backups"
            keys.mkdir(mode=0o700)
            backups.mkdir(mode=0o700)
            pgpass = temp / "pgpass"
            pgpass.write_text(f"source:5432:bs_manager:postgres:{password}\ntarget:5432:bs_manager:postgres:{password}\n")
            pgpass.chmod(0o600)

            PHASE = "building the backup image"
            docker("build", "--tag", image, str(ROOT / "docker" / "backup"), timeout=600)
            created_image = True
            PHASE = "creating isolated Docker resources"
            docker("network", "create", network)
            created_network = True
            for volume in (source_volume, target_volume):
                docker("volume", "create", volume)
                created_volumes.append(volume)

            PHASE = "starting disposable PostgreSQL containers"
            docker("run", "--detach", "--name", source_name, "--network", network, "--network-alias", "source",
                   "--publish", "127.0.0.1::5432", "--volume", source_volume + ":/var/lib/postgresql/data", "--env", "POSTGRES_DB=bs_manager",
                   "--env", "POSTGRES_USER=postgres", "--env", "POSTGRES_PASSWORD=" + password, POSTGRES_IMAGE)
            created_containers.append(source_name)
            docker("run", "--detach", "--name", target_name, "--network", network, "--network-alias", "target",
                   "--publish", "127.0.0.1::5432", "--volume", target_volume + ":/var/lib/postgresql/data", "--env", "POSTGRES_DB=bs_manager",
                   "--env", "POSTGRES_USER=postgres", "--env", "POSTGRES_PASSWORD=" + password, POSTGRES_IMAGE)
            created_containers.append(target_name)
            wait_postgres(source_name)
            wait_postgres(target_name)

            PHASE = "loading synthetic source schema and rows"
            psql(source_name, "bs_manager", """
                CREATE TABLE staff (id integer PRIMARY KEY, name text NOT NULL);
                CREATE TABLE work_log (id integer PRIMARY KEY, staff_id integer NOT NULL REFERENCES staff(id),
                    details jsonb NOT NULL, hours numeric(5,2) NOT NULL);
                CREATE TABLE audit_record (id integer PRIMARY KEY, reason text NOT NULL);
                CREATE FUNCTION reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='audit rows are immutable'; END; $$;
                CREATE TRIGGER audit_record_immutable BEFORE UPDATE OR DELETE ON audit_record
                    FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
                INSERT INTO staff VALUES (7, 'Synthetic Staff');
                INSERT INTO work_log VALUES (11, 7, '{"note":"encrypted backup sentinel","labels":["alpha","beta"]}', 2.75);
                INSERT INTO audit_record VALUES (13, 'synthetic immutable audit');
            """)

            PHASE = "migrating and populating the complete application schema"
            from app import create_app, db
            from app.models import User, TaskEntry, Event
            from app.services import attendance, leave
            from app.attendance_time import local_to_utc
            from flask_migrate import upgrade
            from sqlalchemy.engine import URL
            from datetime import date, datetime
            def application(container, username="postgres", db_password=password):
                port = docker('port', container, '5432').stdout.strip().split(':')[-1]
                url = URL.create('postgresql+psycopg', username=username, password=db_password,
                                 host='127.0.0.1', port=int(port), database='bs_manager')
                return create_app({'TESTING':True,'SECRET_KEY':secrets.token_hex(32),
                                   'SQLALCHEMY_DATABASE_URI':url.render_as_string(hide_password=False)})
            source_app=application(source_name)
            with source_app.app_context():
                upgrade()
                admin=User(name='Synthetic restore admin',email='restore@example.invalid',is_admin=True)
                admin.set_password('synthetic-restore-password')
                db.session.add(admin);db.session.flush()
                attendance.correct(admin.id,admin.id,local_to_utc('2026-10-28T09:00'),
                                   local_to_utc('2026-10-28T10:30'),'Synthetic attendance','Restore sentinel')
                request=leave.create(admin.id,'ferias',date(2026,12,21),date(2026,12,22),'Synthetic leave')
                leave.transition(admin,request,'aprovar','Synthetic decision')
                db.session.add(TaskEntry(user_id=admin.id,date=date(2026,10,28),title='Restore work log',hours=1.5))
                db.session.add(Event(created_by_id=admin.id,title='Restore event',start=datetime(2026,10,28,11)))
                db.session.commit();db.session.remove();db.engine.dispose()

            PHASE = "generating temporary age identities"
            identities = docker("run", "--rm", "--volume", str(keys) + ":/keys", "--entrypoint", "/bin/sh", image,
                                 "-c", "umask 077; age-keygen -o /keys/identity >/dev/null 2>&1; age-keygen -y /keys/identity > /keys/recipients")
            del identities
            recipients = keys / "recipients"
            recipients.chmod(0o600)
            if not recipients.read_text().strip().startswith("age1"):
                raise CheckFailure("Could not prepare synthetic age recipient")
            wrong_keygen = docker("run", "--rm", "--volume", str(keys) + ":/keys", "--entrypoint", "/bin/sh", image,
                                  "-c", "umask 077; age-keygen -o /keys/wrong-identity >/dev/null 2>&1")
            del wrong_keygen
            (keys / "wrong-identity").chmod(0o600)
            REDACT.extend([(keys / "identity").read_text().strip(),
                           (keys / "wrong-identity").read_text().strip()])

            backup_env = ["--env", "PGHOST=source", "--env", "PGPORT=5432", "--env", "PGUSER=postgres",
                          "--env", "PGDATABASE=bs_manager", "--env", "PGPASSFILE=/run/pgpass",
                          "--env", "BACKUP_DIR=/backups", "--env", "BACKUP_RECIPIENTS_FILE=/run/recipients"]
            # Docker Desktop maps mode-0600 bind mounts to root ownership;
            # Linux retains host ownership. Match the owner seen inside Docker,
            # while dropping capabilities and keeping the root filesystem read-only.
            backup_uid = docker('run','--rm','--volume',str(pgpass)+':/run/pgpass:ro',
                '--entrypoint','stat',image,'-c','%u:%g','/run/pgpass').stdout.strip()
            import re
            assert re.fullmatch(r'\d+:\d+', backup_uid)
            PHASE = "creating encrypted backup"
            docker("run", "--rm", "--network", network, "--user", backup_uid,
                   "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", *backup_env,
                   "--volume", str(backups) + ":/backups", "--volume", str(pgpass) + ":/run/pgpass:ro",
                   "--volume", str(recipients) + ":/run/recipients:ro", image, timeout=300)
            archives = sorted(backups.glob("bs-manager-*.age"))
            if len(archives) != 1 or archives[0].stat().st_mode & 0o777 != 0o600:
                raise CheckFailure("Encrypted archive missing or did not use mode 0600")
            if list(backups.glob("*.partial")) or list(backups.glob(".*.partial")):
                raise CheckFailure("Partial archive was left behind after success")
            archive = archives[0]
            PHASE = "checking backup failure leaves no published or partial archive"
            bad_env = ["--env", "PGHOST=source", "--env", "PGUSER=postgres", "--env", "PGDATABASE=missing_database",
                       "--env", "PGPASSFILE=/run/pgpass", "--env", "BACKUP_RECIPIENTS_FILE=/run/recipients"]
            failure=docker("run", "--rm", "--network", network, *bad_env,
                "--volume", str(backups)+":/backups", "--volume", str(pgpass)+":/run/pgpass:ro",
                "--volume", str(recipients)+":/run/recipients:ro", image, check=False)
            assert failure.returncode != 0
            assert sorted(backups.iterdir()) == [archive]

            # Add a guard row, then ensure invalid encrypted inputs fail without running pg_restore.
            PHASE = "checking corrupt and wrong-key rejection"
            psql(target_name, "bs_manager", "CREATE TABLE restore_guard (value text NOT NULL); INSERT INTO restore_guard VALUES ('unchanged');")
            truncated = backups / "truncated.age"
            encrypted = archive.read_bytes()
            truncated.write_bytes(encrypted[: max(1, len(encrypted) // 2)])
            truncated.chmod(0o600)
            wrong_recipient = keys / "wrong-recipients"
            wrong_recipient.write_text(docker("run", "--rm", "--volume", str(keys) + ":/keys:ro", "--entrypoint", "/bin/sh", image,
                                               "-c", "age-keygen -y /keys/wrong-identity").stdout)
            wrong_recipient.chmod(0o600)
            for bad_archive, identity_file in ((truncated, keys / "identity"), (archive, keys / "wrong-identity")):
                result = docker("run", "--rm", "--volume", str(backups) + ":/backups:ro", "--volume", str(keys) + ":/keys:ro",
                                "--entrypoint", "/bin/sh", image, "-c",
                                f"age --decrypt --identity /keys/{identity_file.name} /backups/{bad_archive.name} >/dev/null 2>&1", check=False)
                if result.returncode == 0:
                    raise CheckFailure("Corrupt or wrong-key archive unexpectedly decrypted")
                if query(target_name, "bs_manager", "SELECT value FROM restore_guard") != "unchanged":
                    raise CheckFailure("A rejected archive changed the restore target")
            truncated.unlink()

            psql(target_name, "bs_manager", "DROP TABLE restore_guard;")
            restore_command = (
                "set -eu; umask 077; "
                "age --decrypt --identity /keys/identity /backups/" + archive.name + " > /dev/shm/restore.dump; "
                "pg_restore --list /dev/shm/restore.dump >/dev/null; "
                "pg_restore --exit-on-error --no-owner --no-acl --dbname=bs_manager /dev/shm/restore.dump; "
                "rm -f /dev/shm/restore.dump"
            )
            PHASE = "restoring the validated archive"
            docker("run", "--rm", "--network", network, "--volume", str(backups) + ":/backups:ro",
                   "--volume", str(keys / "identity") + ":/keys/identity:ro", "--volume", str(pgpass) + ":/run/pgpass:ro",
                   "--env", "PGHOST=target", "--env", "PGPORT=5432", "--env", "PGUSER=postgres",
                   "--env", "PGDATABASE=bs_manager", "--env", "PGPASSFILE=/run/pgpass",
                   "--entrypoint", "/bin/sh", image, "-c", restore_command, timeout=300)

            PHASE = "verifying restored data and triggers"
            if query(target_name, "bs_manager", "SELECT name FROM staff WHERE id=7") != "Synthetic Staff":
                raise CheckFailure("Restored staff row did not match")
            if query(target_name, "bs_manager", "SELECT details->>'note' || '|' || (details->'labels')::text || '|' || hours FROM work_log WHERE id=11") != 'encrypted backup sentinel|["alpha", "beta"]|2.75':
                raise CheckFailure("Restored work-log row did not match")
            if query(target_name, "bs_manager", "SELECT reason FROM audit_record WHERE id=13") != "synthetic immutable audit":
                raise CheckFailure("Restored audit row did not match")
            mutation = docker("exec", target_name, "psql", "-U", "postgres", "-d", "bs_manager", "-v", "ON_ERROR_STOP=1",
                              "-c", "UPDATE audit_record SET reason='changed' WHERE id=13", check=False)
            if mutation.returncode == 0 or query(target_name, "bs_manager", "SELECT reason FROM audit_record WHERE id=13") != "synthetic immutable audit":
                raise CheckFailure("Restored immutable audit trigger did not remain active")

            PHASE = "verifying full application login, history and totals after restore"
            from app.models import WorkSession, AttendanceAudit, LeaveRequest, LeaveAudit
            restricted_password=secrets.token_hex(32)
            REDACT.append(restricted_password)
            psql(target_name, 'bs_manager', "CREATE ROLE bsmanager LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '"+restricted_password+"';" + """
                REVOKE CREATE ON SCHEMA public FROM PUBLIC;
                GRANT USAGE ON SCHEMA public TO bsmanager;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bsmanager;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bsmanager;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bsmanager;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO bsmanager;
            """)
            restored=application(target_name,'bsmanager',restricted_password)
            with restored.app_context():
                assert User.query.one().check_password('synthetic-restore-password')
                assert WorkSession.query.one().hours == 1.5
                assert AttendanceAudit.query.one().reason == 'Restore sentinel'
                assert LeaveRequest.query.one().status == 'aprovado'
                assert LeaveAudit.query.count() == 2
                assert TaskEntry.query.one().title == 'Restore work log'
                assert Event.query.one().title == 'Restore event'
                from sqlalchemy import text
                from sqlalchemy.exc import IntegrityError, ProgrammingError
                assert db.session.execute(text('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')).scalar() is False
                try:
                    db.session.execute(text("UPDATE attendance_audit SET reason='changed'"))
                except IntegrityError:
                    db.session.rollback()
                else:
                    raise CheckFailure('Restored application role could mutate audit history')
                try:
                    db.session.execute(text('CREATE TABLE unauthorized_recovery_check (id integer)'))
                except ProgrammingError:
                    db.session.rollback()
                else:
                    raise CheckFailure('Restored application role could create schema objects')
            client=restored.test_client()
            assert client.get('/health/ready').status_code == 200
            login_form=client.get('/login').text
            import re
            token=re.search(r'name="csrf_token"[^>]*value="([^"]+)"',login_form).group(1)
            assert client.post('/login',data={'email':'restore@example.invalid','password':'synthetic-restore-password','csrf_token':token}).status_code == 302
            assert client.get('/picagens/?mes=2026-10').status_code == 200
            assert client.get('/ferias/?ano=2026').status_code == 200
            with restored.app_context():db.session.remove();db.engine.dispose()

            PHASE = "checking encrypted archive freshness"
            freshness = docker("run", "--rm", "--volume", str(backups) + ":/backups:ro", "--env", "BACKUP_DIR=/backups",
                               image, "--check-freshness", "36")
            if "freshness check passed" not in freshness.stdout:
                raise CheckFailure("Freshness check did not pass for the new archive")

            print("PASS: encrypted custom-format backup, private output permissions, corrupt/wrong-key rejection, disposable restore, full application schema/data, restored restricted-role login/readiness, attendance totals/history, leave decisions, foreign keys and audit triggers verified.")
    finally:
        for container in reversed(created_containers):
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, timeout=60)
        for volume in reversed(created_volumes):
            subprocess.run(["docker", "volume", "rm", volume], capture_output=True, timeout=60)
        if created_network:
            subprocess.run(["docker", "network", "rm", network], capture_output=True, timeout=60)
        if created_image:
            subprocess.run(["docker", "image", "rm", image], capture_output=True, timeout=120)


if __name__ == "__main__":
    try:
        main()
    except (CheckFailure, subprocess.TimeoutExpired, FileNotFoundError) as error:
        raise SystemExit(str(error) or "Docker backup rehearsal failed") from None
