# Release validation — 2026-11-01

This records a deployed synthetic demo release and its readiness assessment.
It does not authorize real company records. The user authorized end-to-end checks, committing the reviewed source,
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
  taken from the actual demo VM; the separate completed target restore is
  recorded below.
- PyPA pip-audit reports no known vulnerabilities in the pinned Python requirements
  or the 22 installed Python distributions inspected in the local app image.
  This does not audit the base OS or certify that vulnerabilities cannot exist.
- Release helper checks cover immutable archive validation, traversal/link/device
  rejection and independent rollback attempts. Actual target execution is
  recorded below; the retained rollback image was verified, without deliberately
  forcing a failed deployment on the shared demo.

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
all redirect to Cloudflare Access. On 2026-11-01, the operator also confirmed
that public Access authentication followed by application sign-in reaches the
dashboard. This positive flow is operator-reported; it was not automated by the
agent. A non-allowlisted identity denial remains unverified.

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
changes formed part of this release update. The runtime verifier executed on
2026-11-01 at 19:03:14 UTC; its report was independently retrieved over pinned SSH.
It verified the exact committed running image, non-root/read-only web, dropped
capabilities and disabled privilege escalation, loopback-only web, unpublished
PostgreSQL, retained rollback image and backup digest. All nine record/history
fingerprints remained unchanged through a web-container restart. Readiness
recovered; the connector, Docker and SSH socket remained active. SSH syntax and
effective public-key-only/root-disabled authentication settings passed.

The application source commit remains `88b81e5`. Subsequent repository commits
record evidence and add operator verification tooling; they do not change the
running application image. No push or hosted CI success is claimed.

## Remaining production-readiness and coverage gaps

- Verify denial using an operator-controlled non-allowlisted identity. Anonymous
  redirects and the successful allowed login do not establish this identity flow.
- Complete representative administrator/employee acceptance on the hosted site.
  The full workflow matrix passed against isolated local fixtures; the hosted
  checks cover actual assets, security settings, readiness, persistence/restart,
  recovery and the operator-confirmed dashboard login. Full hosted CRUD has not
  been exercised, and physical phones have not been certified.
- Whole-VM reboot/Windows-host outage recovery for this application version is
  untested. Web-container restart recovery is verified; historical SSH/connector
  guest-reboot checks predate this app release.
- Run hosted CI after a separately authorized push. Local CI-equivalent checks do
  not establish hosted CI success.

Before real records, confirm company timekeeping/leave policies, approved hosting
and ownership, patching, monitoring, independent backup storage, key custody,
retention, scheduling, failure alerts and measured recovery objectives. A VM on a
personal Windows machine remains a preliminary testing environment.
