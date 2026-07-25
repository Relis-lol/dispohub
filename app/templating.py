import os
from datetime import date, datetime, timezone

from fastapi.templating import Jinja2Templates

from app.services.fristen import ampel, ampel_tone, tage_bis, tage_bis_geburtstag
from app.services.i18n import i18n_context
from app.models.damage import PRIORITY_LABELS

templates = Jinja2Templates(directory="app/templates", context_processors=[i18n_context])

# Hilfsfunktionen in allen Templates verfügbar machen
templates.env.globals["ampel"] = ampel
templates.env.globals["ampel_tone"] = ampel_tone
templates.env.globals["tage_bis"] = tage_bis
templates.env.globals["tage_bis_geburtstag"] = tage_bis_geburtstag
templates.env.globals["today"] = date.today
templates.env.globals["priority_labels"] = {p.value: label for p, label in PRIORITY_LABELS.items()}
templates.env.globals["loeschen_fenster_sek"] = 120

# Cache-Busting fürs CSS: Browser sollen nach jeder Änderung neu laden, nicht die
# alte gecachte Version behalten (sonst wirken Layout-Fixes lokal "nicht angekommen").
_css_path = os.path.join("app", "static", "css", "app.css")
templates.env.globals["asset_version"] = (
    str(int(os.path.getmtime(_css_path))) if os.path.exists(_css_path) else "1"
)


def nav_chat_unread(user) -> int:
    """Ungelesene Chat-Nachrichten für die Navigations-Badge."""
    if not user:
        return 0
    from app.db import SessionLocal
    from app.services.chat_service import unread_count
    db = SessionLocal()
    try:
        return unread_count(db, user)
    finally:
        db.close()


templates.env.globals["nav_chat_unread"] = nav_chat_unread


def nav_open_tasks(user) -> int:
    """Anzahl offener Aufgaben für die Fahrer-Tab-Badge."""
    if not user:
        return 0
    from app.db import SessionLocal
    from app.services.task_service import tasks_for_driver
    db = SessionLocal()
    try:
        return len(tasks_for_driver(db, user))
    finally:
        db.close()


templates.env.globals["nav_open_tasks"] = nav_open_tasks


def branding():
    """Firmenlogo + Website für die Seitenleiste (leer = Standard-Schriftzug)."""
    from app.db import SessionLocal
    from app.services.app_settings import get_setting, LOGO_PFAD, FIRMEN_WEBSITE
    db = SessionLocal()
    try:
        return {"logo": get_setting(db, LOGO_PFAD), "website": get_setting(db, FIRMEN_WEBSITE)}
    finally:
        db.close()


templates.env.globals["branding"] = branding


def to_local(value: datetime | None) -> datetime | None:
    """DB-Zeitstempel sind UTC-naiv (SQLite CURRENT_TIMESTAMP) - für Anzeige in lokale Zeit wandeln."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone()


def chatzeit(value: datetime | None) -> str:
    local = to_local(value)
    return local.strftime("%H:%M") if local else ""


def datumzeit(value: datetime | None) -> str:
    local = to_local(value)
    return local.strftime("%d.%m.%Y %H:%M") if local else "–"


templates.env.filters["chatzeit"] = chatzeit
templates.env.filters["datumzeit"] = datumzeit


def euro(value) -> str:
    if value is None:
        return "–"
    return f"{float(value):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def datum(value: date | None) -> str:
    if value is None:
        return "–"
    return value.strftime("%d.%m.%Y")


templates.env.filters["euro"] = euro
templates.env.filters["datum"] = datum
