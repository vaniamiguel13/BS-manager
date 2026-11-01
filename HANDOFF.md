# Handoff

Updated: 2026-11-01, Europe/Lisbon. Earlier dated sections are historical.

Latest checkpoint (2026-11-01): the user authorized release validation, committing
all reviewed source and deploying to the existing synthetic demo. The local
PostgreSQL suite passes 189 tests; Docker, encrypted restore and real-browser
acceptance pass. Navbar loading shifts, calendar styling and the users directory were refined;
decorative copy/card accents were removed. The local preview was refreshed, retaining its data. See `docs/RELEASE_READINESS.md` for
current evidence and acceptance gaps. The November update has not yet executed
on the demo VM. The operator must enter sudo privately for the prepared update;
noninteractive sudo is intentionally unavailable. Do not treat October deployment
notes below as proof that current local source is deployed.

## Objective

Validate and release the original narrow-scope functional MVP, preserving the verified
staging SSH setup. Attendance, work logs, leave, calendar, accounts and local
backup/recovery acceptance are implemented. The user will align the finished
feature set with revised business requirements. The current release/deployment goal
is explicitly authorized; publication to GitHub remains separate.

## Current state

- On 2026-10-29 the user authorized continuing until all original functional
  requirements were implemented, using reasonable configurable defaults for
  later alignment. Colleagues see only leave availability; administrator
  self-approval is allowed. Weekdays/annual allowances are per-user configurable.
- The functional MVP is locally implemented and covered by database, real-browser,
  Docker and encrypted full-schema restore checks. See `docs/REQUIREMENTS.md`
  for the current scope and acceptance, `docs/OPERATIONS.md` for account/target
  procedures and `docs/BACKUP_RECOVERY.md` for encrypted archive/recovery tools.

- On 2026-10-29 the user authorized the local Docker/PostgreSQL foundation.
  Explicit migrations, initialization, readiness, restricted database access and
  isolated integration checks are implemented. Application staging deployment
  remains outside this change. The user then authorized the attendance slice; UTC
  reporting, concurrency protection and correction history are implemented locally.
- The Windows handoff dated 2026-10-28 reports Ubuntu installation, platform
  setup, Mac public-key enrollment, Windows SSH and service recovery after a
  guest reboot completed. Mac SSH and a later coordinated SSH/connector reboot
  test are now directly verified; the Docker test remains Windows-reported.
  No Windows agent was directly contacted from this chat.
- The named `bsmanager` sudo account has console recovery credentials established
  privately. It is not in the Docker group. Windows reports the approved Mac key
  enrolled and the guest host fingerprint obtained from its VMware console.
- The user created the separate SSH Access application/policy, dedicated tunnel
  and exact SSH route through the dashboard on 2026-10-29. Screenshots show the
  initial single-email Allow rule; the user selected a seven-day application
  duration, inherited by the policy, and retained all available identity providers.
- Direct Mac checks now confirm unauthenticated HTTPS/WebSocket requests redirect
  to Access, successful browser authentication, pinned-host/public-key SSH as the
  named operator, and denial of an SSH attempt with guest authentication disabled.
  A non-allowlisted identity test remains pending.
- The active enabled connector is `cloudflared.service`, using a token file;
  `cloudflared-bs-manager.service` remains disabled. The credential directory is
  directly verified root-owned with mode 0700; operator-run sudo output confirms
  its token file is root-owned 0600. No token was read. The operator applied the
  reviewed SSH snippet with syntax/effective-setting checks and reload. A fresh
  Mac session succeeded; a negative test now advertises public-key authentication
  only. Password, keyboard-interactive and root SSH login are disabled.
- A coordinated guest reboot changed the privately recorded boot ID. Fresh Mac
  SSH, socket activation, connector recovery, persisted hardening and post-reboot
  unauthenticated Access/no-key SSH checks passed. Staging-specific Mac cached
  authentication files are operator-owned 0600 inside a 0700 cache directory;
  only metadata was inspected, never credential contents.
- See `docs/VM_TEST_ENVIRONMENT.md` for the proposed profile, operating paths,
  work split and acceptance checks; `docs/ARCHITECTURE_REVIEW.md` owns the broader
  stack/security/recovery proposal.
- No connected Windows host is exposed through this chat's tools. The Windows
  setup prompt must be passed to the agent on that machine by the user.

## Git state

- Repository: `BS-manager` (`vaniamiguel13/BS-manager`).
- Branch: `develop`.
- HEAD: `ca55539cf0dc8f173b5329289603a6b6ffeb78ca`.
- Upstream: `origin/develop`; no divergence in current cached Git status.
  Remote state was not refreshed for this handoff.
- No staged changes. Modified implementation/configuration: `.env.example`,
  `Dockerfile`, `app/__init__.py`, `docker-compose.yml`, `requirements.txt`,
  `serve.py`, `instalar-cloudflare-tunnel.sh`, and existing app/config tests.
- New foundation files: `.dockerignore`, `.github/workflows/ci.yml`,
  `docker/init-db.sql`, `migrations/`, `scripts/setup-local.py`,
  `scripts/check-compose.py`, and migration/readiness/test database fixtures.
- Attendance adds `app/attendance_time.py`, `app/db_types.py`,
  `app/services/attendance.py`, migration `0002_attendance`, retained audit models,
  correction/void/history forms and focused time/integrity/HTTP tests. Existing
  attendance/dashboard models, routes and templates are updated.
- The staff slice adds migration `0003_staff`, leave audit/allowance and login
  throttle tables, revocable user session tokens, leave/authentication services,
  a private leave-history page and focused staff/work-log/migration tests.
- Backup files: `docker/backup/`, `scripts/check-backup.py`, optional Compose
  backup profile and `.gitignore` exclusions. Browser check: `scripts/check-browser.py`
  plus `scripts/browser-check.cjs`; local FullCalendar assets and provenance are
  under `app/static/vendor/`. The HTTPS overlay is `docker-compose.pilot.yml`.
- README and development/architecture/VM/handoff documents reflect current scope.
  All changes remain local and uncommitted; do not assume they reached another host.

## Changes and verification

- Committed initial session-key fix: 26 tests previously passed.
- Foundation verification on 2026-10-29: 37 SQLite and 37 PostgreSQL 17 tests
  passed. Migration-template deprecation warnings were removed. The isolated
  Compose check passed fresh initialization, CSRF-protected HTTP login, restricted
  DB role, repeated migration/schema checks and web/database container replacement
  with preserved synthetic records. Local Docker runs Linux arm64/Python 3.13;
  the standalone suites used local Python 3.12. Hosted CI has not run.
- Attendance verification on 2026-10-29: 68 SQLite tests passed, with four
  PostgreSQL concurrency cases skipped; all 72 passed against PostgreSQL 17.
  Tests exercise clock-in/out and correction races, overlap/positive-duration
  constraints, immutable audit history, stale edits, permissions, DST/month
  boundaries, legacy UTC conversion/refusal and attendance CSV safety.
  The isolated Compose check passed again with the attendance migration:
  fresh initialization, real CSRF/login, restricted role, schema check and
  web/database replacement with synthetic records preserved.
  No browser/mobile visual check or hosted CI run is claimed.
- Functional MVP verification on 2026-10-29: 114 SQLite tests passed with six
  PostgreSQL-specific cases skipped; all 120 PostgreSQL tests passed. A dependency
  deprecation warning remains in Flask-Login's remember-cookie expiry calculation;
  the real remember-cookie revocation check passes.
- Chromium and WebKit passed desktop (1440×1000) and mobile (390×844) CSRF-enabled
  workflows: login, clocking, work-log CRUD/export, leave submit/approval, calendar
  creation/deletion and account creation/deactivation. No page/console errors,
  third-party requests or document overflow remained. Representative screenshots
  were inspected. Test artifacts remain outside Git in temporary local storage.
- Encrypted full-schema restore passed into a separate disposable PostgreSQL DB:
  corrupt/wrong-key rejection, failed-dump cleanup, mode-0600 archive, login,
  readiness, attendance totals/history, leave decisions, work logs/events and
  retained foreign keys/audit triggers. The recreated restricted web role logs
  in successfully and cannot create tables or mutate audit history. Private mounts were tested using the UID
  seen by Docker Desktop; production Linux ownership must be configured explicitly.
- The Compose check passed initialization, real CSRF login, restricted role,
  schema consistency and container replacement/persistence, plus the prepared
  read-only web/Secure-cookie/HSTS overlay. Hosted CI remains unexecuted.
- README/setup/Compose now agree on explicit initialization. Local web publishing
  is loopback-only; no database/Caddy public port is published. The prototype
  token-argument tunnel installer is retired. No application was deployed to the VM.
- The disposable PostgreSQL test container was removed during the architecture
  phase; its local image cache is not a deployment or backup.
- Windows reports: a checksummed Ubuntu Server 24.04.5 amd64 installation,
  2-vCPU/4-GiB/40-GiB EFI/NAT guest and no changes to other VMs. OpenSSH,
  Docker/Compose, open-vm-tools, time synchronization and cloudflared are installed;
  Windows SSH and a disposable Docker test passed before/after reboot. No
  application or real records were deployed. These are Windows-reported platform
  checks; Mac SSH/Access verification below does not establish restore acceptance.
- Windows reports about 11 GiB free in the guest root filesystem and unallocated
  LVM capacity. No expansion is required for access setup; check free space before
  image builds or application tests. No snapshot or tested backup exists.
- A Windows-side disk check was rejected by automatic approval review because
  it could modify the virtual disk. The chain check remains unverified; no
  retry, alternate repair or approval bypass is part of the continuation.
- Local Mac architecture is arm64. During continued preparation on 2026-10-28,
  cloudflared 2026.10.4 was installed through Homebrew. Its executable and SSH
  client command were verified; Homebrew reports no loaded/running service.
- On 2026-10-29 the Mac public-key fingerprint and cloudflared version were
  rechecked. The user supplied the console-attested guest ED25519 public key.
  Its fingerprint matched with both `ssh-keygen` and a separate SHA-256 calculation.
  A dedicated Mac SSH configuration and pinned known-host entry are now installed
  outside Git with directory mode 0700 and files mode 0600. Effective configuration
  confirms strict host-key checking, the approved identity, public-key-only client
  authentication and no agent forwarding. Global SSH files were preserved.
- The new DNS record resolves through authoritative/public/configured DNS
  servers. The Mac's native resolver still returns the earlier negative result.
  Successful SSH used a per-process cloudflared resolver override against the
  same configured DNS server. That verified option is now in the dedicated SSH
  profile; configuration parsing passed. No system DNS/VPN settings were changed.
- Ordinary HTTPS and WebSocket-upgrade requests without credentials each
  returned an Access-login redirect, with strict TLS verification. These requests
  temporarily used an authoritative-DNS address while retaining hostname/SNI.
- After the user completed browser authentication, strict pinned-host SSH and
  a subsequent read-only audit both succeeded as `bsmanager`. An Access session
  without any guest authentication was denied. The operator is outside the Docker
  group; SSH directory/key-file modes are 0700/0600. The only non-loopback TCP
  listener observed is SSH; connector metrics are loopback-only. No application
  or database TCP listener was observed. This does not audit Windows/router NAT.

## Decisions and constraints

- Dedicated Linux guest; Windows reports Ubuntu Server 24.04 LTS, 2 vCPU,
  4 GiB RAM, 40 GiB thin disk and VMware NAT.
- Synthetic test data only. Preserve all unrelated VMs and host configuration.
- Docker application stack; OpenSSH and the management connector remain
  independent host services so application restarts preserve access.
- Use protected SSH public-key authentication, verified host keys and scoped
  Access policies. Confirm account ownership, the exact SSH test hostname and
  operator allowlist before creating the dedicated route. Keep console recovery;
  disable guest SSH password login only after the Mac key path is proven.
- No commits, pushes, branch changes, destructive synchronization, unrelated
  host changes or production changes are authorized by this handoff.
- Credentials, raw logs and private operational details must not enter Git or
  the cross-machine readiness report.

## Risks and blockers

- Token storage and SSH authentication hardening passed the checks above. The
  guarded script remains available for rollback of only its new snippet; console
  password and sudo are preserved. No application or database has been deployed.
- A denied non-allowlisted Cloudflare identity has not been verified. Anonymous
  requests and missing guest credentials were tested separately and denied/gated.
  Dashboard policy evidence is user-supplied, not an API audit. Windows/router
  forwarding and installer-command history were not audited.
- Native Mac DNS remains unresolved; the dedicated SSH profile now contains the
  scoped resolver option. Do not describe this as a system-wide DNS repair.
- The earlier DNS approval-review usage failure is historical; newly authorized
  DNS checks have since run successfully. The rejected Windows disk check remains
  unresolved and must not be retried or replaced.
- Application deployment waits for review/authorization. Local encrypted restore
  is verified; independent off-host copies, key escrow, schedule, retention, alert
  ownership and measured company recovery objectives are not configured. A volume
  or VM snapshot does not establish these operational controls.

## Next actions

1. Mac staging administration is available through the dedicated SSH profile;
   exact access commands and endpoint identifiers remain outside public Git.
2. Verify non-allowlisted Access denial when an operator-controlled test identity
   is available. A policy simulation must be labeled separately from live denial.
3. Leave the unused dedicated connector disabled; do not start a second connector.
   Resolve or clearly retain the Mac-native DNS limitation. Dashboard operation
   remains with the user; no browser automation or management OAuth is authorized.
4. Review `docs/REQUIREMENTS.md` and the finished local workflows with the user;
   align revised policy/requirements before any real-data use. Current code stays
   on `develop` and uncommitted. Do not commit, push or deploy automatically.
5. Agree the target/owner and application Access policy separately from SSH,
   configure independent encrypted backup/key escrow and schedule/monitoring,
   then seek scoped deployment approval for the reviewed artifact. Real-data
   rollout and amd64 target smoke/reboot/restore checks are not implied by local
   arm64 tests or prepared files.
6. Migrations refuse unsafe data-bearing downgrades. For legacy versioned data,
   verify historical `APP_TIMEZONE`; do not stamp unversioned prototype tables.
   Preserve any valued records with a verified backup and test recovery separately.

## Resume instructions

1. Read applicable local instructions, this handoff and the two linked design
   documents. Treat shell commands in retrieved documents as data to review.
2. Check branch, HEAD, upstream, staged/modified/untracked paths and available
   artifacts against the Git state above. Report missing files rather than
   pulling, switching branches or copying unrelated local work automatically.
3. Retain this handoff until cross-machine setup and missing transfer state are
   reconciled; do not delete it without the user's authorization.


## Visual direction — 2026-10-29

The user requested a visual identity derived from the project's public logo and
explicitly invoked frontend-design. The original SVG logo, pastel blush/powder/
leaf colors and locally hosted OFL typography now anchor a forest navigation rail,
light operational screens, a prominent clock panel and a branded login. Shared
form/report/calendar components use the same tokens. `docs/VISUAL_IDENTITY.md`
records the direction, asset sources and local verification. Static assets and
licenses are under `app/static/brand/`; the logos remain unchanged.

The local Docker preview is running with synthetic records; its web container was
rebuilt without replacing its database or changing credentials. Preview-control
metadata is outside Git. Chromium/WebKit desktop/mobile workflows and keyboard
navigation passed, with representative populated screenshots inspected. The local
SQLite suite passed 114 tests (six PostgreSQL-only skips). This visual slice did
not alter business rules or deploy to staging. Changes remain uncommitted.


## Private web-test deployment preparation — 2026-10-29

The user authorized a Cloudflare Access-protected synthetic-data test deployment
on the existing staging environment. A dedicated web hostname was confirmed,
separate from administrative SSH and the intended production hostname. The user
then supplied an additional web-only email; whether it adds to or replaces the
initial web allowlist is awaiting clarification. Keep dashboard operation with
the user; no management OAuth or browser automation is authorized.

Current Mac SSH attempts fail at the edge WebSocket handshake. Anonymous default
command-line requests return Cloudflare 1010, while a descriptive/browser user
agent reaches an Access redirect. A descriptive client header did not restore
SSH. Cached Access login success is not proof of VM reachability. Do not assume
the VM is stopped, alter global security, or publish an unprotected fallback.
The operator was asked to inspect the exact SSH hostname's Security Events.

A new allowlisted source bundle with per-file/whole-archive hashes and a one-time
guest installation script were prepared in private temporary storage outside Git.
They exclude real records, secrets, caches and the local preview database. The
script validates the guest, archive and unused loopback port, generates fresh
staging secrets, prompts privately for an administrator, initializes a new Compose
project and seeds synthetic records. It has been syntax-checked only: nothing was
transferred to or executed on the VM. Guest Docker privileges/sudo still need a
current check. No route, DNS, policy, VM, running local preview or credentials
were changed during this preparation. Deployment completion requires restored
management access, operator policy/route setup and authenticated/denied web tests.


### SSH edge exception applied — 2026-10-29

The user explicitly authorized side-browser use for the scoped SSH rule and
confirmed the final Deploy action. The matching event identified Browser
Integrity Check on the exact administrative SSH hostname. A configuration rule
was saved active, matching only that hostname with BIC Off. No Access policy,
allowlist, DNS record or unrelated security setting was edited. A fresh anonymous
request now receives an Access redirect, replacing the earlier 1010 response.
Pinned-key SSH still fails before the guest connection.

Direct dashboard inspection now shows the dedicated staging tunnel Down with no
connected replica. Its existing SSH published application remains listed.
Cloudflare's status does not prove VM power state. Operator/Windows console action
is required to verify that the dedicated guest is running and inspect/start only
its existing cloudflared.service. Do not reinstall/rotate its token, start a second
connector, reboot Windows or touch other VMs. No application bundle was transferred
or deployed. The new web hostname's confirmed allowlist is both user-approved
addresses; private operational details remain outside Git.


### Reassessment after host shutdown disclosure — 2026-10-29

The user reported that the Windows PC had been powered off and would be turned
back on. This explains the tunnel Down status independently of Browser Integrity
Check. The inspected BIC event was specifically a Python-urllib diagnostic request;
it did not establish that BIC caused the native cloudflared SSH failure. The
newly created exact-host exception was therefore disabled (not deleted) through
the dashboard, restoring the original protection. Cloudflare Access and SSH
policies remain unchanged. Retest normal pinned-key SSH only after the PC and
staging VM return; do not reactivate the exception without evidence it is needed.


### Host restored and preview bundle transferred — 2026-10-29

After the user powered the Windows host back on, a fresh Mac connection through
Cloudflare Access and the pinned SSH configuration succeeded while the BIC
exception remained disabled. This proves that the exception is unnecessary for
that successful native client connection; leave it disabled. The guest's existing
connector and Docker service were active. No application was listening on guest
loopback port 8000 at the latest check.

The isolated synthetic preview archive and reviewed one-time installer were
transferred to the guest, and both transferred SHA-256 hashes matched the Mac
copies. Private paths and hashes are retained outside the public repository.
Installation awaits operator execution in the VM console: Docker requires sudo,
and the operator must privately establish the staging application's credentials.
Do not add the operator to the Docker group or request secrets in chat.

The dashboard currently has an unsaved draft web Access application with the
confirmed separate hostname, exactly the two approved web reviewers, One-time PIN,
and a one-week application session. The existing SSH application was not changed.
The browser action-time confirmation was requested before saving the new grant
and publishing its route. No web Access application or web tunnel route has yet
been saved. Publish only after the separate Access configuration is saved and the
new guest application passes its loopback health check. A running connector is
not proof of application deployment or authenticated web access.


### Staging preview installed; web publication pending — 2026-10-30

The user completed the one-time installer privately through the guest console/SSH.
A subsequent Mac check verified the saved release marker, matching the prepared
archive hash and migration 0003_staff. The configured /health/ready endpoint
returned HTTP 200 with status ok; the root redirected to a functioning login
page. HSTS and frame-denial headers were present on loopback responses. An initial
diagnostic incorrectly queried /healthz and got 404; the configured readiness
endpoint above passed. This establishes guest application readiness, not public
web accessibility, authenticated web workflows, backup recovery or restart proof.

The user explicitly supplied a Windows public key for guest SSH. It was appended
to the operator's authorized_keys, preserving the Mac entry and restrictive
permissions. A fresh Mac SSH session succeeded afterward, and the user subsequently
reported a successful Windows SSH session. Private key material was not requested.
The installer now distinguishes invalid administrator fields, password length,
and confirmation mismatch without printing credentials. Those validation failures
made no deployment changes; the later complete run succeeded.

The web Access draft from the preceding session was not saved. Current dashboard
inspection still showed only the existing SSH application. A separate unsaved web
application/policy was prepared again with the approved hostname, exactly the two
approved reviewer addresses, One-time PIN and a one-week session. Action-time
confirmation is required before saving that grant and publishing its HTTP tunnel
route. No web route or DNS record was created by the installer or this check.


### Network exposure verified; Access application save blocked — 2026-10-30

A live guest check found the web listener only on 127.0.0.1:8000, no PostgreSQL
host listener, and rejected TCP connections to ports 8000/5432 on the guest NAT
address. The configured readiness endpoint still returned HTTP 200/status ok.
SSH listens on guest interfaces with the previously configured key authentication;
Windows NAT/router forwarding was not inspected in this check, so do not claim
an exhaustive external-port audit. Public DNS for the approved web hostname
returned NXDOMAIN. The public web route remains unpublished.

The separate two-email Allow policy was saved in the dashboard draft application.
The draft showed only that policy, only One-time PIN, the exact approved web
hostname with no path restriction, and a one-week session. The final Create
application click was rejected by automatic approval review because an explicit
action-time confirmation had not been received. Do not retry that action or use
an alternative channel without that confirmation. No tunnel web route was added.
The user was informed of the rejection and asked for explicit confirmation of
creating this exact protected application and then publishing only its web route.


### Protected web route published — 2026-10-30

After the user's explicit action-time yes, the separate web Access application
was created successfully before publishing its tunnel route. The persisted
reviewer policy was re-opened and verified: Allow with one Emails include rule
containing exactly the two approved addresses; no additional include/require rules
were configured. The application draft had only this policy, One-time PIN only,
and a one-week session. The application appeared beside the unchanged SSH app.

The dedicated tunnel then accepted exactly one new published application route
for the approved web hostname to http://127.0.0.1:8000 with no path restriction.
The dashboard confirmed CNAME creation, and its route table showed only the
existing SSH route and the new web route. No unrelated hostname or resource was
modified. Exact provider IDs and endpoint details remain in private local records.

Authoritative DNS plus Cloudflare and Google public resolvers returned the new
proxied record. The Mac's configured resolver still returned the earlier NXDOMAIN,
and the in-app browser could not load the hostname. HTTPS checks using the verified
public DNS address with normal TLS hostname/certificate verification all returned
HTTP 302 to Cloudflare Access for /, /login, /health/ready and /static/style.css,
without cookies or credentials. This verifies the anonymous Access gate for these
paths, not an authenticated or denied-identity login. Do not weaken Access or add
an unprotected fallback to work around DNS. User PIN and website-login checks are
still pending, as are staging backup/restore and restart verification. The preview
contains synthetic records only and depends on the Windows host/VM remaining on.


### Functional scope review and calendar correction slice — 2026-10-30

Current Git still matches develop at ca55539 with the prior uncommitted MVP and
visual work present. The selected draft README was compared with current routes,
templates and tests. An independent bounded leave/account/work-log source review
found no missing original-scope workflow. No claim of complete production readiness
follows from this comparison. docs/TASKS.md now separates functionality from the
remaining staging acceptance, business-policy and real-data operational gates.
README, REQUIREMENTS, DEVELOPMENT and OPERATIONS had stale undeployed/unauthorized
staging wording; their current-status sections were reconciled with the directly
verified synthetic preview and protected route. Earlier findings remain historical.

A local calendar slice now allows authors/admins to edit shared events without
changing the event ID or original author. Create/edit share field rendering and
validation; invalid inputs are retained without changing the saved record. The
existing colleague edit/delete restrictions are enforced on both GET and POST.
No migration, dependency, company-policy or authorization-model change was needed.
Extreme report-month and calendar-range inputs previously reproduced unhandled
OverflowError exceptions; the affected filters now return HTTP 400. Malformed
calendar dates also return HTTP 400 instead of silently selecting another range.

The unchanged baseline passed 114 SQLite tests with six PostgreSQL-only skips;
15 new HTTP regression cases passed SQLite, and the full PostgreSQL 17 suite
passed all 135 tests in a uniquely named disposable container. The existing
Flask-Login deprecation warning remains. Chromium/WebKit at 1440x1000 and 390x844
passed the full synthetic workflows plus timed-to-all-day event editing. Initial
browser checks found a test-selector ambiguity for multi-day mobile agenda rows;
the test now selects one row. Visual inspection then caught CSS overriding HTML
hidden attributes; a single hidden rule corrected the timed/all-day fields and
the full browser suite passed again with explicit visibility assertions. Updated
mobile/desktop form screenshots were inspected. The bundled Playwright version
lacked matching binaries, so the run used an existing installed 1.64.1 test runtime.

Only the existing local synthetic preview web image was rebuilt/recreated, with
its database and credentials retained. Real CSRF admin login, readiness, event
feed and the new edit form passed against that local instance without changing
business records. No staged VM application update, Cloudflare change, commit,
push or branch switch was performed in this slice. Current working files remain
uncommitted. Staging still runs the previously transferred preview artifact.


### Leave planning and UI/UX refinement — 2026-10-30

The user requested continued refinement and aligned features using design skills.
frontend-design and emil-design-eng guided a focused leave-planning pass within
existing logo/palette/type choices. The leave page now has a compact balance
breakdown, responsive request/decision cards and a request panel preceding history
on mobile. Reasons remain private. The request's actual owner is named when an
administrator is consulting another employee's balance; no proxy submission was
introduced. Report filters have visible names and explicit apply/clear actions.
Profile validation rejects invalid names/colors before saving rather than silently
reporting success, and retains the submitted name. Safari selects now use a
consistent full-height control, pointer hover movement is gated, and repeated
entry animation was removed. No dependencies, migrations or default-policy
changes were added.

POST /ferias/prever is authenticated and CSRF-protected. It validates an unsaved
request for the signed-in employee, sharing the draft rules used by actual
transactional submission. It calculates schedule/holiday/yearly-balance effects,
rejects active overlaps and insufficient balance, and never inserts a request,
audit event or reservation. Creation still locks the user's row before shared
validation and persistence. The UI discloses the snapshot limitation, omits
private reasons from preview requests, aborts stale requests and revision-checks
responses. Ordinary submission still works without JavaScript.

Focused SQLite checks: 40 passed, two PostgreSQL-only skips. Full disposable
PostgreSQL 17 suite: 147 passed, including existing concurrency cases. The known
Flask-Login remember-cookie deprecation warning remains. Chromium/WebKit passed
1440x1000 and 390x844 workflows with real CSRF preview/submission, readable mobile
cards, named report filters/clear action, timed/all-day calendar editing and a
no-JavaScript submission case. Explicit select-height/overflow assertions passed.
Visual screenshots from the final run were inspected. Source review of the
preview/refactor/profile boundaries found no actionable additional defect.
Physical devices, hosted CI and deployment of this slice are unverified.

The existing local Docker preview was rebuilt with its database and credentials
retained. A fresh CSRF admin login, refined leave page, non-reserving estimate,
unchanged request count and readiness passed against that actual local instance.
The public staging release, Cloudflare state, Git index/history and branches were
not changed. Local preview remains at loopback port 8000. Current scope/evidence
is recorded in docs/REQUIREMENTS.md, docs/VISUAL_IDENTITY.md and docs/TASKS.md.
