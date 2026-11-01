# Remaining implementation and release work

Updated and verified: 2026-11-01. This tracks work; it does not authorize Git,
deployment, access changes, communications or real-data use.

## Functional scope

The original attendance, work-log, leave, team-calendar and user-administration
requirements are implemented locally. [REQUIREMENTS.md](REQUIREMENTS.md) maps
them to behavior and acceptance checks. Calendar event editing and date-filter
validation were added on 2026-10-30; PostgreSQL and desktop/mobile browser checks
passed. This latest slice is not in the staging release yet.
The local UX refinement adds non-reserving leave estimates, readable request
cards, accessible report filters and explicit profile validation. Its full
PostgreSQL suite passed 147 tests; desktop/mobile browser checks and submission
without JavaScript pass. It is also awaiting an authorized staging update.

The 2026-11-01 interface slice fixes joined login words, simplifies sign-in copy
and adds persistent PT/EN selection across the workspace. The full PostgreSQL
suite passes 153 tests; Chromium/WebKit desktop/mobile, translated estimates and
English no-JavaScript submission pass. The existing local Docker preview was
refreshed with data and credentials retained. Staging still needs an authorized
update for the calendar, UX, PT/EN and navbar/theme slices.

The subsequent navbar/theme refinement labels the UI “Management”, reclaims the
sidebar width, aligns report filters/actions, and adds a saved light/dark choice
beside PT/EN. Forty-nine focused server tests pass. Chromium/WebKit workflows and
12 responsive widths from 320 to 1920 px pass for both languages, roles and themes,
including keyboard controls, no-JavaScript account navigation, OS preference,
cross-tab theme changes and unavailable storage. Physical devices remain untested.
The update is local; existing data and credentials are retained.

## Release validation checkpoint — 2026-11-01

The user authorized committing the reviewed implementation and deploying to the
existing demo VM. [RELEASE_READINESS.md](RELEASE_READINESS.md) supersedes earlier
test counts above: 189 PostgreSQL tests pass, with Docker, encrypted restore,
real-browser workflows and responsive acceptance. The navbar loading shift is
fixed and the calendar is refined. The local Docker preview has been refreshed.
The reviewed image-only updater preserves the database, secrets and connector,
creates an encrypted pre-update backup, records the exact source revision and
attempts rollback on activation failure. The target update executed on 2026-11-01 and reports healthy with deployed source
`88b81e5`. The actual backup was copied off the VM and restored in isolation; all
nine table/history fingerprints match. Exact served assets, readiness, cookie
flags, security headers and anonymous public Access redirects pass. Privileged
runtime/restart verification and public reviewer authentication remain pending.

## Before completing the synthetic feedback preview

- [ ] Verify an approved reviewer completes email PIN authentication and website
  login through the public staging hostname. Keep both passwords and PINs private.
- [ ] Verify a non-allowlisted operator-controlled identity cannot reach the site;
  anonymous redirects and the saved policy alone do not prove this flow.
- [ ] Run representative attendance, work-log, leave and calendar workflows on
  synthetic staging records, including the separate employee role.
- [ ] Create a named application account for the second approved reviewer through
  the existing administrator workflow; Access enrollment alone is not an account.
- [ ] Resolve or recheck the Mac's cached DNS failure without weakening Access.
- [x] Rehearse encrypted backup and isolated restore from the staging deployment;
  preserve its original database and credentials.
- [ ] Coordinate an application restart/reboot check and verify recovery and
  persisted records. Previous host SSH/connector reboot tests predate the app.
- [x] Prepare and deploy the reviewed update/rollback artifact for calendar, UX,
  PT/EN and security fixes, preserving staging secrets and records (2026-11-01).

## Before real company records

- [ ] Confirm whether time records are internal tracking or official/payroll input.
- [ ] Review entitlement, part-time schedules, holidays, past-date corrections,
  administrator self-approval and leave privacy with the company. Current defaults
  are configurable and are not a legal/payroll policy engine.
- [ ] Agree an approved always-on host, ownership and maintenance coverage. The
  personal Windows/VM setup is preliminary and unavailable when its host is off.
- [ ] Select approved independent encrypted-backup storage, recovery-key custody,
  schedule, retention, failure detection and alert ownership. Verify recovery using
  materials accessible independently of the application host; measure RPO/RTO.
- [ ] Run hosted CI after an explicitly authorized commit/push; local tests do not
  establish hosted CI success. Review the complete uncommitted MVP before release.

The draft's future email notifications, overtime reports, kanban, QR/geolocation,
and SSO remain outside the agreed MVP. CRM, subscriptions and accounting remain
outside this release. Add new functionality only against an identified need.
