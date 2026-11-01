# PostgreSQL backup and restore

The backup image is a local building block for PostgreSQL 17. It runs
`pg_dump` in custom archive format and pipes the dump directly into `age`
encryption. The plaintext dump is not written to the backup volume. The
backup process needs only PostgreSQL client credentials, a public age
recipients file, and the backup directory; it must never receive an age
private identity. The image uses the upstream PostgreSQL client image and
Alpine's `age` package ([package details](https://pkgs.alpinelinux.org/package/v3.23/community/x86_64/age),
[age command documentation](https://github.com/FiloSottile/age/blob/main/doc/age.1.ronn)).

The optional Compose `backup` profile implements this contract. It has no
published port, runs with an explicit numeric user, a read-only root filesystem,
no additional capabilities, and no-new-privileges. Its credential/recipient bind
mounts are read-only; only the backup destination is writable. Set its UID/GID to
the owner of these files as seen inside Docker. On Docker Desktop, private
bind mounts can appear root-owned even when the host file belongs to you; verify
mount ownership and set UID/GID accordingly. Keep the capability and filesystem
restrictions. The Linux pilot should use its dedicated operator UID. Paths must already exist; Compose will not create
missing credential directories.

Prepare private paths outside Git, put only the public age recipients into the
recipients file, and create a mode-0600 PostgreSQL password file in this format:

```text
db:5432:bsmanager:bsmanager_owner:<owner database password>
```

The fields are host, port, database, user and password. Escape literal `:` and
`\` in the password as required by PostgreSQL's password-file format. Enter it
privately; never paste the password into a command argument or chat. Configure
`BACKUP_DIR`, `BACKUP_PGPASS_FILE`, `BACKUP_RECIPIENTS_FILE`, `BACKUP_UID` and
`BACKUP_GID` in the host-private `.env`, then run:

```bash
docker compose --profile backup build backup
docker compose run --rm backup
```

What it does: builds the tools image and creates one encrypted database archive
in the pre-existing private destination. It does not install a schedule, apply
retention, or copy the archive off-host. Protect and verify the private files
before running it. The runtime contract is:

- `PGHOST`, `PGPORT`, `PGUSER`, and `PGDATABASE` name the PostgreSQL source.
- `PGPASSFILE` points to a read-only mounted password file. Do not pass the
  database password in command-line arguments or logs.
- `BACKUP_RECIPIENTS_FILE` points to a read-only file with one or more public
  age recipients; it defaults to `/run/secrets/backup_recipients`.
- `BACKUP_DIR` is the writable backup destination; it defaults to `/backups`.
- Mount only the recipients file, password file, and backup destination. Never
  mount the age private identity into the backup service.

Each run creates a mode-0600 partial archive in the destination, streams
`pg_dump --format=custom --no-owner --no-acl` through age, and atomically
publishes a timestamped `.age` file without overwriting an existing name. If
dump or encryption fails, its partial file is removed and the command fails.
No automatic retention deletion is implemented.

## Key handling

Generate an identity on a trusted offline machine, then share only its public
recipient with the backup host:

```bash
age-keygen -o backup-identity.txt
age-keygen -y backup-identity.txt > backup-recipients.txt
chmod 600 backup-identity.txt backup-recipients.txt
```

What it does: creates a private decryption identity and derives its public
recipient list. Store the identity in an independent, encrypted and access-
controlled location. Keep a tested recovery copy separate from the backup host.
The recipient list is public, but protect it from unauthorized modification.

Losing every private identity makes the encrypted archives unrecoverable.
Compromise of a private identity exposes every backup encrypted to its
recipient. Rotate by adding a new recipient to the recipients file, verifying
the new recipient can decrypt a new archive, and retaining the old identity
until all archives encrypted only to it have expired under the approved
retention policy.

## Freshness check

The image has a lightweight check intended for a scheduler or monitor:

```bash
docker compose run --rm backup --check-freshness 36
```

What it does: checks that the newest encrypted archive's filesystem
modification time is no more than 36 hours old. It does not decrypt, validate
the dump, or prove recoverability. Preserve file timestamps when copying or
restoring backup files if monitoring relies on this check. The freshness check
is not a restore rehearsal.

The backup tool requires a writable persistent destination, usually a mounted
directory or volume. Copy encrypted archives off-host to a separate account or
system with independent access controls. A disk or volume on the database host
alone is not a disaster-recovery copy.

## Restore procedure

Restore into a new, empty database. Stop application writes first and verify
that the archive and the correct private identity are available. Keep the age
identity off the backup service. Decrypt into a private temporary filesystem,
inspect the archive, and only then run `pg_restore`. The example below uses a
Docker tmpfs for the plaintext archive; replace the container network, target
host/database, image, and mounted file paths with the approved recovery
environment. The mounted password file must match the target role and must be
read-only.

```bash
docker run --rm --network bs-manager-recovery \
  --mount type=bind,src="$BACKUP_FILE",dst=/backup.age,readonly \
  --mount type=bind,src="$AGE_IDENTITY_FILE",dst=/run/identity,readonly \
  --mount type=bind,src="$PGPASSFILE",dst=/run/pgpass,readonly \
  --tmpfs /restore:rw,noexec,nosuid,size=2g \
  --env PGHOST=target-db --env PGPORT=5432 --env PGUSER=bsmanager_owner \
  --env PGDATABASE=bsmanager --env PGPASSFILE=/run/pgpass \
  --entrypoint /bin/sh bs-manager-backup-tools -ec '
    umask 077
    age --decrypt --identity /run/identity /backup.age > /restore/database.dump
    pg_restore --list /restore/database.dump >/dev/null
    pg_restore --exit-on-error --no-owner --no-acl \
      --dbname="$PGDATABASE" /restore/database.dump
    rm -f /restore/database.dump
  '
```

What it does: decrypts and validates the archive in memory-backed temporary
storage before restoring to the new database. A decryption/authentication or
archive-listing failure exits before `pg_restore` is invoked. The restore
process requires enough tmpfs capacity for the full uncompressed dump and
enough target database storage for the restored data.

The archive omits ownership and ACLs by design. Recreate the application's
restricted database role and reapply grants after restoring, before starting
the web application. Run the following as a database owner or administrator,
adjusting role/database names to the environment:

```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO bsmanager;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bsmanager;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bsmanager;
ALTER DEFAULT PRIVILEGES FOR ROLE bsmanager_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bsmanager;
ALTER DEFAULT PRIVILEGES FOR ROLE bsmanager_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO bsmanager;
```

What it does: restores the intended distinction between the schema owner used
for migrations and the restricted application role. Confirm the target role
exists and owns the restored schema before granting access.

After restoration, verify Alembic readiness, row counts and representative
records, application login, attendance history, and application-role access.
Keep the source database and its backups intact until the recovery is reviewed.

## Recovery rehearsal

Run the disposable rehearsal from the repository root:

```bash
python3 scripts/check-backup.py
```

What it does: builds the backup image, creates uniquely named temporary
PostgreSQL containers, network, and volumes, creates only synthetic rows,
generates a temporary age identity, encrypts a custom-format dump, rejects a
truncated archive and wrong identity before restore, restores to a separate
database, and checks representative rows and an audit immutability trigger.
It removes only resources with its unique run prefix and its own image. The
test requires the application Python dependencies, Docker and network access to pull the official PostgreSQL image
and install Alpine's `age` package. It also migrates and restores the full application schema, verifies readiness,
login through a recreated restricted role, attendance totals/history, leave
decisions, work logs and events. It also rejects schema creation and audit
mutation by that role. It does
not prove an off-host backup, key escrow, schedule, retention,
monitoring, or production recovery process.

## Operational decisions still required

Before using this for real records, choose and document the recovery-point and
recovery-time objectives, schedule, retention, off-host destination, access
controls, key escrow/rotation ownership, alerting, and restore approval. A
reasonable starting policy to discuss is daily backups with seven daily, four
weekly, and three monthly copies; this is a proposal, not an installed policy.
Backups contain staff attendance and work-log data. Encryption does not protect
against a compromised database host, a malicious privileged operator, deletion
of the only backup copy, or loss of every decryption key. This database archive
does not include `.env`, `SECRET_KEY`, identity configuration, container images,
or host configuration; those need separate secure recovery procedures.
