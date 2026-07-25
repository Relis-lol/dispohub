from datetime import date

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_office
from app.models import (
    Vehicle, VehicleStatus, DamageReport, DamageStatus,
    Appointment, AppointmentStatus, CostEntry, Invoice, InvoiceStatus,
    Task, TaskStatus, SafetyItem, User,
)
from app.services.fristen import ampel, tage_bis_geburtstag
from app.templating import templates

router = APIRouter()


def dashboard_context(db: Session, user_current=None) -> dict:
    heute = date.today()
    monat_start = heute.replace(day=1)

    offene_schaeden = (
        db.query(DamageReport)
        .filter(DamageReport.status != DamageStatus.erledigt)
        .order_by(DamageReport.created_at.desc())
        .all()
    )
    neue_meldungen = [d for d in offene_schaeden if d.status == DamageStatus.gemeldet]

    fahrzeuge_reparatur = (
        db.query(Vehicle)
        .filter(Vehicle.status.in_([VehicleStatus.in_reparatur, VehicleStatus.werkstatt_geplant]),
                Vehicle.geloescht_am.is_(None))
        .all()
    )

    termine = (
        db.query(Appointment)
        .filter(Appointment.status == AppointmentStatus.offen)
        .order_by(Appointment.faellig_am.asc())
        .all()
    )
    heutige = [t for t in termine if t.faellig_am == heute]
    ueberfaellig = [t for t in termine if t.faellig_am < heute]
    bald = [t for t in termine if heute < t.faellig_am <= heute.fromordinal(heute.toordinal() + 30)]

    monatskosten = (
        db.query(func.coalesce(func.sum(CostEntry.betrag), 0))
        .filter(CostEntry.datum >= monat_start)
        .scalar()
    )

    leasing_auslaufend = (
        db.query(Vehicle)
        .filter(Vehicle.geloescht_am.is_(None))
        .filter(Vehicle.leasing_ende.isnot(None))
        .filter(Vehicle.leasing_ende <= heute.fromordinal(heute.toordinal() + 60))
        .order_by(Vehicle.leasing_ende.asc())
        .all()
    )

    from app.services.chat_service import unread_count
    ungelesene_nachrichten = unread_count(db, user_current) if user_current else 0

    neue_rechnungen = (
        db.query(Invoice).filter(Invoice.status == InvoiceStatus.eingegangen).count()
    )
    ungeklaerte_belege = (
        db.query(Invoice).filter(Invoice.status == InvoiceStatus.ungeklaert).count()
    )

    offene_aufgaben = db.query(Task).filter(Task.status == TaskStatus.offen).count()

    adr_faellig = sum(
        1 for i in db.query(SafetyItem).all() if ampel(i.ablauf_am) in ("rot", "gelb")
    )

    geburtstage_bald = [
        u for u in db.query(User).filter(User.geburtstag.isnot(None),
                                         User.geloescht_am.is_(None)).all()
        if (tage_bis_geburtstag(u.geburtstag) or 999) <= 14
    ]
    geburtstage_bald.sort(key=lambda u: tage_bis_geburtstag(u.geburtstag))

    return {
        "offene_aufgaben": offene_aufgaben,
        "adr_faellig": adr_faellig,
        "geburtstage_bald": geburtstage_bald,
        "ungelesene_nachrichten": ungelesene_nachrichten,
        "neue_rechnungen": neue_rechnungen,
        "ungeklaerte_belege": ungeklaerte_belege,
        "neue_meldungen": neue_meldungen,
        "offene_schaeden": offene_schaeden,
        "fahrzeuge_reparatur": fahrzeuge_reparatur,
        "termine_heute": heutige,
        "termine_bald": bald,
        "termine_ueberfaellig": ueberfaellig,
        "monatskosten": monatskosten,
        "leasing_auslaufend": leasing_auslaufend,
        "anzahl_fahrzeuge": db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None)).count(),
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(require_office), db: Session = Depends(get_db)):
    ctx = dashboard_context(db, user)
    ctx.update({"request": request, "user": user, "active": "dashboard"})
    return templates.TemplateResponse("dashboard.html", ctx)
