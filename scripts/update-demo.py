#!/usr/bin/env python3
"""Image-only update of the existing synthetic demo, with encrypted backup.

Execute privately with sudo on bs-manager-staging. The independently verified
archive checksum must come from a reviewed clean Mac commit, not from an
untrusted archive supplier. No migrations, volume deletion or Access changes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import tarfile
import urllib.request

BASE = Path('/home/bsmanager/bs-manager-preview')
MANAGED = Path('/var/lib/bs-manager-staging')
PROJECT = 'bs-manager-staging'
EXPECTED_HEAD = '0003_staff'
DOCKER = '/usr/bin/docker'
TABLES = ('user', 'work_session', 'attendance_audit', 'task_entry', 'leave_request',
          'leave_audit', 'leave_allowance', 'event', 'alembic_version')


def validate_archive(payload, digest, commit):
    """Validate immutable bytes; checksum trust is supplied by the operator."""
    if not re.fullmatch(r'[0-9a-f]{40}', commit) or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('Invalid release identity.')
    if len(payload) > 30*1024*1024 or hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError('Release archive size/checksum mismatch.')
    prefix = 'release-'+commit
    with tarfile.open(fileobj=io.BytesIO(payload)) as source:
        if source.pax_headers.get('comment') != commit:
            raise ValueError('Archive comment differs from the expected source identity.')
        members = source.getmembers()
        if len(members)>1000 or sum(item.size for item in members)>20*1024*1024:
            raise ValueError('Archive exceeds expected limits.')
        names=set()
        for item in members:
            parts=Path(item.name).parts
            if (not parts or parts[0]!=prefix or item.name.startswith('/') or '..' in parts
                    or not (item.isdir() or item.isfile()) or item.name in names):
                raise ValueError('Unsafe/duplicate archive member.')
            names.add(item.name)
        for name in ('Dockerfile','docker-compose.yml','docker-compose.pilot.yml','app/__init__.py'):
            if prefix+'/'+name not in names:raise ValueError('Incomplete application archive.')
    return prefix


def extract_archive(payload, destination):
    # The same validated bytes are extracted; the caller-owned path is never reopened.
    destination.mkdir(mode=0o755); destination.chmod(0o755)
    with tarfile.open(fileobj=io.BytesIO(payload)) as source:
        for item in source.getmembers():
            target=destination.joinpath(*Path(item.name).parts[1:])
            if item.isdir():
                target.mkdir(parents=True,exist_ok=True,mode=0o755);target.chmod(0o755)
            else:
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
                with target.open('xb') as output:output.write(source.extractfile(item).read())
                target.chmod(0o755 if item.mode & 0o111 else 0o644)


def recover(service, pointer, report):
    """Try service recovery even if pointer recovery or reporting fails."""
    errors=[]
    for name, action in [('service',service),('pointer',pointer),('report',report)]:
        try:action()
        except BaseException:errors.append(name)
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--recipient-file',required=True,type=Path)
    args=parser.parse_args()
    if os.geteuid()!=0 or socket.gethostname()!='bs-manager-staging':
        raise SystemExit('Run privately with sudo only on bs-manager-staging.')
    if not BASE.is_dir() or not (BASE/'current').is_symlink():
        raise SystemExit('Expected existing demo; no bootstrap/reset is allowed.')
    os.umask(0o077)
    MANAGED.mkdir(mode=0o755,exist_ok=True)
    parent=MANAGED.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=0 or parent.st_mode & 0o022:
        raise SystemExit('Managed deployment parent must be root-owned and non-writable by others.')
    if args.archive.stat().st_size>30*1024*1024:raise SystemExit('Release archive is too large.')
    payload=args.archive.read_bytes()
    prefix=validate_archive(payload,args.sha256,args.commit)
    recipient=args.recipient_file.read_text().strip()
    if not re.fullmatch(r'age1[0-9a-z]{58}',recipient):raise SystemExit('Expected an age public recipient only.')
    if shutil.disk_usage(BASE).free<4*2**30:raise SystemExit('At least 4 GiB free is required; no resize is allowed.')
    state_dir=MANAGED/args.commit
    if state_dir.exists():raise SystemExit('Update directory exists; reconcile before retrying.')
    state_dir.mkdir(mode=0o700)
    release=MANAGED/prefix
    if release.exists():raise SystemExit('Release exists; refusing overwrite.')
    extract_archive(payload,release)
    # Snapshot the existing credential file once into a root-private directory.
    descriptor=os.open(BASE/'preview.env',os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>65536:
            raise SystemExit('Expected a private regular environment file.')
        config=state_dir/'preview.env'
        with os.fdopen(descriptor,'rb',closefd=False) as source,config.open('xb') as output:
            output.write(source.read())
    finally:os.close(descriptor)
    record={'source_commit':args.commit,'archive_sha256':args.sha256,'project':PROJECT,
            'phase':'preflight','started_at':datetime.now(timezone.utc).isoformat()}
    def run(command,timeout=900,env=None):
        result=subprocess.run(command,capture_output=True,text=True,timeout=timeout,env=env)
        if result.returncode:raise RuntimeError('Operation failed during '+record['phase']+'; exit '+str(result.returncode))
        return result.stdout.strip()
    def export(name,payload):
        # Drop privilege before writing into the operator's user-owned directory.
        code="""import os,sys
from pathlib import Path
root=Path.home()/'bs-manager-updates'/sys.argv[1]
root.mkdir(parents=True,exist_ok=True,mode=0o700)
fd=os.open(root/sys.argv[2],os.O_WRONLY|os.O_CREAT|os.O_TRUNC|getattr(os,'O_NOFOLLOW',0),0o600)
with os.fdopen(fd,'wb') as output:output.write(sys.stdin.buffer.read())
"""
        result=subprocess.run(['/usr/sbin/runuser','-u','bsmanager','--','/usr/bin/python3','-c',code,args.commit,name],input=payload,capture_output=True,timeout=60)
        return result.returncode==0
    def save():
        data=(json.dumps(record,indent=2)+'\n').encode()
        temporary=state_dir/'result.tmp'
        with temporary.open('wb') as output:output.write(data);output.flush();os.fsync(output.fileno())
        os.replace(temporary,state_dir/'result.json')
        export('result.json',data)  # Root-owned record remains authoritative if export fails.
    command=[DOCKER,'compose','--project-name',PROJECT,'--env-file',str(config),
             '-f',str(release/'docker-compose.yml'),'-f',str(release/'docker-compose.pilot.yml')]
    image='bs-manager-staging:'+args.commit
    def compose(*arguments,image_override=image):
        return run(command+list(arguments),env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','BS_MANAGER_IMAGE':image_override})
    def container(service):
        value=run([DOCKER,'ps','--filter','label=com.docker.compose.project='+PROJECT,
                   '--filter','label=com.docker.compose.service='+service,'--format','{{.ID}}'])
        if not re.fullmatch(r'[0-9a-f]{12,64}',value):raise RuntimeError('Expected one existing '+service+' container.')
        return value
    web,database=container('web'),container('db')
    old_image=run([DOCKER,'inspect','--format','{{.Image}}',web])
    bindings=json.loads(run([DOCKER,'inspect','--format','{{json .HostConfig.PortBindings}}',web]))
    if bindings!={'8000/tcp':[{'HostIp':'127.0.0.1','HostPort':'8000'}]}:raise SystemExit('Unexpected web exposure.')
    if json.loads(run([DOCKER,'inspect','--format','{{json .HostConfig.PortBindings}}',database])):raise SystemExit('Database host exposure is forbidden.')
    def sql(query):return run([DOCKER,'exec',database,'psql','-U','bsmanager_owner','-d','bsmanager','-At','-v','ON_ERROR_STOP=1','-c',query])
    if sql('SELECT version_num FROM alembic_version')!=EXPECTED_HEAD:raise SystemExit('Existing schema is not at the required head; no migrations are run.')
    # Require the exact already-used infrastructure definitions before reusing them.
    old_release=(BASE/'current').resolve()
    immutable_files=['docker-compose.yml','docker-compose.pilot.yml','docker/init-db.sql']
    immutable_files += sorted(str(path.relative_to(release)) for path in (release/'migrations/versions').glob('*.py'))
    for name in immutable_files:
        observed=run(['/usr/sbin/runuser','-u','bsmanager','--','sha256sum',str(old_release/name)]).split()[0]
        if observed!=hashlib.sha256((release/name).read_bytes()).hexdigest():
            raise SystemExit('Infrastructure/migration source differs; this image-only updater refuses '+name)
    def fingerprint():
        result={}
        for table in TABLES:
            query='SET TIME ZONE \'UTC\'; SELECT count(*)::text || \':\' || md5(COALESCE(string_agg(row_to_json(t)::text,E\'\\n\' ORDER BY row_to_json(t)::text),\'\')) FROM "'+table+'" t;'
            result[table]=sql(query).splitlines()[-1]
        return result
    rollback_image='bs-manager-staging:rollback-'+old_image.removeprefix('sha256:')[:12]
    record.update(previous_image=old_image,rollback_image=rollback_image,image=image)
    record['phase']='build';save()
    run([DOCKER,'image','tag',old_image,rollback_image])
    compose('build','--build-arg','SOURCE_COMMIT='+args.commit,'web')
    heads=run([DOCKER,'run','--rm','--network','none','--entrypoint','python',image,'-c',"from alembic.script import ScriptDirectory; print(','.join(sorted(ScriptDirectory('/app/migrations').get_heads())))"])
    if heads!=EXPECTED_HEAD:raise SystemExit('Image requires a different migration head; no deployment performed.')
    record['python_packages']=json.loads(run([DOCKER,'run','--rm','--network','none','--entrypoint','python',image,'-c',"import importlib.metadata as m,json; print(json.dumps(sorted(d.metadata['Name']+'=='+d.version for d in m.distributions())))"]))
    save()
    backup_image='bs-manager-backup:'+args.commit
    run([DOCKER,'build','-t',backup_image,str(release/'docker/backup')])
    previous_pointer=(MANAGED/'current').readlink() if (MANAGED/'current').is_symlink() else None
    recovery_needed=False
    def restore_pointer():
        link=MANAGED/'current.pending'
        link.unlink(missing_ok=True)
        if previous_pointer is None:(MANAGED/'current').unlink(missing_ok=True)
        else:link.symlink_to(previous_pointer);os.replace(link,MANAGED/'current')
    try:
        record['phase']='backup';save()
        recovery_needed=True  # A failed/timed-out stop can still have stopped the service.
        compose('stop','--timeout','30','web',image_override=rollback_image)
        record['before']=fingerprint();save()
        backup=state_dir/'pre-update.age';partial=state_dir/'pre-update.partial'
        dump=subprocess.Popen([DOCKER,'exec',database,'pg_dump','-U','bsmanager_owner','-d','bsmanager','--format=custom','--no-owner','--no-acl'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            with partial.open('xb') as output:
                encrypted=subprocess.run([DOCKER,'run','--rm','-i','--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--entrypoint','age',backup_image,'--encrypt','--recipient',recipient],stdin=dump.stdout,stdout=output,stderr=subprocess.PIPE,timeout=120)
            dump.stdout.close();dump.communicate(timeout=120)
            if dump.returncode or encrypted.returncode or partial.stat().st_size<100:raise RuntimeError('Dump/encryption failed.')
            partial.rename(backup)
        finally:
            if dump.poll() is None:dump.kill();dump.wait()
            partial.unlink(missing_ok=True)
        if not export('pre-update.age',backup.read_bytes()):raise RuntimeError('Encrypted backup could not be exported to the operator.')
        record['backup_sha256']=hashlib.sha256(backup.read_bytes()).hexdigest();save()
        if fingerprint()!=record['before']:raise RuntimeError('Records changed while the application was stopped.')
        record['phase']='activate';save()
        compose('up','-d','--wait','--no-deps','--force-recreate','web')
        with urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=10) as response:
            if response.status!=200 or json.load(response)!={'status':'ok'}:raise RuntimeError('Readiness failed.')
        active_web=container('web')
        record['image_id']=run([DOCKER,'inspect','--format','{{.Image}}',active_web])
        revision=run([DOCKER,'image','inspect','--format','{{index .Config.Labels "org.opencontainers.image.revision"}}',record['image_id']])
        if revision!=args.commit:raise RuntimeError('Active image revision differs from the reviewed commit.')
        link=MANAGED/'current.pending';link.symlink_to(release);os.replace(link,MANAGED/'current')
        record['phase']='healthy';record['completed_at']=datetime.now(timezone.utc).isoformat();save()
        print('Demo updated. Database, credentials and connector retained. Encrypted backup and previous image recorded; off-host restore and Access verification remain required.')
    except BaseException:
        record['phase']='rollback'
        errors=recover(lambda:compose('up','-d','--wait','--no-deps','--force-recreate','web',image_override=rollback_image) if recovery_needed else None,restore_pointer,save)
        record['phase']='rollback_failed' if any(name!='report' for name in errors) else 'rolled_back'
        try:save()
        except BaseException:pass
        if errors:print('Recovery actions needing operator review: '+', '.join(errors))
        raise


if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as error:raise SystemExit(str(error)) from None
