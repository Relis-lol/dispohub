"""Vordrucke: druckfertige Formulare (Arbeitszeitnachweis, Tankliste, Urlaub)."""
import calendar as pycal
from datetime import date, timedelta

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_area
from app.models import User, Role, Vehicle, LeaveRequest, LeaveStatus
from app.services.app_settings import get_setting, LOGO_PFAD
from app.templating import templates

router = APIRouter(prefix="/vordrucke")
require_mitarbeiter = require_area("mitarbeiter")

MONATSNAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
               "August", "September", "Oktober", "November", "Dezember"]


def _monat_tage(monat: str) -> tuple[str, list[date]]:
    """'YYYY-MM' -> (Anzeige-Label, Liste aller Tage des Monats)."""
    try:
        jahr, mon = (int(x) for x in monat.split("-"))
        erster = date(jahr, mon, 1)
    except (ValueError, TypeError):
        heute = date.today()
        jahr, mon = heute.year, heute.month
        erster = heute.replace(day=1)
    tage = [erster + timedelta(days=i) for i in range(pycal.monthrange(jahr, mon)[1])]
    return f"{MONATSNAMEN[mon - 1]} {jahr}", tage


@router.get("", response_class=HTMLResponse)
def uebersicht(request: Request, user=Depends(require_mitarbeiter), db: Session = Depends(get_db)):
    mitarbeiter = (db.query(User).filter(User.geloescht_am.is_(None))
                   .order_by(User.role, User.name).all())
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    genehmigte = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.status == LeaveStatus.genehmigt)
        .order_by(LeaveRequest.von.desc())
        .limit(30)
        .all()
    )
    return templates.TemplateResponse(
        "forms/index.html",
        {"request": request, "user": user, "active": "vordrucke",
         "mitarbeiter": mitarbeiter, "fahrzeuge": fahrzeuge, "genehmigte": genehmigte,
         "monat_default": date.today().strftime("%Y-%m")},
    )


@router.get("/arbeitszeit", response_class=HTMLResponse)
def arbeitszeit(request: Request, user=Depends(require_mitarbeiter), db: Session = Depends(get_db),
                mitarbeiter_id: int | None = None, monat: str = ""):
    m = db.get(User, mitarbeiter_id) if mitarbeiter_id else None
    label, tage = _monat_tage(monat)
    return templates.TemplateResponse(
        "forms/arbeitszeit.html",
        {"request": request, "user": user, "m": m, "monat_label": label, "tage": tage,
         "logo": get_setting(db, LOGO_PFAD)},
    )


@router.get("/tankliste", response_class=HTMLResponse)
def tankliste(request: Request, user=Depends(require_mitarbeiter), db: Session = Depends(get_db),
              vehicle_id: int | None = None, monat: str = ""):
    v = db.get(Vehicle, vehicle_id) if vehicle_id else None
    label, tage = _monat_tage(monat)
    return templates.TemplateResponse(
        "forms/tankliste.html",
        {"request": request, "user": user, "v": v, "monat_label": label, "tage": tage,
         "logo": get_setting(db, LOGO_PFAD)},
    )


@router.get("/urlaubsantrag", response_class=HTMLResponse)
def urlaubsantrag(request: Request, user=Depends(require_mitarbeiter),
                  db: Session = Depends(get_db), mitarbeiter_id: int | None = None):
    m = db.get(User, mitarbeiter_id) if mitarbeiter_id else None
    return templates.TemplateResponse(
        "forms/urlaubsantrag.html",
        {"request": request, "user": user, "m": m, "logo": get_setting(db, LOGO_PFAD)},
    )


@router.get("/urlaubsbestaetigung/{antrag_id}", response_class=HTMLResponse)
def urlaubsbestaetigung(antrag_id: int, request: Request, user=Depends(require_mitarbeiter),
                        db: Session = Depends(get_db)):
    antrag = db.get(LeaveRequest, antrag_id)
    if not antrag or antrag.status != LeaveStatus.genehmigt:
        raise HTTPException(status_code=404, detail="Kein genehmigter Antrag")
    return templates.TemplateResponse(
        "forms/urlaubsbestaetigung.html",
        {"request": request, "user": user, "antrag": antrag,
         "logo": get_setting(db, LOGO_PFAD), "heute": date.today()},
    )
