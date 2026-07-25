# Changelog

All notable changes to this project are documented in this file.
The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-07-25

Initial public release. DispoHub was developed iteratively as an internal
tool before this release; this entry summarizes the resulting feature set
rather than the development history.

### Added

**Core dispatch & fleet operations**
- Damage report workflow: driver report with photos → management inbox →
  acceptance → workshop appointment → cost booking.
- Vehicle records with inspection/contract deadlines, cost tracking,
  document/photo storage, and an interactive damage-location diagram.
- Invoice inbox with rule-based pre-sorting (sender, subject keywords,
  license-plate detection, duplicate detection) and a monthly tax-export
  (CSV + PDF) for handing off to an accountant, plus a raw-receipt filedrop
  for documents that don't need individual invoice entry.
- Fuel card import (CSV) with automatic cost booking and duplicate detection.
- Task list, polls (quick yes/no questions to drivers), internal notes,
  birthday reminders, safety-equipment (e.g. ADR) tracking with expiry
  alerts.
- Month-grid calendar (date × vehicle) with vehicle appointments and
  driver vacation/sick-leave rows; appointments can be entered and closed
  directly from the grid.
- Vacation request workflow: drivers request via the mobile app, office/
  management approve with a remaining-balance check; approved leave is
  posted automatically to the employee's leave account and shows up on the
  calendar.
- Employee records ("personnel file") with driver-card/ADR-card expiry,
  vacation balance, sick-leave log, working-hours log, document upload, and
  private notes.
- Printable forms (timesheet, fuel log, leave request, leave confirmation)
  generated from live data with your company logo, ready to print or
  save as PDF via the browser.
- Parking-location reporting (driver shares GPS + optional photo; shown on
  a free OpenStreetMap/Leaflet map with a "open in Google Maps" deep link —
  no paid mapping API required).

**Driver mobile app**
- Chat: 1:1 and group threads, real-time via WebSocket, photo and voice-
  message attachments, "convert to damage report" action, unread badges,
  own-message delete (time-limited).
- On-call/availability page: office and management contacts shown with a
  green/red reachability indicator (manual toggle or a time-window
  schedule), with a confirmation prompt before calling someone marked
  unavailable.
- Self-service password change.
- Language switcher (see "Internationalization" below).

**Administration**
- User and vehicle management in the UI (create/soft-delete) with a
  30-day recycle bin and automatic permanent deletion after that window.
  New employees get a random one-time password and are required to set
  their own on first login.
- Per-area permission matrix for the Office role.
- Company logo upload (shown in the sidebar and on printable forms).
- One-click database backup download (SQLite) for admins/management.

**Internationalization**
- Driver-facing pages (login, chat, report/melden, tasks, contacts,
  change password) are available in German, Czech, English, Russian,
  Polish, and Turkish, with a flag-based switcher. Office/management pages
  are German-only for now. See the README for translation-quality caveats.

**Security**
- CSRF protection on all forms (automatically injected token, no manual
  per-form wiring required).
- Login rate-limiting (5 failed attempts → 15-minute lockout).
- Session cookies: `HttpOnly` always, `SameSite=Lax`, `Secure` configurable
  for HTTPS deployments.
- Bcrypt password hashing; random one-time passwords for new accounts.
- See [SECURITY.md](SECURITY.md) for the full security posture writeup.

**Deployment**
- Docker Compose setup (PostgreSQL + app + Adminer) with healthchecks and
  a persistent volume.
- Alembic database migrations, applied automatically on container start.
- `.env.example` covering all configuration options.

### Known limitations

See the README's "Known limitations" and "Project status" sections —
notably: no automated email intake configured out of the box (the IMAP
code is ready but needs a real mailbox), no multi-factor authentication,
single-process assumptions for chat/rate-limiting, and unreviewed machine
translations for five of the six supported languages.
