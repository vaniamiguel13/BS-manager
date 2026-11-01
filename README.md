# BS-manager

BS-manager is a small internal staff-management prototype. Its initial scope is
attendance, work logs, leave and absences, the team calendar, and account
administration. CRM, subscriptions, and accounting are outside this release.

## Status and safety

The original functional MVP is implemented and verified locally with synthetic
data: attendance, work logs, leave, calendar and account administration. See the
[requirements checklist](docs/REQUIREMENTS.md) for behavior and evidence.
The synthetic preview was updated to the reviewed application release on
2026-11-01 behind its separate Cloudflare Access policy. Its actual encrypted
pre-update backup has been restored successfully in an isolated Mac database. No real staff records should be entered yet. Live sign-in
acceptance, company policy sign-off, production placement and independent off-host
backup ownership remain release gates. Hosted CI has not run. See the
[remaining-work tracker](docs/TASKS.md) for current implementation and release gaps.
The [2026-11-01 release validation](docs/RELEASE_READINESS.md) records the latest
checks and distinguishes local acceptance, verified deployment and remaining
live acceptance gates.

The recommended local path is Docker Compose with PostgreSQL. The web container
uses a restricted database role; only the one-off migration/admin service uses
the database owner credentials. Normal web workers do not create schemas, run
migrations, or seed accounts.

## Workspace layout and theme

The product is labelled **Management**, alongside the original project logo.
Desktop navigation uses a full-width top bar; smaller screens have a collapsible
menu. The light/dark button beside PT/EN remembers a browser-local preference and
uses the system theme before a choice is saved. It is also available before login.

## Interface language

Choose **PT** or **EN** at the top right, including on the sign-in page. Portuguese
is the default; the choice is remembered in the current browser. Labels, feedback,
calendar controls and CSV headings follow that choice. Entered names, notes,
projects and retained record contents remain in their original language.

## Local Docker setup

Requirements: Docker Engine with the Compose plugin and Python 3 for the setup helper.
Use a fresh development volume. Existing prototype databases are not automatically
converted; preserve them separately instead of stamping them at the new revision.

```bash
python3 scripts/setup-local.py
docker compose run --build --rm migrate
docker compose run --rm migrate flask --app wsgi create-admin
docker compose up -d --wait
```

What it does: creates a private `.env` with random local secrets (mode `0600`,
without overwriting an existing file), applies database migrations without
creating an administrator, prompts for the first administrator with a hidden
password prompt, and starts the local services. Open <http://localhost:8000>.
The local port is bound to loopback and uses HTTP for development; it is not a
public or LAN deployment.

Stop the containers while keeping the local database volume:

```bash
docker compose down
```

What it does: removes the Compose containers and network while preserving the
named PostgreSQL volume and its data.

To deliberately erase the local database volume as well:

```bash
docker compose down --volumes
```

What it does: removes the containers and permanently deletes the named local
PostgreSQL volume, including all records stored in it.

### Applying an application update

Build the release image, apply its migrations once using the owner role, then
recreate the web container on that image:

```bash
docker compose build web migrate
docker compose run --rm migrate flask --app wsgi db upgrade
docker compose up -d --wait --force-recreate web
```

What it does: builds the application image, applies pending versioned migrations
explicitly, and replaces the web container after the database schema is ready.
Take an approved backup before schema-changing updates when using any data you
need to preserve. Do not run `db upgrade` in each application worker.

## Local Python and SQLite

For development without Docker, the app defaults to a SQLite database under
`instance/`. Use a fresh development database; this is not a migration path for
old prototype tables.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
flask --app wsgi --debug init-db
flask --app wsgi --debug create-admin
flask --app wsgi run --debug
```

What it does: creates an isolated Python environment, installs development
dependencies, applies migrations to the local SQLite database, prompts for an
administrator, and starts Flask's development server at <http://127.0.0.1:5000>.
Without a configured `SECRET_KEY`, debug mode creates a temporary key; sessions
will be invalidated when the app restarts. Do not use this server for deployment.

## Attendance timestamps and corrections

Attendance instants are stored in UTC and displayed in `APP_TIMEZONE` (default
`Europe/Lisbon`). Reports split overnight sessions at local midnight and clip
them to the selected month; CSV rows contain those daily portions and explicit
UTC offsets. Open sessions use one captured current instant per report.

Administrator corrections require a reason and the displayed record version.
Annulling a record retains it and its before/after history, while removing it
from totals. Audit rows reject updates/deletes in the database; this protects
application operations, not against a database owner or machine administrator.

Migration `0002_attendance` upgrades the versioned `0001_initial` schema. It
interprets existing naive attendance values in the configured `APP_TIMEZONE`,
converts them to UTC, and records a baseline with the original values and an
unknown historical actor. Confirm the historical timezone before any data-bearing
upgrade. Invalid/overlapping intervals and ambiguous or nonexistent DST times
stop the upgrade for explicit resolution. Unversioned prototype tables require
separate reconciliation; do not stamp them or guess timestamps.

For repeated DST hours, the correction form requires the earlier or later
occurrence. Nonexistent local times are rejected. Downgrading this migration
with attendance records is refused to protect history. A reviewed, tested backup
restore is required for data-bearing rollback. The local encrypted full-schema
restore rehearsal passes; the company off-host recovery process is still to be
configured. These tracking rules do not establish payroll or legal compliance.

## Leave, calendar and accounts

Employees see their own leave details and decision history. Colleagues see only
approved availability (“Indisponível”); pending requests and sensitive categories
are visible only to their owner and administrators. Administrators may approve
their own requests, as selected for this internal tool.

Each employee has configurable working weekdays and a default annual allowance
(initially Monday–Friday and 22 days), with optional allowances for specific years.
Requests retain their working-week snapshot, exclude configured holidays, reserve
balance while pending, reject active overlaps and split balance across years.
Approval rechecks the balance; rejected/cancelled requests release reservations.
These defaults need company confirmation before official timekeeping use.

Administrators create/deactivate accounts, change roles and reset passwords.
Password and access changes revoke existing sessions. Users may change their
own password; trusted operators have an interactive `reset-password` recovery
command. The database shares login throttling across workers. See the
[operations guide](docs/OPERATIONS.md) for recovery and the prepared HTTPS overlay.

Backups use a public age recipient, streaming a PostgreSQL custom dump directly
into encryption. The optional backup profile never receives the decryption key.
See [backup/recovery](docs/BACKUP_RECOVERY.md) for setup, failure/freshness checks,
full-schema restore rehearsal and remaining off-host responsibilities.

## Tests

```bash
python -m pytest -q
```

What it does: runs the test suite using temporary SQLite databases by default.
When `TEST_DATABASE_URL` is set, PostgreSQL tests create a unique temporary
schema and drop only that schema. Point it only at a dedicated, disposable test
database, never at production or a database containing real staff records.

The CI workflow also checks dependency consistency, shell-script syntax, and
the Docker Compose initialization, migration, login, and persistence path.
Run that isolated check locally with:

```bash
python3 scripts/check-compose.py
```

What it does: builds a uniquely named synthetic test project, verifies migrations,
HTTP login and persistence across container replacement, then deletes only that
project's test containers, database volume and image. It preserves the normal
development stack. This is a persistence check, not an independent backup/restore
rehearsal. Credentials are outside the build context; local container environment
values remain visible to anyone with Docker-administrator access.

For encrypted full-schema backup/restore acceptance (application Python
dependencies and Docker required):

```bash
python scripts/check-backup.py
```

What it does: creates isolated synthetic source/target databases, encrypts a
backup, rejects corrupt/wrong-key inputs, restores and verifies application login,
totals and retained history, then removes only its own test resources.

For local browser acceptance, install Playwright 1.64.1 and its Chromium/WebKit
browsers in a separate test-tools directory, make the package available through
`NODE_PATH`, then run:

```bash
python scripts/check-browser.py
```

What it does: serves a disposable CSRF-enabled fixture only on loopback and checks
employee/administrator workflows at desktop/mobile sizes in Chromium and WebKit.
It rejects external browser requests and keeps screenshots in a temporary folder.
The CI file contains reproducible dependency installation steps.

## Legacy entry points and test VM

`serve.py`, `iniciar.sh`, and `instalar-servico.sh` are legacy non-Docker helpers.
They do not apply migrations automatically; with the selected database
configuration and a valid `SECRET_KEY`, run `flask --app wsgi init-db` before
starting them. They are not the supported deployment path.
`instalar-cloudflare-tunnel.sh` is retired and exits without changing services;
do not pass tunnel credentials as command-line arguments.

The [VM test environment notes](docs/VM_TEST_ENVIRONMENT.md) describe a separate
synthetic-data validation environment. They do not authorize production hosting
or establish that application deployment, public access, or backup recovery has
been approved or verified.
