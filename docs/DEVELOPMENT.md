# Development baseline

Reviewed: 2026-10-28. This is a development plan, not a release-readiness claim.

## Scope and source

The first release covers attendance, work logs, leave requests, the team
calendar, and account administration. CRM, customer subscriptions, and
accounting are outside this release.

The starting point is the Flask prototype at
[`0f72f5b`](https://github.com/vaniamiguel13/BS-manager/tree/0f72f5b0fe456c95b2c446ff1d0326b0e05552c3),
from `claude/eager-hypatia-kjqj00`. Ongoing work uses `develop`.
The older Next.js prototype at `426723f` has a broader product scope and is
retained as reference. The two prototypes share only the initial skeleton;
they are separate implementations and should not be merged wholesale.

Keep the existing Flask/Jinja application for this release. Reconsider the stack
only if an identified requirement justifies the implementation and maintenance
cost. Hosting, production database, identity provider, and network exposure
remain decisions to make before deployment.

## Acceptance criteria

These criteria guide development; unchecked items are not claims of completion.

| Area | Required result |
| --- | --- |
| Access | Employees can access their own records; administrative actions and team reports enforce permissions on the server. Deactivation removes access. Account recovery has a documented path. |
| Attendance | Clock-in/out works on desktop and mobile. At most one session is open per person. Invalid and overlapping records are rejected, including simultaneous requests. |
| Time totals | Duration uses elapsed time across DST. Daily and monthly totals handle overnight work and month boundaries consistently. |
| Corrections | Administrative corrections and deletions retain actor, timestamp, reason, and before/after values in an audit history. |
| Work logs | Employees can create, edit, and export their entries; administrators can review team entries. Filters and exports obey the same permissions. |
| Leave | Requests enforce valid dates, overlap and annual balance rules; approvals, rejections and cancellations retain their history. Part-time and annual entitlement rules are confirmed before real use. |
| Calendar | Holidays, shared events, and availability render correctly. Colleagues see only the approved absence detail they need. Sensitive leave details have explicit access rules. |
| Exports | CSV output has correct totals and encoding, and user-controlled cells cannot introduce spreadsheet formulas. |
| Operations | A clean installation, schema upgrade, service restart, and isolated backup restore are verified against the selected deployment design. |
| Usability | The main employee and administrator workflows are checked in a browser at desktop and mobile sizes, with clear validation and failure messages. |

## Review findings

Findings refer to the starting revision unless marked as locally addressed.
Synthetic checks used disposable data only.

1. **Unsafe session configuration — locally addressed.** Normal startup accepted
   a public default `SECRET_KEY`. A synthetic session signed with that key
   accessed an administrative page. The application now rejects missing,
   whitespace-only, or short keys outside development/test startup. Debug and
   test startup generate an independent temporary key when none is supplied.
   The minimum length check does not establish randomness: operators must
   generate the key securely and keep it outside Git. See
   [Flask's configuration guidance](https://flask.palletsprojects.com/en/stable/config/#SECRET_KEY).
2. **Attendance has no complete correction history.**
   `app/models.py:WorkSession` records only the most recent editor;
   `app/routes/attendance.py:delete` permanently deletes the row. A synthetic
   deletion left no attendance row or audit record. Add history before real use.
3. **Local timestamps produce incorrect DST durations.**
   `app/utils.py:now` discards the timezone; `WorkSession.duration` subtracts
   naive timestamps. For a synthetic Lisbon session on 2026-10-25 from 00:30
   to 02:30, the model reported two hours for three elapsed hours. Store instants
   in UTC and convert for display; define how existing records will migrate.
4. **Approved medical-leave types are visible to colleagues.**
   `app/routes/calendar.py:events` and the dashboard expose the approved absence
   kind for every person. This was reproduced through the calendar endpoint
   using another employee's synthetic medical leave. Recommended default:
   colleagues see availability; the employee and authorised administrators see
   leave details. Confirm that visibility rule before implementation.
5. **Attendance integrity relies on sequential application checks.**
   `clock_in` checks for an open session before inserting; there is no database
   uniqueness constraint. The administrator form also accepts overlapping
   sessions. The concurrency risk is a code finding, not a reproduced concurrent
   run. Enforce invariants transactionally and test competing requests.
6. **Schema changes have no migration path.** `create_app` calls
   `db.create_all()` on every startup. This creates tables but does not upgrade
   existing tables, as the
   [Flask-SQLAlchemy documentation](https://flask-sqlalchemy.readthedocs.io/en/stable/quickstart/#create-the-tables)
   explains. Add versioned migrations before changing persisted models.
7. **Login throttling is local to each process.** `_failures` in
   `app/routes/auth.py` is in memory, while the Docker command starts three
   workers. Lockout state is neither shared nor persistent. This is a static
   finding; shared-worker enforcement has not been tested.
8. **Other permission and export gaps need coverage.** The work-log project
   dropdown queries every employee's project names. CSV exports write
   user-controlled text directly to cells. Scope project suggestions to the
   viewer and protect text cells from formula interpretation.

The baseline already uses password hashing, CSRF protection and server-side
ownership checks in several routes. Those are useful foundations; they do not
establish that all access paths are correct. The existing baseline suite passed
15 tests. An additional synthetic check confirmed that deactivating a user
blocks their existing session on the next protected request.

## Delivery order

1. **Secure, repeatable development baseline.** Complete the session-key fix,
   reproducible environment setup, automated checks, configuration validation,
   and a versioned migration path. Confirm whether any existing data needs
   preserving before schema changes.
2. **Reliable staff records.** Fix time storage/totals, session invariants,
   correction history, leave transitions and privacy. Add focused tests for
   permissions, concurrent submissions and boundary dates.
3. **Usable internal pilot.** Review the desktop/mobile workflows with synthetic
   data, verify CSV output and account recovery, and correct usability issues.
4. **Deployment preparation.** Choose an owner-approved host, identity/access
   model, persistent database, backup/restore and update/rollback process.
   Existing deployment scripts remain prototype proposals until reviewed for
   that target. Then verify the approved deployment with a small pilot.

## Decisions still needed

No existing prototype is in use with real records, as reported on 2026-10-28.
Start with a fresh versioned schema and synthetic development data.

- Total number of users and administrative responsibility.
- Working schedules and annual leave entitlement, including part-time staff;
  treatment of corrections, overnight sessions and reporting periods.
- Who may see leave categories and reasons, who may approve requests, and
  whether an administrator may approve their own request.
- UI language, account provisioning/recovery, and whether existing company
  identity can be reused.
- Hosting ownership, database, maintenance and backup responsibility, and the
  exact public hostname before configuring DNS or certificates.

Keep credentials, staff records, private infrastructure details and backups
outside this repository. Its public visibility was verified on 2026-10-28;
application access and repository visibility are separate concerns.
