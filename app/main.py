import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.services.csrf import CSRFMiddleware

from app.config import settings
from app.db import Base, engine
from app.deps import RedirectToLogin, get_current_user
from app.templating import templates
from app.routers import auth, dashboard, vehicles, drivers, damages, calendar, costs, invoices, chat, fuelcards, admin, tasks, notes, parking, verwaltung, leave, polls, forms, contacts

# Modelle importieren, damit die Tabellen bei create_all() bekannt sind.
import app.models  # noqa: F401

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.secret_key_ist_unsicher:
        logging.getLogger("dispohub").warning(
            "SECRET_KEY ist noch der Standardwert aus .env.example — vor echtem "
            "Betrieb unbedingt einen eigenen zufälligen Wert setzen (Sessions sind "
            "sonst fälschbar)."
        )
    # Dev-Komfort: Tabellen anlegen, falls sie fehlen (in Prod übernimmt Alembic).
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        from app.services.seed import seed_if_empty
        seed_if_empty()
    # Papierkorb: abgelaufene Einträge (älter als 30 Tage) endgültig entfernen
    from app.db import SessionLocal
    from app.services.papierkorb import purge_abgelaufene
    _db = SessionLocal()
    try:
        purge_abgelaufene(_db)
    finally:
        _db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware, secret_key=settings.secret_key, max_age=60 * 60 * 12,
    same_site="lax", https_only=settings.session_cookie_secure,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(RedirectToLogin)
async def redirect_to_login(request: Request, exc: RedirectToLogin):
    return RedirectResponse("/login", status_code=303)


@app.get("/health", include_in_schema=False)
def health():
    """Unauthenticated liveness check for container orchestration (Docker
    healthcheck, load balancers, uptime monitors) — deliberately does not
    touch the database, so it reflects only "is the process up"."""
    return {"status": "ok"}


_FEHLER_TEXTE = {
    403: ("🚫", "error.403_title", "error.403_text"),
    404: ("🔍", "error.404_title", "error.404_text"),
}


@app.exception_handler(StarletteHTTPException)
async def html_fehlerseite(request: Request, exc: StarletteHTTPException):
    """Zeigt bei normalen Seitenaufrufen eine verständliche Fehlerseite statt
    rohem JSON — betrifft v.a. 403 (fehlende Berechtigung) und 404."""
    akzeptiert_html = "text/html" in request.headers.get("accept", "")
    if not akzeptiert_html or exc.status_code not in _FEHLER_TEXTE:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    icon, titel_key, text_key = _FEHLER_TEXTE[exc.status_code]
    user = get_current_user(request, next(_get_db_for_error()))
    custom_text = exc.detail if isinstance(exc.detail, str) and exc.detail != "Not Found" else None
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request, "icon": icon, "titel_key": titel_key,
            "text_key": text_key, "custom_text": custom_text,
            "angemeldet_als": user.name if user else None,
            "user_role": user.role.value if user else None,
        },
        status_code=exc.status_code,
    )


def _get_db_for_error():
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse("app/static/manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse("app/static/js/sw.js", media_type="application/javascript")


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(calendar.router)
app.include_router(costs.router)
app.include_router(damages.router)
app.include_router(invoices.router)
app.include_router(invoices.export_router)
app.include_router(chat.router)
app.include_router(fuelcards.router)
app.include_router(admin.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(parking.router)
app.include_router(verwaltung.router)
app.include_router(leave.router)
app.include_router(polls.router)
app.include_router(forms.router)
app.include_router(contacts.router)
