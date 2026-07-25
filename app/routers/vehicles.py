from datetime import date

from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_area
from app.models import (
    Vehicle, VehicleStatus, CostEntry, User, Role,
    DamageReport, DamageStatus, Priority, Document,
    SafetyItem, Task, ParkingSpot,
)
from app.models.vehicle import VEHICLE_STATUS_LABELS
from app.services.uploads import save_upload
from app.templating import templates

router = APIRouter(prefix="/fahrzeuge")

require_fahrzeuge = require_area("fahrzeuge")


@router.get("", response_class=HTMLResponse)
def liste(request: Request, user=Depends(require_fahrzeuge), db: Session = Depends(get_db)):
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    return templates.TemplateResponse(
        "vehicles/list.html",
        {"request": request, "user": user, "active": "fahrzeuge", "fahrzeuge": fahrzeuge},
    )


@router.get("/{vehicle_id}", response_class=HTMLResponse)
def detail(vehicle_id: int, request: Request, user=Depends(require_fahrzeuge),
           db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")

    kosten_gesamt = (
        db.query(func.coalesce(func.sum(CostEntry.betrag), 0))
        .filter(CostEntry.vehicle_id == vehicle_id)
        .scalar()
    )
    monat_start = date.today().replace(day=1)
    kosten_monat = (
        db.query(func.coalesce(func.sum(CostEntry.betrag), 0))
        .filter(CostEntry.vehicle_id == vehicle_id, CostEntry.datum >= monat_start)
        .scalar()
    )
    fahrer = (db.query(User).filter(User.role == Role.fahrer, User.geloescht_am.is_(None))
              .order_by(User.name).all())
    haenger = db.query(Vehicle).filter(Vehicle.zugfahrzeug_id == vehicle_id).all()
    fotos = (
        db.query(Document)
        .filter(Document.vehicle_id == vehicle_id, Document.damage_id.is_(None))
        .order_by(Document.created_at.desc())
        .all()
    )
    adr_items = (
        db.query(SafetyItem)
        .filter(SafetyItem.vehicle_id == vehicle_id)
        .order_by(SafetyItem.ablauf_am.asc().nullslast())
        .all()
    )
    letzter_standort = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.vehicle_id == vehicle_id)
        .order_by(ParkingSpot.created_at.desc())
        .first()
    )
    return templates.TemplateResponse(
        "vehicles/detail.html",
        {
            "request": request, "user": user, "active": "fahrzeuge",
            "v": vehicle, "kosten_gesamt": kosten_gesamt, "kosten_monat": kosten_monat,
            "fahrer": fahrer, "haenger": haenger, "fotos": fotos, "adr_items": adr_items,
            "letzter_standort": letzter_standort,
            "status_optionen": [(s.value, label) for s, label in VEHICLE_STATUS_LABELS.items()],
        },
    )


@router.post("/{vehicle_id}/stammdaten")
def stammdaten_speichern(vehicle_id: int, user=Depends(require_fahrzeuge),
                         db: Session = Depends(get_db),
                         kennzeichen: str = Form(...), hersteller: str = Form(""),
                         modell: str = Form(""), km_stand: int = Form(0),
                         status: VehicleStatus = Form(VehicleStatus.einsatzbereit),
                         hu_faellig: str = Form(""), sp_faellig: str = Form(""),
                         uvv_faellig: str = Form(""), tacho_faellig: str = Form(""),
                         leasing_anbieter: str = Form(""), leasing_ende: str = Form(""),
                         monatliche_fixkosten: str = Form("")):
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")
    if not kennzeichen.strip():
        raise HTTPException(status_code=400, detail="Kennzeichen angeben")
    v.kennzeichen = kennzeichen.strip().upper()
    v.hersteller = hersteller.strip()
    v.modell = modell.strip()
    v.km_stand = max(0, km_stand)
    v.status = status
    v.hu_faellig = date.fromisoformat(hu_faellig) if hu_faellig else None
    v.sp_faellig = date.fromisoformat(sp_faellig) if sp_faellig else None
    v.uvv_faellig = date.fromisoformat(uvv_faellig) if uvv_faellig else None
    v.tacho_faellig = date.fromisoformat(tacho_faellig) if tacho_faellig else None
    v.leasing_anbieter = leasing_anbieter.strip() or None
    v.leasing_ende = date.fromisoformat(leasing_ende) if leasing_ende else None
    v.monatliche_fixkosten = (float(monatliche_fixkosten.replace(",", "."))
                              if monatliche_fixkosten.strip() else None)
    db.commit()
    return RedirectResponse(f"/fahrzeuge/{vehicle_id}", status_code=303)


@router.post("/{vehicle_id}/adr")
def adr_hinzufuegen(vehicle_id: int, user=Depends(require_fahrzeuge), db: Session = Depends(get_db),
                    bezeichnung: str = Form(...), ablauf_am: str = Form("")):
    if not db.get(Vehicle, vehicle_id):
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")
    db.add(SafetyItem(
        vehicle_id=vehicle_id, bezeichnung=bezeichnung.strip(),
        ablauf_am=(date.fromisoformat(ablauf_am) if ablauf_am else None),
    ))
    db.commit()
    return RedirectResponse(f"/fahrzeuge/{vehicle_id}", status_code=303)


@router.post("/{vehicle_id}/adr-checkliste")
def adr_checkliste_senden(vehicle_id: int, user=Depends(require_fahrzeuge), db: Session = Depends(get_db)):
    """Legt eine Aufgabe für den aktuellen Fahrer an, alle ADR-Mittel zu prüfen."""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")
    items = db.query(SafetyItem).filter(SafetyItem.vehicle_id == vehicle_id).all()
    if not items:
        return RedirectResponse(f"/fahrzeuge/{vehicle_id}", status_code=303)
    zeilen = [f"{i.bezeichnung}" + (f" (Ablauf {i.ablauf_am.strftime('%d.%m.%Y')})" if i.ablauf_am else "")
              for i in items]
    db.add(Task(
        titel=f"ADR-Ausrüstung prüfen — {vehicle.kennzeichen}",
        beschreibung="Bitte kontrollieren:\n" + "\n".join(zeilen),
        vehicle_id=vehicle_id,
        zugewiesen_user_id=vehicle.driver.id if vehicle.driver else None,
        erstellt_von_id=user.id,
    ))
    db.commit()
    return RedirectResponse(f"/fahrzeuge/{vehicle_id}", status_code=303)


@router.post("/{vehicle_id}/foto")
def foto_hochladen(vehicle_id: int, user=Depends(require_fahrzeuge), db: Session = Depends(get_db),
                   foto: UploadFile = File(...)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")
    doc = save_upload(foto)
    if doc:
        doc.vehicle_id = vehicle_id
        db.add(doc)
        db.commit()
    return RedirectResponse(f"/fahrzeuge/{vehicle_id}", status_code=303)


@router.post("/{vehicle_id}/fahrer")
def fahrer_zuweisen(vehicle_id: int, user=Depends(require_fahrzeuge), db: Session = Depends(get_db),
                    fahrer_id: str = Form("")):
    """Fahrzeugzuordnung ändern (Springer/Schichtwechsel) - vorheriger Fahrer wird frei."""
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")

    # Bisherigen Fahrer dieses Fahrzeugs lösen
    bisheriger = db.query(User).filter(User.vehicle_id == vehicle_id).first()
    if bisheriger:
        bisheriger.vehicle_id = None

    if fahrer_id.strip():
        neuer = db.get(User, int(fahrer_id))
        if neuer and neuer.role == Role.fahrer:
            neuer.vehicle_id = vehicle_id
    db.commit()
    return RedirectResponse(f"/fahrzeuge/{vehicle_id}", status_code=303)


# --- Schaden-Draufsicht (Sticky-Notes auf Fahrzeugsilhouette) --------------
@router.get("/{vehicle_id}/draufsicht", response_class=HTMLResponse)
def draufsicht(vehicle_id: int, request: Request, user=Depends(require_fahrzeuge),
               db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")
    pins = (
        db.query(DamageReport)
        .filter(DamageReport.vehicle_id == vehicle_id, DamageReport.position_x.isnot(None))
        .order_by(DamageReport.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "vehicles/draufsicht.html",
        {
            "request": request, "user": user, "active": "fahrzeuge",
            "v": vehicle, "pins": pins, "priorities": list(Priority),
        },
    )


@router.post("/{vehicle_id}/schaden-pin")
def schaden_pin(vehicle_id: int, request: Request, user=Depends(require_fahrzeuge),
                db: Session = Depends(get_db),
                beschreibung: str = Form(...), position_x: float = Form(...),
                position_y: float = Form(...), schadensdatum: date = Form(...),
                ort: str = Form(""), prioritaet: Priority = Form(Priority.normal),
                fotos: list[UploadFile] = File(default=[])):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")

    report = DamageReport(
        vehicle_id=vehicle_id, reporter_id=user.id,
        beschreibung=beschreibung.strip(), prioritaet=prioritaet, status=DamageStatus.gemeldet,
        schadensdatum=schadensdatum, ort=(ort.strip() or None),
        position_x=max(0.0, min(1.0, position_x)), position_y=max(0.0, min(1.0, position_y)),
    )
    for f in fotos or []:
        doc = save_upload(f)
        if doc:
            report.documents.append(doc)
    db.add(report)
    db.commit()
    return RedirectResponse(f"/fahrzeuge/{vehicle_id}/draufsicht", status_code=303)
