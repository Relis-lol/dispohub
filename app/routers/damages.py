from datetime import date, datetime

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user, require_area
from app.models import (
    User, Role, Vehicle, VehicleStatus,
    DamageReport, DamageStatus, Priority,
    Appointment, AppointmentSource,
    CostEntry, CostCategory, Document,
)
from app.services.uploads import save_upload
from app.templating import templates

router = APIRouter()
require_schaeden = require_area("schaeden")


def _detail_response(request: Request, db: Session, user: User, report: DamageReport):
    """HTMX → nur den Vorgangs-Block liefern, sonst volle Detailseite."""
    ctx = {"request": request, "user": user, "d": report, "active": "schaeden"}
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("damages/_vorgang.html", ctx)
    return templates.TemplateResponse("damages/detail.html", ctx)


# ---------------------------------------------------------------------------
# Fahreransicht (mobil): Schaden melden
# ---------------------------------------------------------------------------
@router.get("/melden", response_class=HTMLResponse)
def melden_form(request: Request, user: User = Depends(require_user),
                db: Session = Depends(get_db), ok: int | None = None,
                parkplatz: int | None = None, urlaub: int | None = None):
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    meine = (
        db.query(DamageReport)
        .filter(DamageReport.reporter_id == user.id)
        .order_by(DamageReport.created_at.desc())
        .limit(10)
        .all()
    )
    # Offene Schäden am aktuellen Fahrzeug, egal wer sie gemeldet hat — damit
    # z.B. ein Nachtfahrer sieht "das wurde schon gemeldet", bevor er es erneut tut.
    am_fahrzeug = []
    if user.vehicle_id:
        am_fahrzeug = (
            db.query(DamageReport)
            .filter(DamageReport.vehicle_id == user.vehicle_id,
                    DamageReport.status != DamageStatus.erledigt)
            .order_by(DamageReport.created_at.desc())
            .all()
        )
    from app.models import LeaveRequest
    meine_antraege = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.user_id == user.id)
        .order_by(LeaveRequest.created_at.desc())
        .limit(5)
        .all()
    )
    return templates.TemplateResponse(
        "damages/report.html",
        {
            "request": request, "user": user, "fahrzeuge": fahrzeuge, "active": "melden",
            "meine": meine, "am_fahrzeug": am_fahrzeug, "priorities": list(Priority), "ok": ok,
            "parkplatz_ok": parkplatz, "mein_fahrzeug_id": user.vehicle_id,
            "urlaub_ok": urlaub, "meine_antraege": meine_antraege,
        },
    )


@router.post("/melden")
def melden(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db),
           vehicle_id: int = Form(...), beschreibung: str = Form(...),
           prioritaet: Priority = Form(Priority.normal),
           nachricht: str = Form(""), fotos: list[UploadFile] = File(default=[])):
    if not db.get(Vehicle, vehicle_id):
        raise HTTPException(status_code=400, detail="Unbekanntes Fahrzeug")

    report = DamageReport(
        vehicle_id=vehicle_id, reporter_id=user.id,
        beschreibung=beschreibung.strip(), prioritaet=prioritaet,
        nachricht_an_gf=(nachricht.strip() or None),
        status=DamageStatus.gemeldet,
    )
    for f in fotos or []:
        doc = save_upload(f)
        if doc:
            report.documents.append(doc)
    db.add(report)
    db.commit()
    return RedirectResponse("/melden?ok=1", status_code=303)


# ---------------------------------------------------------------------------
# Büro/GF: Posteingang + Vorgangsbearbeitung
# ---------------------------------------------------------------------------
@router.get("/schaeden", response_class=HTMLResponse)
def posteingang(request: Request, user=Depends(require_schaeden), db: Session = Depends(get_db)):
    offen = (
        db.query(DamageReport)
        .filter(DamageReport.status != DamageStatus.erledigt)
        .order_by(DamageReport.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "damages/inbox.html",
        {"request": request, "user": user, "active": "schaeden", "schaeden": offen},
    )


@router.get("/schaeden/{report_id}", response_class=HTMLResponse)
def schaden_detail(report_id: int, request: Request, user=Depends(require_schaeden),
                   db: Session = Depends(get_db)):
    report = db.get(DamageReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Schaden nicht gefunden")
    return templates.TemplateResponse(
        "damages/detail.html",
        {"request": request, "user": user, "d": report, "active": "schaeden"},
    )


@router.post("/schaeden/{report_id}/uebernehmen")
def uebernehmen(report_id: int, request: Request, user=Depends(require_schaeden),
                db: Session = Depends(get_db)):
    report = db.get(DamageReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Schaden nicht gefunden")
    if report.status == DamageStatus.gemeldet:
        report.status = DamageStatus.uebernommen
        # Fahrzeug in "Werkstatt geplant" setzen, wenn noch einsatzbereit
        if report.vehicle and report.vehicle.status == VehicleStatus.einsatzbereit:
            report.vehicle.status = VehicleStatus.werkstatt_geplant
        db.commit()
        db.refresh(report)
    return _detail_response(request, db, user, report)


@router.post("/schaeden/{report_id}/termin")
def termin_anlegen(report_id: int, request: Request, user=Depends(require_schaeden),
                   db: Session = Depends(get_db),
                   titel: str = Form(...), faellig_am: date = Form(...)):
    report = db.get(DamageReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Schaden nicht gefunden")
    appt = Appointment(
        vehicle_id=report.vehicle_id, damage_id=report.id,
        titel=titel.strip(), quelle=AppointmentSource.schaden, faellig_am=faellig_am,
    )
    db.add(appt)
    if report.status == DamageStatus.gemeldet:
        report.status = DamageStatus.uebernommen
    db.commit()
    db.refresh(report)
    return _detail_response(request, db, user, report)


@router.post("/schaeden/{report_id}/kosten")
def kosten_ergaenzen(report_id: int, request: Request, user=Depends(require_schaeden),
                     db: Session = Depends(get_db),
                     betrag: float = Form(...), beschreibung: str = Form(""),
                     kategorie: CostCategory = Form(CostCategory.reparatur)):
    report = db.get(DamageReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Schaden nicht gefunden")
    cost = CostEntry(
        vehicle_id=report.vehicle_id, damage_id=report.id,
        kategorie=kategorie, betrag=betrag, datum=date.today(),
        beschreibung=(beschreibung.strip() or "Reparaturkosten"),
    )
    db.add(cost)
    report.status = DamageStatus.in_reparatur
    if report.vehicle:
        report.vehicle.status = VehicleStatus.in_reparatur
    db.commit()
    db.refresh(report)
    return _detail_response(request, db, user, report)


@router.post("/schaeden/{report_id}/erledigt")
def erledigt(report_id: int, request: Request, user=Depends(require_schaeden),
             db: Session = Depends(get_db)):
    report = db.get(DamageReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Schaden nicht gefunden")
    report.status = DamageStatus.erledigt
    if report.vehicle:
        report.vehicle.status = VehicleStatus.einsatzbereit
    db.commit()
    db.refresh(report)
    return _detail_response(request, db, user, report)
