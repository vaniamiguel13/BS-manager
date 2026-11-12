# Visual identity — first direction

Designed: 2026-10-29. Subject: the internal BreastScreening-AI team workspace.
The main job is to make clocking, work records and team availability easy to use.

The source is the project's original logo from https://breastscreeningai.eu/.
Original SVGs are stored unchanged in `app/static/brand/`, with source URLs/hashes.
This is a product direction for review, not an official company brand manual.

## Tokens and layout

| Token | Value | Role |
| --- | --- | --- |
| Logo blush | `#FFDEF6` | Warm identity accent and review/leave surfaces |
| Logo powder | `#BFD5FF` | Active navigation and time/report accents |
| Logo leaf | `#5FC28A` | Identity accent and positive state |
| Forest | `#173F38` | Sidebar, clock panel and strong contrast |
| Ink | `#203C43` | Body text and headings |
| Cloud | `#F3F6F8` | Quiet workspace background |

Logo pastels are accents; dark derived colors carry text and actionable controls.
Errors and warnings retain distinct semantic colors. Body: Manrope; display:
Bricolage Grotesque, used for headings and key values. Fonts are self-hosted under
SIL OFL, with their licenses and provenance alongside them. Data uses tabular
figures and a restrained monospace treatment for elapsed time.

Desktop uses a fixed forest navigation rail, a slim context bar and a generous
content area. Mobile folds navigation into a keyboard-accessible menu and keeps
clocking prominent. Reports scroll within their cards; the calendar retains its
own responsive layout. The signature is the original pastel logo on forest,
echoed in blush/powder/leaf section accents. No decorative medical imagery or
claims about clinical capability are added to this staff-management tool.

The initial direction deliberately keeps the operational screens light: a fully
dark dashboard would reduce the separation between brand and dense data. Motion
is limited to short state/entry transitions and respects reduced-motion settings.


## Local verification

The first direction is implemented in the shared shell, dashboard and login,
with the component palette applied to every report/form/calendar. Original logo
geometry/colors are unchanged. Browser assets and fonts are served locally.
Chromium and WebKit desktop/mobile workflows pass, including reduced motion and
keyboard menu operation. The SQLite suite passed 114 tests, with six PostgreSQL-
only cases skipped; the existing upstream remember-cookie deprecation warning
remains. No business rules, schema or live Cloudflare resources changed.
The local Docker preview was rebuilt while preserving its synthetic database.

## Workflow refinement — 2026-10-30

The frontend-design and emil-design-eng skills guided a focused leave-planning
pass within the existing identity. A compact mint balance summary replaces three
stacked mobile statistics cards. Readable request cards show date, status,
decisions and actions without horizontal table scrolling. The blue-accented
request panel appears before history on small screens; the desktop layout pairs
history with planning. Pending administrator decisions remain a distinct queue.

Selecting dates shows a read-only working-day and annual-balance estimate. The
server shares validation with submission, uses the signed-in employee's schedule
and holidays, and never reserves days during preview. The interface makes this
limit explicit and names the request owner when an administrator views another
employee's balance. Missing JavaScript does not prevent ordinary submission.
Private reasons are not sent to the estimate endpoint.

Report filters now have visible labels and an explicit apply action. Profile
validation reports invalid names/colors instead of silently claiming success.
Native selects use consistent sizing across browser engines; hover movement is
restricted to precise pointers, and repeated dashboard entry animation was
removed. No new fonts, packages, company-policy defaults or clinical content were
introduced. Verification results are recorded in REQUIREMENTS.md and HANDOFF.md;
physical-device testing and hosted deployment of this slice are not claimed.

## Copy and language — 2026-11-01

The login uses “Gestão da equipa” / “Team workspace”, with a short description of
attendance, work logs and leave. Removing the forced line break fixes the joined
words seen when mobile CSS hid that element. Plain instructions replace the
previous welcome/marketing language. A compact, keyboard-accessible PT/EN control
sits above the guest card and in the workspace header, using the existing forest
and neutral tokens. The active language has an explicit pressed state; changing
it uses an ordinary server form and works without JavaScript. Native-language
button labels stay understandable before a choice is made.

Labels, feedback, calendar controls and estimates switch together. Names, entered
notes and original record contents remain untouched. Desktop and mobile Chromium
and WebKit screenshots were inspected; automated overflow and workflow checks
passed in both languages. This remains browser-engine evidence, not an iPhone or
Android device test. The local preview is refreshed; this slice is not hosted yet.

## Navbar, report alignment and dark theme — 2026-11-01

The user rejected the sidebar/header arrangement. The product label is now
“Management”, aligned horizontally with the original logo. A full-width navbar
replaces the desktop rail and duplicate breadcrumb row; content no longer loses
244 px to navigation or stops at the old maximum width. Tablet navigation wraps
onto a second header row; mobile navigation uses a compact two-column menu.
Language and theme controls remain together. Account/profile/sign-out controls use
a native disclosure, including when JavaScript is unavailable. Keyboard menus
support Enter/Space and Escape, and active links expose their current-page state.

Report headings/actions, labelled filters and exports now have distinct rows.
Filters and export controls share a 44 px height and bottom baseline on desktop;
mobile fields stack and export buttons wrap within the available width. The
header and content share one gutter token. The workspace fills the viewport
without assuming a fixed header height when the tablet navbar wraps.

Dark mode uses dark forest-neutral surfaces, readable mint/blush/blue accents and
dark form/dialog/calendar surfaces. The logo and user-selected event colours are
preserved. The theme button sits beside PT/EN, exposes a pressed state and stores
only a presentation preference. It follows the system initially, retains manual
choices across navigation, synchronizes tabs, and still toggles if storage is
unavailable. Without JavaScript, the theme button stays hidden; native navigation,
account controls and form submission remain usable.

Chromium/WebKit checks pass at 320, 390, 700, 760, 761, 768, 1024, 1240, 1241, 1280,
1440 and 1920 px in PT/EN, both roles and both themes. Checks cover full available
width, no page overflow, navbar non-overlap, common gutters, report baselines,
keyboard menus and theme persistence. Representative screenshots were inspected.
This is browser-engine evidence; physical-device testing is not claimed.

## Type scale, mobile dock and record layouts — 2026-11-12

Body text is now 15 px and the smallest interface text 12 px. Hover styles apply
only to hover-capable fine pointers; controls have a press state, 16 px inputs on
coarse pointers and suitable `inputmode`/`autocomplete` hints. The viewport covers
the safe areas and `theme-color` follows the header in each theme.

At 760 px and below the navigation is a floating translucent dock above the
bottom safe area, with five destinations and the current one filled. It replaces
the two-column menu. The top bar keeps the logo, “Management”, PT/EN, theme and
the account menu, which also holds Users for administrators. The dock is ordinary
links, so it works without JavaScript. It moves aside while a text field is
focused, while a form control is pressed and while a dialog is open, and becomes
opaque when transparency is reduced or `backdrop-filter` is unsupported. Desktop
and tablet keep the full-width navbar. A leaf dot marks Picagens while clocked in.

Attendance and work-log tables render as day-grouped cards at 900 px and below instead
of scrolling sideways. Attendance lists show `HH:MM`; the full timestamp stays in
the title attribute, the history page and CSV. Month navigation uses icon buttons
with a current-month link and a summary row. Dialogs open as bottom sheets on
phones. Leave balances gain a segmented bar beside the unchanged figures, weekday
schedules are chips, and audit histories are lists of dated change cards.

Home-screen icons (180, 192, 512 and maskable 512 px) are rendered from the
unmodified `symbol.svg` on the forest colour and recorded in `brand/sources.json`.
The web manifest declares standalone display. No service worker or offline mode
exists, because pages are authenticated and served `no-store`.

Verified on 2026-11-12 with local synthetic data: `scripts/check-browser.py` and
`scripts/check-browser.py --responsive` pass in Chromium and WebKit, covering
320–1920 px, PT/EN, both roles, both themes, dock position, label clipping and
content clearance. Screenshots at 390 and 1440 px were inspected in both themes.
This is browser-engine evidence. Touch feel, translucency on hardware, safe areas,
input zoom and installed standalone launch on a physical phone are not verified,
and nothing here is deployed.
