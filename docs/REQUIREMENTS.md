# MVP requirements and acceptance

Updated: 2026-11-01. Dated local checkpoints below are historical; the final
release section and RELEASE_READINESS.md describe current deployment.
This checklist reconciles the functional requirements in the
latest Flask draft (`0f72f5b`) with the user's selected narrow scope and subsequent
security/recovery requirements. CRM, subscriptions/accounting and the old draft's
future ideas (email notifications, kanban, QR/geolocation, overtime and SSO) are
outside this MVP. This is local implementation acceptance, not deployment approval.

| Requirement | Implemented behavior | Verified evidence |
| --- | --- | --- |
| Browser access on desktop/mobile | Responsive staff/admin forms, mobile calendar list and contained table scrolling | Chromium + WebKit at 1440×1000 and 390×844; real CSRF forms, no document overflow or JavaScript errors |
| Attendance entry/exit with notes | One open session, serialized transitions and database overlap/positive-duration protection | HTTP tests, competing PostgreSQL clock-in/out and overlap transactions, real-browser clocking |
| Daily/monthly totals and CSV | UTC elapsed durations, local-day/month clipping, overnight and DST handling, formula-safe CSV | Boundary/DST tests, role-scoped export tests and browser workflows |
| Administrator attendance corrections | Manual creation, version-checked edits, retained voids with mandatory reason and immutable before/after audit | Transaction, stale-edit, permission and database-trigger tests; browser manual entry |
| Work logs | Date, project, title, description and finite 0–24 hours; employee-owned CRUD and administrator team review | Role/filter/input tests; real-browser create/edit/delete/download |
| Work-log filters/CSV | Month/project/employee filters; employee-scoped project suggestions; escaped text cells | Cross-user denial, query/filter and CSV tests |
| Leave types and working days | Vacation, absence, medical leave, training, remote work and other; configured weekdays and holidays | HTTP/service tests; national/movable holiday cases and year boundary checks |
| Annual leave balance | Default/year-specific allowances; pending/approved reservations; year splitting; no overspend under concurrent requests | PostgreSQL competing requests and approval revalidation; configurable part-time schedule snapshots |
| Leave planning estimate | Working-day/yearly balance preview for the signed-in employee; no reservations until actual submission | HTTP no-write, schedule/holiday/year-split, overlap/balance, CSRF and cross-user input checks; real-browser estimate and no-JavaScript submission |
| Leave decisions/history | Approve/reject with note; cancel with authorization/state checks; retained actor/time/before/after history | Role/state/stale-version and immutable-history tests; browser request/approval |
| Team calendar | Portuguese holidays, approved availability, private pending leave and shared events | Role-based JSON/dashboard tests, real local FullCalendar create/render and input-validation tests |
| Shared event corrections | Author/admin editing of title, description, date/time and all-day span; original author retained | Owner/admin/colleague HTTP tests and Chromium/WebKit desktop/mobile create→edit→delete workflows |
| Sensitive leave privacy | Colleagues see only “Indisponível”; owners/admins retain categories/reasons in private leave pages | Calendar, dashboard and history allow/deny tests; no-store headers |
| Responsive workspace and theme | Management product label; full-width navbar, mobile menu, aligned report controls and persistent light/dark switch beside PT/EN | Chromium/WebKit 320–1920 px, PT/EN, both roles/themes; keyboard and no-JavaScript navigation, theme persistence/system preference/storage failure |
| Users | Named account creation, roles, deactivation, annual allowance, working weekdays, color and password changes | Account tests and browser create/deactivate; self-lockout prevention |
| Account recovery/security | Interactive operator reset, admin employee reset, revocable sessions and shared database login limits | Password/deactivation/remember-session tests, cross-app throttle and concurrent login tests |
| Docker portability | Explicit migrations/admin initialization; restricted web DB role; loopback web and private PostgreSQL | Isolated Compose fresh init, CSRF login, schema consistency and container replacement |
| Recoverable records | Encrypted custom dump; atomic publication; dump failure cleanup; separate clean restore with full schema/history/login | Actual disposable Docker backup/restore, corrupt/wrong-key rejection and permission checks |
| HTTPS pilot preparation | Secure-cookie/read-only web overlay, independent host tunnel and operator runbook | Local overlay acceptance; exact demo runtime/hardening/restart verified on 2026-11-01 |

## Selected internal defaults

- UI: European Portuguese by default, with a persistent PT/EN browser switch on
  the sign-in page and in the workspace. Entered content is not translated.
- `APP_TIMEZONE`: Europe/Lisbon; attendance storage: UTC instants.
- Colleague leave visibility: availability only. Administrator self-approval: allowed.
- Working weekdays and annual allowance: configurable per employee, with optional
  year-specific allowances. Monday–Friday/22 days are draft defaults, not legal
  or payroll policy. Holidays include the configured municipal/extra dates.
- Active leave of any kind cannot overlap. Pending vacation reserves balance;
  rejected/cancelled requests release it. Started approved leave requires an
  administrator to cancel. New requests may include past dates for internal
  corrections; there is no payroll closure or statutory accrual engine.
- Shared events are local company wall times; all-day end dates are inclusive in
  the form and exclusive in the calendar feed. Attendance instants have explicit
  UTC offsets in CSV. Changed ambiguous attendance times require an occurrence.
- Leave periods are bounded to two years; calendar feed ranges are bounded.
  Work-log description limit: 10,000 characters. Passwords: 12–1024 characters.
- Month reports accept years 1900–9998. Out-of-range months and invalid calendar
  ranges return HTTP 400 rather than an unhandled date-overflow exception.

## Earlier local verification — 2026-10-30

The review mapped the original five functional modules back to the selected
draft's README. No missing original-scope workflow was found in that comparison.
Calendar editing is an additional usability improvement. Extreme date-filter
failures were reproduced locally and fixed. The PostgreSQL 17 suite now passes
147 tests; Chromium/WebKit pass at 1440×1000 and 390×844, including real CSRF forms,
event editing and timed-to-all-day conversion. The SQLite baseline before this
slice passed 114 tests with six PostgreSQL-specific skips; the 15 new cases also
passed on SQLite. The later leave/profile slice passed 40 focused SQLite tests
with two PostgreSQL-only skips. Browser acceptance now also covers the estimate,
labelled report filters and no-JavaScript submission. These checks use disposable
local data, not the staging database.

## PT/EN verification — 2026-11-01

The sign-in heading now uses ordinary text without a mobile-hidden line break;
copy reads “Gestão da equipa” / “Team workspace”. PT/EN selection is available
before and after sign-in and preserves authentication and GET filters. The
CSRF-protected locale form accepts only supported languages and local return
paths; its cookie follows the deployment's secure-cookie setting. No new schema,
identity provider or dependency is required. Navigation, forms, feedback, calendar
controls/holidays, leave estimates, system history labels and CSV headings are
translated. Dates, company time zone, stored audit contents and entered text retain
their existing meaning and original values.

The full disposable PostgreSQL 17 suite passed **153 tests**. The six localization
cases also passed on SQLite with real CSRF enabled; they cover permissions,
privacy, unchanged entered records, safe redirects, error-page switching, history
and exports. The existing Flask-Login deprecation warning remains. Chromium and
WebKit passed at 1440×1000 and 390×844, including both login languages, English
workspace pages, translated estimates and English submission without JavaScript.
Mobile and desktop screenshots were inspected. Table scroll containment was fixed
for hidden action labels. No physical-device or hosted-application result is
claimed. The actual existing local Docker preview was rebuilt, retaining its data
and credentials; PT/EN login copy, locale persistence, CSRF switch and readiness
passed against it. This interface slice has not been deployed to staging.

## Navbar/theme verification — 2026-11-01

The subsequent UI refinement passes 49 focused server tests plus synthetic
Chromium/WebKit workflows. Separate geometry/theme checks cover 12 widths from
320 to 1920 px, both languages/roles/themes, report baselines, navbar non-overlap,
keyboard and native no-JavaScript account navigation, theme persistence, system
preference, cross-tab changes and unavailable storage. Representative screens were
visually inspected. Physical-device and hosted-deployment acceptance are separate.

## Reproduce local acceptance

- `python -m pytest -q`: temporary SQLite; `TEST_DATABASE_URL` enables unique
  PostgreSQL test schemas in a dedicated disposable database.
- `python scripts/check-compose.py`: isolated Docker install/login/persistence.
- `python scripts/check-backup.py`: isolated full-schema encrypted restore.
- `python scripts/check-browser.py`: isolated local Chromium/WebKit workflows
  (requires the separate Playwright test runtime).

What it does: these checks use synthetic fixtures and clean up only resources
created for their own run. Never point tests at a database containing real data.
See README and the operations/recovery guides for prerequisites and effects.

## Deployed release and remaining readiness gaps — 2026-11-01

The reviewed application source was committed as `88b81e5` and deployed to the
existing synthetic demo behind its separate Cloudflare Access application.
PostgreSQL acceptance now passes 189 tests. Exact served assets, secure cookies,
readiness and anonymous redirects pass. The operator confirms successful public
Access/application login. The runtime report independently verifies the committed
image, hardening, loopback exposure, active services, SSH settings and web restart
recovery with unchanged records/history. The actual encrypted pre-update dump was
copied off the VM and restored into an isolated Mac database; all nine table
fingerprints match. No real-data or hosted-CI acceptance is implied.

Non-allowlisted identity denial, full hosted administrator/employee CRUD, physical
phones and whole-host recovery for this application remain unverified. Real use
also requires company policy approval, hosting/maintenance ownership, independent
backup storage/key custody, scheduling/retention/alerts and measured recovery
objectives. See [TASKS.md](TASKS.md) and
[RELEASE_READINESS.md](RELEASE_READINESS.md) for current evidence and gaps.

## Interface additions — 2026-11-12

Added without schema changes, migrations or new dependencies:

- Dashboard: running elapsed time for the open session (server-rendered value
  without JavaScript), hours per weekday for the current week, a quick work-log
  form for today, and absences split into today and upcoming under the existing
  privacy rule.
- Work logs: daily totals, hours per project for the filtered month, and a
  duplicate action that prefills a new entry dated today. Duplicating follows the
  same owner-or-administrator rule as editing.
- The quick form returns to the dashboard through a `next` value accepted only
  when it is a local path; anything else falls back to the work-log list.
- A web manifest and icons allow adding the application to a home screen. There
  is no offline mode.

Tested locally on 2026-11-12: 192 tests pass on SQLite with 7 PostgreSQL-only
tests skipped, and both browser checks pass in Chromium and WebKit. PostgreSQL
acceptance, hosted CI, the demo and physical phones were not exercised.
