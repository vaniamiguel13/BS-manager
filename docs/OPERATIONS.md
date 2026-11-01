# Operating the internal pilot

Prepared on 2026-10-29; status reconciled on 2026-10-30. A separately authorized
synthetic staging preview uses this deployment shape. Its readiness and anonymous
Access gate have been verified; authenticated sign-in, target backup/restore and
application restart recovery remain acceptance gates. This guide does not grant
deployment authorization. Keep the operator SSH tunnel independent of the app.

## Local versus HTTPS configuration

Use `docker-compose.yml` alone for loopback HTTP development. For an approved
HTTPS pilot behind a host-managed tunnel, combine it with
`docker-compose.pilot.yml`. The overlay enables Secure cookies and HSTS, and
runs the web filesystem read-only with a small writable temporary filesystem.
The local Docker check verifies this overlay’s read-only filesystem, Secure
cookies, HSTS and readiness. It does not verify target ingress.
The application port remains bound to loopback; PostgreSQL has no host port.
Do not browse the Secure-cookie configuration through HTTP for login testing.

Before publishing an application route, the operator must create its separate
Access application with an explicit employee allowlist and verify allow/deny
flows. Do not reuse the administrative SSH application or its policy. Point
only the approved application hostname at the loopback web listener. Keep
Cloudflare credentials outside Compose, Git and command arguments. Dashboard
operations and company account ownership remain operator responsibilities.

## Initialize or update an approved target

Use fresh synthetic data for the preliminary pilot. Generate a unique `.env`
on that host, retain owner-only permissions, then build and migrate once before
starting workers:

```bash
python3 scripts/setup-local.py
docker compose -f docker-compose.yml -f docker-compose.pilot.yml build web migrate
docker compose -f docker-compose.yml -f docker-compose.pilot.yml run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.pilot.yml run --rm migrate flask --app wsgi create-admin
docker compose -f docker-compose.yml -f docker-compose.pilot.yml up -d --wait
```

What it does: prepares host-specific secrets, applies versioned schema changes,
prompts privately for the first administrator and starts the HTTPS-cookie stack.
Run only on the explicitly approved target, with the operator-controlled HTTPS
route configured. Never commit `.env` or bootstrap passwords.

For updates, preserve secrets, record the reviewed revision/image, take and
verify an encrypted backup, stop web writes, build the new image and run the
migration service once. Then recreate web on that image and verify readiness,
login, synthetic CRUD, history and expected counts. Do not run migrations inside
every web worker. If an upgrade fails, keep the web stopped and investigate;
retrying blindly is not a rollback strategy.

## Accounts and recovery

Administrators create named accounts, set their working weekdays, calendar
color, base annual allowance and optional year-specific allowance. Monday–Friday
and 22 days are configurable draft defaults. Existing leave requests retain their
working-week snapshot. Entitlement reductions below active reservations are
rejected. Self-approval is permitted by the selected internal policy; colleagues
see only availability. Revisit these rules before adopting official timekeeping.

Passwords have 12–1024 characters. Users change their own password after supplying
the current password. Administrators may reset employee passwords after verifying
identity privately. Password, account-role, email or activation changes revoke old
sessions; reactivating an account does not revive old cookies. Login limits are
shared through the database: ten failures within a 15-minute window block that
account for 15 minutes. This does not replace an outer Access policy.

For an existing account whose administrator is unavailable:

```bash
docker compose run --rm migrate flask --app wsgi reset-password
```

What it does: prompts for the existing email and a hidden replacement password,
revokes old login/remember cookies and clears its login lockout. It does not
activate a disabled account or grant administrator rights. The operator must
verify the person's identity and transfer any temporary password privately.
No email delivery or identity-provider integration is configured.

If every administrator account is lost, a trusted console/host operator can run
the documented interactive `create-admin` command. This grants administrator
access and must be treated as an explicit recovery action. Keep console recovery
and the independent host/SSH credential path available.

## Backup and rollback

Follow [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md). A Docker volume, container restart
or VM snapshot does not prove independent recovery. Back up the database using
public-recipient encryption; keep decryption identities and recovery copies apart
from the database host. Store host secrets and deployment configuration in a
separate approved secure recovery location. They are not in a database archive.

Migrations with retained history refuse data-bearing downgrades. For recovery,
restore a trusted encrypted archive into a separate empty database, reapply
restricted-role grants, use the matching application image and verify it before
switching traffic. Preserve the original database and archive. Restoring a
backup loses changes after that backup; record and reconcile that interval.

Before any real-data pilot, name the owner, off-host destination, backup schedule,
retention, key escrow, restore approval and measurable recovery objectives. The
repository supplies working local tools and a full-schema restore rehearsal;
it does not install a scheduler or establish an independent company backup.

## Routine checks

```bash
docker compose ps
docker compose exec web python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').status)"
docker compose run --rm backup --check-freshness 36
```

What it does: reports service state, checks database migration readiness and
checks whether an encrypted archive exists within 36 hours. Prepare the backup
profile first. Freshness does not authenticate an archive or prove restore.
Review backup job failures, available storage, container health and updates;
perform an isolated restore after backup/key/schema changes and periodically.
Configure recipients and monitoring explicitly; these commands send no alerts.

## Existing synthetic demo: image-only update

Prepared on 2026-11-01. `scripts/package-release.py` refuses a dirty tree and
archives the exact committed source into a new directory outside the checkout.
The reviewed archive digest and commit must be independently verified on the Mac
before executing `scripts/update-demo.py` privately with sudo on
`bs-manager-staging`. Transfer only source, the reviewed updater, a launcher and
the public age recipient; keep its private recovery identity on the Mac.

This bounded updater requires the existing `bs-manager-staging` Compose project,
unchanged Compose/init definitions and migration head `0003_staff`. It never runs
migrations, resets a database, resizes disks or changes Cloudflare. It snapshots
the existing private environment into root-managed state, builds first, retains
the previous image, briefly stops only web, fingerprints existing records and
creates an encrypted full database dump before replacing web. Activation must pass
readiness and exact image-revision checks; errors attempt restoration of the old
image and deployment pointer independently of reporting errors.

New authoritative source/state live under `/var/lib/bs-manager-staging`, with
`current` pointing at the activated committed source. Root-private per-commit
state retains the environment, encrypted backup and result. The historical
`~/bs-manager-preview/current` pointer is preserved for the previous installer;
do not use it as the current deployment revision after this update. An
operator-readable copy of the result and encrypted archive is exported under
`~/bs-manager-updates/<commit>/`, with private permissions. The original
`preview.env`, database volume and host connector remain in place. Do not rerun
the bootstrap/start-preview helper to update this deployment.

A failed/partial update directory must be inspected before retrying. Never delete
it and rerun blindly. Off-VM restore verification, running-image checks, restart
acceptance and public Access allow/deny tests are still required after the script
reports healthy. Preserve the rollback image and encrypted backup until those
checks and reviewer acceptance complete. Use the recorded rollback image with
the exact trusted Compose definitions and private environment to recover; never
restore a database over the existing deployment as an image rollback step.
