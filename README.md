# DispoHub

**Open-source dispatch and driver management system for small logistics and
transport companies.**

DispoHub helps small trucking, courier, and transport businesses run their
daily dispatch operations from one place: vehicle records, driver
communication, damage reports, invoices, fuel cards, scheduling, and HR
basics — without paying for a heavyweight fleet-management SaaS platform
built for enterprises.

> **Project status:** DispoHub is a functioning open-source MVP, not a
> polished, fully production-hardened product. It grew out of real use at a
> small transport company and covers a genuinely complete day-to-day
> workflow, but it hasn't been battle-tested across many different
> operations yet. Review [Known limitations](#known-limitations) and
> [Security](#security) before relying on it for your own business — and
> expect to adapt it to your specific processes. See
> [Project status](#project-status) for the full picture.

---

## Table of contents

- [Who this is for](#who-this-is-for)
- [Key features](#key-features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [System requirements](#system-requirements)
- [Quick start (Docker)](#quick-start-docker)
- [Full installation guide](#full-installation-guide)
- [Configuration](#configuration)
- [Roles & permissions](#roles--permissions)
- [First login](#first-login)
- [Language support](#language-support)
- [Email configuration](#email-configuration)
- [Backups & restore](#backups--restore)
- [Database migrations](#database-migrations)
- [Tests](#tests)
- [Updating](#updating)
- [Known limitations](#known-limitations)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Project status](#project-status)
- [Contributing](#contributing)
- [License](#license)

## Who this is for

DispoHub is aimed at **small logistics and transport companies** — think a
handful to a few dozen vehicles and drivers, run out of a single office —
who need dispatch management, driver communication, and basic fleet
operations software, but for whom enterprise fleet-management platforms are
overkill (or overpriced). It's built to be self-hosted and adapted to your
own workflow rather than used as a rigid one-size-fits-all SaaS product.

If you're a developer, it's also a reasonably complete example of a
server-rendered FastAPI + Jinja2 application: role-based access control,
CSRF protection, file uploads, WebSocket chat, PDF/CSV export, and a small
custom i18n system, all without a frontend build step.

## Key features

**Dispatch & fleet operations**
- Damage report workflow (driver report with photos → office review →
  workshop appointment → cost booking)
- Vehicle records: inspection deadlines, contracts, costs, documents,
  interactive damage-location diagram
- Invoice inbox with rule-based pre-sorting and a monthly tax export
  (CSV + PDF), plus a raw-receipt "filedrop" for your accountant
- Fuel card CSV import with automatic cost booking
- Task list, quick yes/no polls to drivers, internal notes, birthday
  reminders, safety-equipment expiry tracking
- Month-grid calendar (date × vehicle) with driver vacation/sick-leave rows
- Vacation requests with an approval workflow and automatic balance
  tracking
- Employee records: driver-card/qualification expiry, vacation balance,
  sick-leave log, working hours, documents
- Printable forms (timesheet, fuel log, leave request/confirmation) with
  your company logo
- GPS parking-location reporting with a free OpenStreetMap map (no paid
  mapping API)

**Driver mobile app** (installable as a PWA)
- Real-time chat (1:1 and groups) with photo and voice-message attachments
- On-call page showing office/management contacts with a live
  green/red reachability indicator
- Self-service password change
- Available in 6 languages (see [Language support](#language-support))

**Administration**
- Create/manage users and vehicles in the UI, with a 30-day recycle bin
  instead of instant deletion
- Per-area permission matrix for the office role
- Company logo upload
- One-click database backup download

**Security** — see the [Security](#security) section for details:
CSRF protection on every form, login rate-limiting, hashed passwords with
forced first-login password changes, role-based access control.

## Screenshots

Screenshots (dashboard, a vehicle record, the driver mobile chat view, and
the calendar grid — all with fictional demo data, no real company
information) are planned but not yet included in this release; see
[`docs/screenshots/`](docs/screenshots/) for what's needed and how to add
them. Until then, the fastest way to see the app is the
[quick start](#quick-start-docker) below — it's running in a couple of
minutes with realistic demo data pre-loaded.

## Architecture

DispoHub is a server-rendered web application — no separate frontend build,
no SPA framework. Pages are rendered with Jinja2 templates; a small amount
of vanilla JavaScript handles the chat WebSocket connection, camera/photo
pickers, and voice recording.

```
Browser  ──HTTP/WebSocket──►  FastAPI app (Uvicorn)
                                 ├─ Jinja2 templates (server-rendered HTML)
                                 ├─ SQLAlchemy ORM ──► PostgreSQL (Docker) or SQLite (local dev)
                                 ├─ Alembic migrations
                                 └─ In-process WebSocket manager (chat)
```

Session authentication uses signed, `HttpOnly` cookies (no separate auth
service/JWT layer). All state-changing requests go through standard HTML
forms and are protected by an automatically-injected CSRF token — there is
no JSON API surface. See [SECURITY.md](SECURITY.md) for the full writeup.

## Technology stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12),
  [SQLAlchemy 2](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/)
- **Database:** PostgreSQL (Docker deployment) or SQLite (local development)
- **Templates:** Jinja2, server-rendered, no frontend build step
- **Real-time:** native WebSockets (FastAPI/Starlette), no external broker
- **Auth:** signed session cookies (`itsdangerous`), `passlib`/`bcrypt`
  password hashing
- **PDF export:** [fpdf2](https://github.com/py-pdf/fpdf2)
- **Maps:** [Leaflet](https://leafletjs.com/) + OpenStreetMap tiles
  (self-hosted assets, no API key)
- **Tests:** pytest (148+ tests) with FastAPI's `TestClient`
- **Deployment:** Docker Compose (Postgres + app + Adminer)

Only technologies actually used in this codebase are listed above.

## System requirements

**Docker deployment (recommended):**
- Docker Engine 24+ and Docker Compose v2
- ~1 GB RAM for the containers, minimal disk space for a small fleet

**Local/manual deployment:**
- Python 3.12+
- SQLite (bundled with Python) for development, or your own PostgreSQL 14+
  instance for production

**Browser support (client side):** any modern evergreen browser (Chrome,
Firefox, Edge, Safari). The driver app is an installable PWA and uses the
browser's Geolocation, MediaRecorder (voice messages), and Notification
APIs where available — these degrade gracefully if unsupported.

## Quick start (Docker)

```bash
git clone https://github.com/Relis-lol/dispohub.git
cd dispohub
cp .env.example .env
docker compose up --build
```

Then open **http://localhost:8000** and log in with one of the
[demo accounts](#first-login). An optional database UI (Adminer) is
available at **http://localhost:8080**.

Stop the stack with `docker compose down` (add `-v` to also remove the
database volume and start fresh next time).

## Full installation guide

### Option A — Docker Compose (recommended for trying it out or a real deployment)

1. Install Docker Engine + Docker Compose v2 if you haven't already.
2. Clone the repository and enter it:
   ```bash
   git clone https://github.com/Relis-lol/dispohub.git
   cd dispohub
   ```
3. Copy the environment template and review it:
   ```bash
   cp .env.example .env
   ```
   For a real deployment, at minimum change `SECRET_KEY` to a random value
   (see the comment in `.env.example` for how to generate one) and set
   `SESSION_COOKIE_SECURE=true` once you're behind HTTPS.
4. Build and start everything:
   ```bash
   docker compose up --build
   ```
   This starts PostgreSQL, applies database migrations automatically, and
   (by default) seeds demo data. The app is served on
   `http://localhost:8000`.
5. To stop: `docker compose down`. Your data persists in the `pgdata`
   Docker volume between restarts; `docker compose down -v` removes it.

### Option B — Local Python environment (no Docker, SQLite)

Good for development or a very small single-machine deployment.

```bash
git clone https://github.com/Relis-lol/dispohub.git
cd dispohub
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # defaults to a local SQLite database
alembic upgrade head
uvicorn app.main:app --reload
```

Open **http://localhost:8000**.

> Chat uses an in-process WebSocket broadcast, so run with a **single**
> Uvicorn worker (no `--workers`, no multi-instance deployment) unless you
> first move that state to something shared like Redis — see
> [Known limitations](#known-limitations).

## Configuration

All configuration is via environment variables, documented in
[`.env.example`](.env.example). Copy it to `.env` and adjust as needed. Key
variables:

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs session cookies. **Change this before any real use.** | insecure placeholder (app warns on startup if unchanged) |
| `DATABASE_URL` | SQLAlchemy connection string (SQLite or PostgreSQL) | local SQLite file |
| `SEED_ON_STARTUP` | Load demo data if the database is empty | `true` |
| `SESSION_COOKIE_SECURE` | Send the session cookie only over HTTPS | `false` (set `true` behind HTTPS) |
| `IMAP_HOST` / `IMAP_USER` / `IMAP_PASSWORD` / `IMAP_ORDNER` | Optional real invoice-mailbox intake | unset (invoice intake stays simulated) |

## Roles & permissions

DispoHub has four roles:

| Role | Access |
|---|---|
| **Admin** | Full access to everything, including user/vehicle management and settings |
| **Management** (Geschäftsführung) | Same as Admin except a couple of admin-only settings; can approve leave, manage permissions, view all cost/financial data |
| **Office** (Büro) | Access is configurable per area (vehicles, employees, calendar, damages, costs, invoices, tax export, fuel cards, tasks) via a settings page — office staff see whichever areas are enabled |
| **Driver** | Mobile-only view: chat, damage/parking/vacation reporting, tasks, on-call contacts, own password — no access to office/financial data |

There's also a narrow **IT** view intended for technical staff who need to
see vehicle/employee lists without financial data — it's a minimal
read-mostly page, not a full role tier.

## First login

Demo credentials (seeded automatically when `SEED_ON_STARTUP=true` and the
database is empty — **change or remove these before using DispoHub with
real data**):

| Role | Email | Password |
|---|---|---|
| Admin | `admin@dispohub.example` | `admin123` |
| Management | `gf@dispohub.example` | `gf123` |
| Office | `buero@dispohub.example` | `buero123` |
| IT | `it@dispohub.example` | `it123` |
| Driver | `fahrer1@dispohub.example` | `fahrer123` |
| Driver | `fahrer2@dispohub.example` | `fahrer123` |

Drivers land directly in the mobile chat view; office/management land on the
dashboard.

To create real accounts once you're ready: log in as Admin or Management →
**Administration** → create employees there. New accounts get a random
one-time password shown once on screen, and the new user is required to set
their own password on first login.

## Language support

The **driver-facing app** (login, chat, damage/parking/vacation reporting,
tasks, on-call contacts, change password) is available in:

🇩🇪 German · 🇨🇿 Czech · 🇬🇧 English · 🇷🇺 Russian · 🇵🇱 Polish · 🇹🇷 Turkish

A flag switcher is shown on the login page and in the driver app's header;
the choice is stored in a cookie (no account setting needed).

The **office/management side** (vehicles, costs, invoices, administration,
etc.) is currently **German only** — that's where the original operation
this was built for does its office work, and translating that much
additional surface was out of scope for this release.

> ⚠️ **Translation quality note:** the Czech, English, Russian, Polish, and
> Turkish translations were AI-generated and have **not** been reviewed by
> native speakers. They should be understandable, but expect some rough
> edges — corrections are very welcome, see
> [Contributing → Translations](CONTRIBUTING.md#translations).

## Email configuration

Invoice intake is **simulated by default** (a "simulate inbox" button
generates realistic demo invoices so you can try the review workflow).

Real IMAP-based intake is implemented and ready to use
(`app/services/mail_ingest.py`) — set `IMAP_HOST`, `IMAP_USER`,
`IMAP_PASSWORD`, and `IMAP_ORDNER` in `.env` and the "simulate" button is
replaced with a "fetch inbox" button that pulls real unread mail from that
mailbox and runs it through the same rule-based categorization.

**Use a dedicated mailbox** (e.g. `invoices@yourcompany.example`) with its
own credentials — this feature needs full read access to whatever mailbox
you point it at, so don't use a personal or admin inbox.

Outbound email (e.g. automatically emailing the monthly tax export to your
accountant) is **not implemented** — the export is a manual CSV/PDF
download and a receipt "filedrop" your accountant can pull from instead.

## Backups & restore

Admin/Management can download a full database backup at any time from
**Administration → Download backup**. For SQLite, this uses SQLite's own
backup API to produce a consistent snapshot even while the app is running
(no risk of grabbing a half-written file).

This is a **manual, on-demand** download — there is no automated backup
schedule built in. For a real deployment, either:
- Download the backup regularly yourself and store it somewhere safe, or
- If running the Docker/PostgreSQL setup, back up the `pgdata` Docker
  volume using your usual PostgreSQL backup approach (`pg_dump`, volume
  snapshots, etc.) — the in-app download button is SQLite-only.

**To restore** a SQLite backup: stop the app, replace the database file
with the downloaded backup, restart.

## Database migrations

Schema changes are managed with Alembic. Docker Compose applies migrations
automatically on container start (`alembic upgrade head` runs before the
app starts, see `Dockerfile`). For a local/manual setup:

```bash
alembic upgrade head
```

After changing a model, generate a new migration:

```bash
alembic revision --autogenerate -m "short description"
alembic upgrade head   # verify it applies cleanly
```

Local development also runs `create_all()` on startup as a convenience
fallback so you can start hacking without running migrations first — this
only creates missing tables, it never alters existing ones, so don't rely
on it for schema changes once you have real data.

## Tests

```bash
pytest
```

148+ tests cover the core workflows, permission boundaries, CSRF
protection (with a dedicated test client that has CSRF checks turned back
on — the rest of the suite disables them for convenience, see
`tests/conftest.py`), internationalization, and more.

## Updating

```bash
git pull
# Docker:
docker compose up --build
# Local:
pip install -r requirements.txt
alembic upgrade head
```

Always check [CHANGELOG.md](CHANGELOG.md) for breaking changes before
updating a deployment with real data, and take a backup first (see
[Backups & restore](#backups--restore)).

## Known limitations

- **No independent security audit** — see [Security](#security).
- **Single-process assumptions:** the chat WebSocket broadcast and login
  rate-limiting are both in-memory. Don't run multiple Uvicorn workers or
  multiple app instances without addressing this first.
- **No automated email intake by default** — the code is ready, but needs
  you to provide real mailbox credentials (see
  [Email configuration](#email-configuration)).
- **No outbound email** (e.g. no automatic emailing of reports/invoices).
- **No multi-factor authentication.**
- **No automated/scheduled backups** — download is manual (Docker/Postgres
  users should use standard Postgres backup tooling instead).
- **Office/management UI is German-only.**
- **Machine-translated driver UI** — see the translation quality note
  above.
- **Not independently validated in production at scale** — see
  [Project status](#project-status).

## Security

CSRF protection, session cookie hardening, password handling, rate
limiting, access control, and file-upload validation are all documented in
detail in [SECURITY.md](SECURITY.md), along with how to report a
vulnerability. Please read it before deploying with real company data.

## Troubleshooting

**"SECRET_KEY is still the placeholder" warning on startup**
Expected in a fresh checkout. Set a real random value in `.env` before any
non-local use (see the comment in `.env.example`).

**`(trapped) error reading bcrypt version` on startup**
Harmless. It's a known compatibility quirk between `passlib` 1.7.4 (its
last release) and `bcrypt` >= 4.1, which removed an internal attribute
`passlib` uses only to log its version — password hashing and verification
both work correctly despite the warning.

**Login redirects back to the login page with no error**
Check that cookies aren't being blocked by the browser (session auth
requires cookies) and, if running behind a reverse proxy, that it forwards
the `Host` header correctly.

**Docker: `db` service never becomes healthy**
Check `docker compose logs db` — usually a port conflict on 5432 with an
existing local Postgres install, or insufficient disk space for the
volume.

**Chat doesn't update in real time**
Confirm you're running a single Uvicorn worker (see
[Known limitations](#known-limitations)) and that nothing between the
browser and the server is buffering/blocking WebSocket upgrades (some
reverse proxy configs need explicit WebSocket passthrough rules).

**"Kein Zugriff" / access-denied page after switching roles in another tab**
Session auth is per-browser, not per-tab — logging in as a different demo
user in one tab changes the session for all tabs sharing that cookie jar.
Use a private/incognito window to test multiple roles side by side.

**Migrations fail on an existing database that predates migrations**
If you have an older database that was only ever created via `create_all()`
(no Alembic history), stamp it to the current baseline instead of
re-running every migration from scratch:
```bash
alembic stamp head
```
Then verify your schema actually matches the models before relying on this.

## Project status

DispoHub is a **functioning open-source MVP**, built from and for a real
small transport/logistics operation, then generalized for public release.
It is:

- ✅ Feature-complete for a real day-to-day dispatch/office workflow at a
  small operation (see [Key features](#key-features))
- ✅ Covered by an automated test suite (148+ tests)
- ⚠️ **Not** independently security-audited — see [Security](#security)
- ⚠️ **Not** validated across a range of different transport companies'
  workflows — you should expect to adapt it to your own processes
- ⚠️ Likely to need further polish around translations, third-party
  integrations (email, deployment automation), and operation-specific
  business rules before a larger production rollout
- ⚠️ Pre-1.0 — expect breaking changes between releases until a 1.0 is
  tagged

If that matches what you're looking for — a real, working starting point
you can self-host and adapt, rather than a finished polished product —
DispoHub should be useful to you today.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for
development setup, code style, and how translation corrections work.

## License

[MIT](LICENSE).
