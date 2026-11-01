# Remaining implementation and release work

Updated and reconciled: 2026-11-01. This tracker does not grant authorization for
Git publication, access changes, external communications or real-data use.

## Delivered and verified

The narrow MVP scope is implemented: attendance, work logs, leave/availability,
team calendar and users. [REQUIREMENTS.md](REQUIREMENTS.md) maps features to local
acceptance; [RELEASE_READINESS.md](RELEASE_READINESS.md) records exact deployment
and verification boundaries.

- [x] Review the implementation and fix discovered authentication/date/secrets
  defects; complete the PostgreSQL suite (189 passing tests).
- [x] Verify full local administrator/employee workflows in Chromium and WebKit,
  PT/EN, light/dark, no-JavaScript forms, and responsive layouts at 320–1920 px.
- [x] Fix navbar loading shifts, align controls, refine calendar and users, and
  remove decorative slogans/labels/card-top accents; refresh the local preview.
- [x] Commit reviewed source and deploy application commit `88b81e5` to the
  existing synthetic demo, preserving credentials, database and connector.
- [x] Verify exact served assets, readiness, secure cookie/response settings and
  anonymous Cloudflare Access redirects after deployment.
- [x] Restore the actual encrypted pre-update backup in an isolated Mac database;
  all nine data/history fingerprints match. Retain private recovery materials.
- [x] Verify runtime image/hardening, loopback-only web, unpublished database,
  retained rollback image/backup, effective SSH settings and services.
- [x] Restart only demo web and verify readiness recovery and unchanged records.
- [x] Operator confirms public Access/application sign-in reaches the dashboard.

## Hosted acceptance and feedback follow-up

- [ ] Verify denial for an operator-controlled non-allowlisted identity. Anonymous
  redirects and saved policy do not by themselves prove this flow.
- [ ] Run representative administrator and employee CRUD workflows on synthetic
  hosted records. Full automated workflows currently prove local acceptance.
- [ ] Confirm the second approved reviewer has a named application account;
  Cloudflare Access enrollment alone does not create one.
- [ ] Coordinate whole-VM reboot/host-outage acceptance for this application.
  Current web-container restart and persistence checks pass; historical guest
  SSH/connector reboot tests predate the app.

## Before real company records

- [ ] Confirm internal-only tracking versus official/payroll use.
- [ ] Agree company entitlement, part-time schedules, holidays, correction rules,
  administrator self-approval and leave privacy. Defaults remain configurable.
- [ ] Approve an always-on host, patching/monitoring and maintenance ownership.
  The personal Windows/VM placement is preliminary and stops with its host.
- [ ] Select independent encrypted-backup storage, recovery-key custody,
  schedule/retention, failure alerts and measured RPO/RTO. The actual off-VM restore
  passed; a recurring independently operated disaster-recovery service is not set up.
- [ ] Run hosted CI after separately authorizing a push; local checks do not prove
  hosted CI success.

CRM, subscriptions, accounting, notifications, kanban, QR/geolocation, overtime
reports and SSO remain outside the agreed MVP. Align new features to a concrete
company requirement.
