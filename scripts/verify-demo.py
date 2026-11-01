#!/usr/bin/env python3
"""Verify the existing demo; optionally restart only its committed web container.

Run privately with sudo on bs-manager-staging. Never prints environment values,
records, tokens or passwords. No migrations, credentials or ingress are changed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import time
import urllib.request

DOCKER = '/usr/bin/docker'
MANAGED = Path('/var/lib/bs-manager-staging')
PROJECT = 'bs-manager-staging'
TABLES = ('user', 'work_session', 'attendance_audit', 'task_entry', 'leave_request',
          'leave_audit', 'leave_allowance', 'event', 'alembic_version')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=120)
    require(result.returncode == 0, 'Verification command failed; raw output withheld.')
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--restart-web', action='store_true')
    args = parser.parse_args()
    require(os.geteuid() == 0 and socket.gethostname() == 'bs-manager-staging',
            'Run privately with sudo only on bs-manager-staging.')
    require(re.fullmatch(r'[0-9a-f]{40}', args.commit), 'Invalid commit identity.')
    os.umask(0o077)
    state = MANAGED / args.commit
    info = state.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
            'Expected root-managed deployment state.')
    record = json.loads((state / 'result.json').read_text())
    require(record['source_commit'] == args.commit and record['phase'] == 'healthy',
            'Expected the exact healthy committed deployment.')
    require((MANAGED / 'current').resolve() == MANAGED / ('release-' + args.commit),
            'Deployment pointer differs from the requested release.')

    def container(service):
        value = run([DOCKER, 'ps', '--filter', 'label=com.docker.compose.project=' + PROJECT,
                     '--filter', 'label=com.docker.compose.service=' + service, '--format', '{{.ID}}'])
        require(re.fullmatch(r'[0-9a-f]{12,64}', value), 'Expected one running ' + service + ' container.')
        return value

    web, database = container('web'), container('db')
    observed = json.loads(run([DOCKER, 'inspect', web]))[0]
    require(observed['Image'] == record['image_id'], 'Running image differs from deployment record.')
    require(observed['Config']['User'] not in ('', '0', 'root'), 'Web must run without root.')
    require(observed['HostConfig']['ReadonlyRootfs'], 'Web filesystem must be read-only.')
    require('ALL' in observed['HostConfig']['CapDrop'], 'Web capabilities must be dropped.')
    require(any(value in ('no-new-privileges', 'no-new-privileges:true')
                for value in observed['HostConfig']['SecurityOpt']), 'Privilege escalation must be disabled.')
    require(observed['HostConfig']['PortBindings'] == {
        '8000/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8000'}]}, 'Unexpected web exposure.')
    require(not json.loads(run([DOCKER, 'inspect', '--format', '{{json .HostConfig.PortBindings}}', database])),
            'Database must have no published host port.')
    require(run([DOCKER, 'image', 'inspect', '--format', '{{index .Config.Labels "org.opencontainers.image.revision"}}',
                 observed['Image']]) == args.commit, 'Image revision differs from commit.')
    require(run([DOCKER, 'image', 'inspect', '--format', '{{.Id}}', record['rollback_image']]) == record['previous_image'],
            'Recorded rollback image is unavailable or changed.')
    require(hashlib.sha256((state / 'pre-update.age').read_bytes()).hexdigest() == record['backup_sha256'],
            'Retained encrypted backup digest differs.')

    def fingerprints():
        result = {}
        for table in TABLES:
            query = ("SET TIME ZONE 'UTC'; SELECT count(*)::text || ':' || "
                     "md5(COALESCE(string_agg(row_to_json(t)::text,E'\\n' ORDER BY row_to_json(t)::text),'')) "
                     'FROM "' + table + '" t;')
            result[table] = run([DOCKER, 'exec', database, 'psql', '-U', 'bsmanager_owner', '-d', 'bsmanager',
                                 '-At', '-v', 'ON_ERROR_STOP=1', '-c', query]).splitlines()[-1]
        return result

    require(fingerprints() == record['before'],
            'Records differ from pre-update snapshot; reconcile any concurrent demo edits before acceptance.')
    if args.restart_web:
        print('Restarting only the demo web container; brief interruption expected.', flush=True)
        run([DOCKER, 'restart', '--time', '30', web])
    for attempt in range(45):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3) as response:
                if response.status == 200 and json.load(response) == {'status': 'ok'}:
                    break
        except (OSError, ValueError):
            pass
        time.sleep(2)
    else:
        raise RuntimeError('Readiness did not recover; inspect the recorded rollback procedure.')
    require(container('web') == web, 'Web container changed during verification.')
    require(fingerprints() == record['before'], 'Records changed during restart acceptance.')
    for service in ('cloudflared.service', 'docker.service', 'ssh.socket'):
        require(run(['systemctl', 'is-active', service]) == 'active', service + ' is not active.')
    token = Path('/etc/cloudflared/token').stat()
    require(token.st_uid == 0 and stat.S_IMODE(token.st_mode) == 0o600, 'Tunnel token permissions differ.')
    run(['/usr/sbin/sshd', '-t'])
    ssh = run(['/usr/sbin/sshd', '-T', '-C',
               'user=bsmanager,host=localhost,addr=127.0.0.1,laddr=127.0.0.1,lport=22'])
    settings = dict(line.split(None, 1) for line in ssh.splitlines() if ' ' in line)
    require(all(settings.get(key) == value for key, value in {
        'pubkeyauthentication': 'yes', 'authenticationmethods': 'publickey',
        'passwordauthentication': 'no', 'kbdinteractiveauthentication': 'no', 'permitrootlogin': 'no'
    }.items()), 'Effective SSH hardening differs.')
    result = {'source_commit': args.commit, 'image_id': record['image_id'],
              'verified_at': datetime.now(timezone.utc).isoformat(), 'runtime_hardening': True,
              'loopback_only_web': True, 'database_not_published': True, 'tables_unchanged': len(TABLES),
              'rollback_image_retained': True, 'backup_digest_verified': True,
              'web_restart_verified': args.restart_web, 'readiness': 'ok',
              'connector_ssh_docker_active': True, 'key_only_ssh': True}
    data = (json.dumps(result, indent=2) + '\n').encode()
    with (state / 'verification.json').open('wb') as output:
        output.write(data)
    code = """from pathlib import Path
import os,sys
p=Path.home()/'bs-manager-updates'/sys.argv[1]/'verification.json'
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as output:output.write(sys.stdin.buffer.read())
"""
    exported = subprocess.run(['/usr/sbin/runuser', '-u', 'bsmanager', '--', '/usr/bin/python3', '-c', code, args.commit],
                              input=data, capture_output=True, timeout=30)
    require(exported.returncode == 0, 'Verification passed but operator report export failed; root report retained.')
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from None
