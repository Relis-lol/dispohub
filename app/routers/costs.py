from datetime import date

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_area
from app.models import CostEntry, Vehicle
from app.models.cost import CATEGORY_LABELS
from app.templating import templates

router = APIRouter(prefix="/kosten")
require_kosten = require_area("kosten")


@router.get("", response_class=HTMLResponse)
def uebersicht(request: Request, user=Depends(require_kosten), db: Session = Depends(get_db)):
    monat_start = date.today().replace(day=1)

    # Kosten je Kategorie (aktueller Monat)
    je_kategorie = (
        db.query(CostEntry.kategorie, func.coalesce(func.sum(CostEntry.betrag), 0))
        .filter(CostEntry.datum >= monat_start)
        .group_by(CostEntry.kategorie)
        .all()
    )
    je_kategorie = sorted(
        [(CATEGORY_LABELS.get(k, k.value), float(s)) for k, s in je_kategorie],
        key=lambda x: -x[1],
    )

    # Kosten je Fahrzeug (aktueller Monat)
    je_fahrzeug = (
        db.query(Vehicle, func.coalesce(func.sum(CostEntry.betrag), 0))
        .outerjoin(CostEntry, (CostEntry.vehicle_id == Vehicle.id) & (CostEntry.datum >= monat_start))
        .group_by(Vehicle.id)
        .all()
    )
    je_fahrzeug = sorted([(v, float(s)) for v, s in je_fahrzeug], key=lambda x: -x[1])

    gesamt_monat = sum(s for _, s in je_kategorie)

    letzte = (
        db.query(CostEntry).order_by(CostEntry.datum.desc(), CostEntry.id.desc()).limit(20).all()
    )

    return templates.TemplateResponse(
        "costs/list.html",
        {
            "request": request, "user": user, "active": "kosten",
            "je_kategorie": je_kategorie, "je_fahrzeug": je_fahrzeug,
            "gesamt_monat": gesamt_monat, "letzte": letzte,
        },
    )
