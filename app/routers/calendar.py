import calendar as pycal
from datetime import date, timedelta

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_area
from app.models import (
    Appointment, AppointmentSource, AppointmentStatus, Vehicle, User, Role,
    PersonnelEntry, EntryArt,
)
from app.models.appointment import SOURCE_LABELS
from app.templating import templates

router = APIRouter(prefix="/kalender")
require_kalender = require_area("kalender")

MONATSNAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
               "August", "September", "Oktober", "November", "Dezember"]


@router.get("", response_class=HTMLResponse)
def kalender(request: Request, user=Depends(require_kalender), db: Session = Depends(get_db),
             monat: str = ""):
    heute = date.today()
    try:
        jahr, mon = (int(x) for x in monat.split("-"))
        date(jahr, mon, 1)
    except (ValueError, TypeError):
        jahr, mon = heute.year, heute.month

    erster = date(jahr, mon, 1)
    letzter = date(jahr, mon, pycal.monthrange(jahr, mon)[1])
    tage = [erster + timedelta(days=i) for i in range(letzter.day)]
    vormonat = (erster - timedelta(days=1)).replace(day=1)
    naechster = (letzter + timedelta(days=1))

    # --- Fahrzeug-Zeilen: offene Termine im Monat je Fahrzeug ---------------
    termine_monat = (
        db.query(Appointment)
        .filter(Appointment.status == AppointmentStatus.offen,
                Appointment.faellig_am >= erster, Appointment.faellig_am <= letzter)
        .all()
    )
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    fz_zellen: dict[int, dict[int, list]] = {v.id: {} for v in fahrzeuge}
    allgemein: dict[int, list] = {}
    for t in termine_monat:
        ziel = fz_zellen.get(t.vehicle_id) if t.vehicle_id else None
        if ziel is None:
            ziel = allgemein
        ziel.setdefault(t.faellig_am.day, []).append(t)

    # --- Fahrer-Zeilen: Urlaub/Krankheit aus der Personalakte ---------------
    fahrer = (db.query(User).filter(User.role == Role.fahrer, User.geloescht_am.is_(None))
              .order_by(User.name).all())
    fahrer_zellen: dict[int, dict[int, str]] = {f.id: {} for f in fahrer}
    eintraege = (
        db.query(PersonnelEntry)
        .filter(PersonnelEntry.art.in_([EntryArt.urlaub, EntryArt.krank]))
        .all()
    )
    for e in eintraege:
        if e.user_id not in fahrer_zellen:
            continue
        ende = e.bis or e.datum
        if ende < erster or e.datum > letzter:
            continue
        d = max(e.datum, erster)
        while d <= min(ende, letzter):
            fahrer_zellen[e.user_id][d.day] = e.art.value
            d += timedelta(days=1)

    # --- Offene Termine als Liste darunter (bewährte Ansicht) ---------------
    termine = (
        db.query(Appointment)
        .filter(Appointment.status == AppointmentStatus.offen)
        .order_by(Appointment.faellig_am.asc())
        .all()
    )

    return templates.TemplateResponse(
        "calendar/list.html",
        {
            "request": request, "user": user, "active": "kalender",
            "termine": termine, "tage": tage, "heute": heute,
            "monat_label": f"{MONATSNAMEN[mon - 1]} {jahr}",
            "vormonat": vormonat.strftime("%Y-%m"), "naechster": naechster.strftime("%Y-%m"),
            "fahrzeuge": fahrzeuge, "fz_zellen": fz_zellen, "allgemein": allgemein,
            "fahrer": fahrer, "fahrer_zellen": fahrer_zellen,
            "quellen": [(q.value, label) for q, label in SOURCE_LABELS.items()],
            "monat_param": erster.strftime("%Y-%m"),
        },
    )


@router.post("/termin")
def termin_anlegen(user=Depends(require_kalender), db: Session = Depends(get_db),
                   titel: str = Form(...), faellig_am: date = Form(...),
                   vehicle_id: str = Form(""), quelle: AppointmentSource = Form(AppointmentSource.allgemein)):
    if not titel.strip():
        raise HTTPException(status_code=400, detail="Titel angeben")
    db.add(Appointment(
        titel=titel.strip(), faellig_am=faellig_am, quelle=quelle,
        vehicle_id=(int(vehicle_id) if vehicle_id.strip() else None),
    ))
    db.commit()
    return RedirectResponse(f"/kalender?monat={faellig_am.strftime('%Y-%m')}", status_code=303)


@router.post("/termin/{termin_id}/erledigt")
def termin_erledigt(termin_id: int, user=Depends(require_kalender), db: Session = Depends(get_db),
                    monat: str = Form("")):
    termin = db.get(Appointment, termin_id)
    if not termin:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")
    termin.status = AppointmentStatus.erledigt
    db.commit()
    return RedirectResponse(f"/kalender?monat={monat}" if monat else "/kalender", status_code=303)
