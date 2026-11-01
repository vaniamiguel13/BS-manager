# Release validation — 2026-11-01

This is a synthetic demo release candidate, not approval to handle real company
records. The user authorized end-to-end checks, committing the reviewed source,
and updating the existing demo VM. Pushing to GitHub has not been requested.

## Verified locally

- The full PostgreSQL suite passes **189 tests**. It covers permissions, CSRF,
  attendance/DST/concurrency/history, work logs, leave balances/privacy/approval,
  calendar administration, account/session revocation, migrations and readiness.
- The earlier SQLite checkpoint passes 178 tests with seven PostgreSQL-specific
  skips. PostgreSQL is the deployment database and the final full-suite evidence.
- Real Chromium and WebKit workflows cover administrator and employee behavior,
  attendance, work logs, leave, calendar create/edit/delete and month/week/agenda
  controls, account administration, PT/EN and submission without JavaScript.
- Responsive browser checks cover 320–1920 px, both languages, roles and themes,
  keyboard navigation, system theme, persistence, cross-tab synchronization and
  unavailable storage. Navigation is also sampled across six pages with delayed
  fonts and theme initialization; scrollbar changes must preserve its position.
  These are browser-engine checks, not physical-device certification.
- Disposable Docker/PostgreSQL acceptance covers fresh initialization, restricted
  runtime database credentials, explicit/repeated migrations, data persistence,
  loopback exposure, readiness and the hardened HTTPS overlay.
- The encrypted-backup rehearsal verifies a complete schema/data restore into an
  isolated database, including history, triggers and recreated runtime access.
  Corrupt archives and wrong keys fail. This is separate from restoring a backup
  taken from the actual demo VM, which remains deployment acceptance work.
- PyPA pip-audit reports no known vulnerabilities in the pinned Python requirements
  or the 22 installed Python distributions inspected in the local app image.
  This does not audit the base OS or certify that vulnerabilities cannot exist.
- Release helper checks cover immutable archive validation, traversal/link/device
  rejection and independent rollback attempts. The privileged update procedure
  still requires actual target execution and verification.

The review also fixed a login/reset race by retaining the verified session-token
snapshot, rejected ambiguous/malformed login return paths, aligned supported date
bounds across writes and reports, and protected local `.env` creation permissions.
The interface now uses stable navigation typography and reserves the deferred
theme control's space. The calendar retains the project palette, adds clearer
controls/today/weekend styling and uses a compact agenda on phones.
The users directory groups names/emails and provides a tablet/mobile layout,
while preserving account actions. Decorative slogans, duplicate labels and the
coloured card-top stripe have been removed.

## Current demo evidence

Read-only verification on 2026-11-01 reached the console-attested VM through the
pinned Cloudflare Access SSH configuration. SSH, Docker and the existing connector
were active. The operator has no noninteractive sudo permission. The existing
application still uses the October preview; the November candidate is not yet
installed. Its existing Compose and database initialization definitions match the
candidate, allowing an image-only update without migrations or database reset.

Anonymous HTTPS requests to the staging root, login, readiness, stylesheet,
calendar and administrator URLs redirect to Cloudflare Access. This verifies the
anonymous gate, not the current dashboard policy or every identity flow. The
approved web allowlist contains the two user-selected reviewer addresses; SSH
retains its separate administrator policy. No Cloudflare changes are part of this
release update.

## Remaining acceptance

- Execute the reviewed image-only update with the operator's private sudo entry.
- Verify the running image's exact committed revision, readiness, loopback binding,
  unchanged database/history fingerprints, secure cookies and restart behavior.
- Copy the encrypted pre-update backup off the VM and restore it into an isolated
  database with the separately retained Mac recovery identity. Preserve the source
  database and existing credentials.
- Recheck the anonymous Access gate after deployment. Have an approved reviewer
  complete public Access/application login privately, and verify denial with an
  operator-controlled non-allowlisted identity. Do not request PINs/passwords in chat.
- Run hosted CI after a separately authorized push. Local CI-equivalent checks do
  not establish hosted CI success.

Before real records, confirm company timekeeping/leave policies, approved hosting
and ownership, patching, monitoring, independent backup storage, key custody,
retention, scheduling, failure alerts and measured recovery objectives. A VM on a
personal Windows machine remains a preliminary testing environment.
