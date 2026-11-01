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

The image-only updater executed on 2026-11-01 and reports healthy at
18:34:59 UTC. The deployed application source is commit
`88b81e59872ee7c57ac5b4ec92f99afce9dfa33e`; the running image recorded by the
updater is `sha256:993cf0233f22b89ce81b6ba4bece486b5c410e5a4d675343270db5fe411554c3`.
The October preview was retained as a rollback image. Existing credentials,
database volume, migrations and Cloudflare connector were preserved. The
operator entered sudo privately; no password or tunnel token was handled in chat.

Independent post-deployment origin checks over pinned SSH confirm readiness,
byte-identical stylesheet/theme/logo assets, CSRF login, Secure/HttpOnly/SameSite
cookies, no-store responses, frame protection and HSTS. Anonymous public HTTPS
requests to root, login, readiness, stylesheet, calendar and administrator URLs
all redirect to Cloudflare Access. These checks do not establish the dashboard's
current exact policy or successful/denied authenticated identity flows.

The actual encrypted pre-update dump was copied into a private Mac recovery
folder, decrypted through a pipe and fully restored into a disposable PostgreSQL
database with no network exposure. All nine table/history fingerprints match the
pre-update snapshot. No plaintext archive was written and the original demo
database was not restored over. Ciphertext and the private recovery identity are
retained off the VM with owner-only permissions; independent storage/key custody
and scheduling remain production gates.

The 22 Python distributions actually built on the demo VM were checked with
PyPA pip-audit after deployment; no known vulnerabilities were reported. This
does not cover the base OS or prove absence of undisclosed vulnerabilities.

The separately scoped web and SSH Access policies were preserved. No Cloudflare
changes formed part of this release update. A bounded runtime verifier is
prepared to confirm actual container hardening, preserved records, rollback image,
connector and SSH settings, and web-container restart recovery. Its privileged
execution and real public reviewer login are still pending below.

## Remaining acceptance

- Verify the running image's exact committed revision, readiness, loopback binding,
  unchanged database/history fingerprints, secure cookies and restart behavior.
- Have an approved reviewer complete public Access/application login privately,
  and verify denial with an
  operator-controlled non-allowlisted identity. Do not request PINs/passwords in chat.
- Run hosted CI after a separately authorized push. Local CI-equivalent checks do
  not establish hosted CI success.

Before real records, confirm company timekeeping/leave policies, approved hosting
and ownership, patching, monitoring, independent backup storage, key custody,
retention, scheduling, failure alerts and measured recovery objectives. A VM on a
personal Windows machine remains a preliminary testing environment.
