# Security Policy

## Reporting a vulnerability

If you find a security issue in DispoHub, please **do not open a public issue**.
Instead, open a [GitHub Security Advisory](../../security/advisories/new) on
this repository, or contact the maintainer directly. Please include steps to
reproduce and, if possible, the impact you'd expect in a typical small-fleet
deployment.

We'll acknowledge reports as quickly as we can on a best-effort basis — this
is a community-maintained open-source project without a dedicated security
team or SLA.

## Supported versions

DispoHub is pre-1.0 software. Only the latest tagged release is supported;
please upgrade before reporting an issue if you're running an older version.

## Security posture (as of the v0.1.0 release)

This section documents the state of the built-in security controls, so
operators can make an informed decision before deploying DispoHub with real
data. It reflects a self-review by the project's maintainer(s), not an
independent third-party audit.

### CSRF protection

- All state-changing requests in DispoHub go through standard HTML forms
  (`application/x-www-form-urlencoded` or `multipart/form-data`) — **there is
  no JSON API surface**, so there is nothing to carve out a CSRF exemption
  for. `app/services/csrf.py` implements a middleware that:
  - Automatically injects a per-session, random (`secrets.token_hex(16)`)
    hidden `csrf_token` field into every outgoing `<form method="post">`.
  - Rejects any incoming POST with form-encoded or multipart data whose
    `csrf_token` doesn't match the session's token, returning a friendly
    HTML error page (not a bare JSON error).
  - JavaScript-driven submissions (e.g. the chat send button, which uses
    `fetch()` with `FormData`) inherit the token automatically because the
    token field lives inside the `<form>` element they read from.
- **Documented exemption:** `GET /logout` (a plain link, not a form) changes
  only the requesting user's own session and carries no session cookie when
  triggered cross-site (see `same_site="lax"` below), so no CSRF token is
  required for it. This is explained in a code comment in
  `app/routers/auth.py`. If `/logout` is ever posted to as a real form with
  form-encoded data, the same CSRF middleware still applies to it.
- WebSocket connections (`/ws/chat/{id}`) are session-cookie-authenticated
  but read-only from the client's perspective (used only to keep the
  connection alive; all message sending happens via the CSRF-protected POST
  endpoint). An `Origin` header check was added to reject cross-site
  WebSocket handshakes, since browsers do not restrict cross-origin
  WebSocket connections the way they restrict `fetch`/XHR.
- Test coverage: `tests/test_csrf.py` covers valid tokens, missing tokens,
  invalid tokens, tokens from a different session, plain HTML forms, login,
  file uploads (multipart), JS/`fetch`-style requests, and that error
  responses are human-readable HTML rather than raw JSON.

### Session cookies

- `HttpOnly` is always set (hardcoded by Starlette's `SessionMiddleware`,
  not configurable to be disabled).
- `SameSite=Lax` is set explicitly.
- `Secure` is controlled by `SESSION_COOKIE_SECURE` (default `false` for
  local HTTP development — **set this to `true` once you deploy behind
  HTTPS**).
- The signing key (`SECRET_KEY`) defaults to an obviously-fake placeholder
  and the app logs a startup warning if it's still set to that value.
  **Always set a real, random `SECRET_KEY` before any non-local use.**

### Authentication & passwords

- Passwords are hashed with bcrypt (via `passlib`).
- New employee accounts get a short random password (`app/security.py`,
  `secrets.choice` over an unambiguous alphabet), shown exactly once to the
  admin who created the account, and the new user is forced to set their own
  password on first login.
- Login is rate-limited: 5 failed attempts per IP+email lock out further
  attempts for 15 minutes (`app/services/rate_limit.py`, in-memory — see
  "Known limitations" below).

### Access control

- Role-based access control with four roles (Admin, Management, Office,
  Driver) plus a per-area permission matrix for the Office role
  (`app/services/permissions.py`, `app/deps.py`).
- Every route that touches non-public data requires an authenticated session;
  unauthenticated requests are redirected to `/login`, not shown a 500 or a
  partial page.
- Denied access renders a readable error page that also tells the user which
  account they're currently logged in as — this was specifically added after
  user feedback that a bare `{"detail":"..."}` JSON response was confusing
  when someone had switched roles in another browser tab (sessions are
  per-browser, not per-tab).

### File uploads

- Uploaded files are always stored under a server-generated random filename
  (`uuid4().hex` + a checked extension) — **the original filename from the
  client is never used to build a filesystem path**, so path traversal via a
  crafted filename is not possible.
- Extensions are checked against an allow-list per upload type (images;
  images + PDF for documents; a small set of audio formats for voice
  messages).

### Known limitations

- **No independent security audit.** This is a self-review by the project
  maintainer(s), assisted by AI tooling. Treat it as a starting point, not a
  guarantee.
- **Single-process assumptions.** Login rate-limiting and the chat
  WebSocket broadcast are both in-memory and assume a single `uvicorn`
  worker process. Do not run with `--workers > 1` or behind a
  load-balanced multi-instance deployment without addressing this first
  (e.g. moving rate-limit state and chat broadcast to Redis).
- **No built-in HTTPS termination.** DispoHub expects to run behind a
  reverse proxy (nginx, Caddy, Traefik, etc.) that terminates TLS. Running
  it directly exposed to the internet over plain HTTP is not recommended.
- **No multi-factor authentication.**
- **Demo/seed accounts** use simple, publicly-documented passwords
  (`admin123`, `gf123`, etc.). They are gated behind `SEED_ON_STARTUP=true`
  and are meant for evaluation only — **disable seeding and remove/replace
  the seed accounts before using DispoHub with real company data.**
