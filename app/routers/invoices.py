import csv
import io
import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_area
from app.models import Invoice, InvoiceStatus, Vehicle, CostEntry, CostCategory, Receipt
from app.models.cost import CATEGORY_LABELS
from app.services.mail_rules import vorsortieren
from app.services.uploads import save_receipt
from app.templating import templates

router = APIRouter(prefix="/rechnungen")
require_rechnungen = require_area("rechnungen")


# --- Prüf-Inbox -------------------------------------------------------------
@router.get("", response_class=HTMLResponse)
def inbox(request: Request, user=Depends(require_rechnungen), db: Session = Depends(get_db)):
    offen = (
        db.query(Invoice)
        .filter(Invoice.status != InvoiceStatus.geprueft)
        .order_by(Invoice.eingegangen_am.desc())
        .all()
    )
    geprueft = (
        db.query(Invoice)
        .filter(Invoice.status == InvoiceStatus.geprueft)
        .order_by(Invoice.rechnungsdatum.desc())
        .limit(15)
        .all()
    )
    from app.services.mail_ingest import ist_konfiguriert
    return templates.TemplateResponse(
        "invoices/inbox.html",
        {"request": request, "user": user, "active": "rechnungen",
         "offen": offen, "geprueft": geprueft, "imap_konfiguriert": ist_konfiguriert()},
    )


@router.post("/abrufen")
def echten_eingang_abrufen(user=Depends(require_rechnungen), db: Session = Depends(get_db)):
    """Holt neue Rechnungen aus dem echten Belege-Postfach (nur aktiv, wenn
    IMAP_HOST/IMAP_USER/IMAP_PASSWORD in .env gesetzt sind, siehe mail_ingest.py)."""
    from app.services.mail_ingest import neue_rechnungen_abholen
    neue_rechnungen_abholen(db)
    return RedirectResponse("/rechnungen", status_code=303)


@router.get("/{invoice_id}", response_class=HTMLResponse)
def detail(invoice_id: int, request: Request, user=Depends(require_rechnungen),
           db: Session = Depends(get_db)):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    kategorien = [(c.value, CATEGORY_LABELS[c]) for c in CostCategory]
    return templates.TemplateResponse(
        "invoices/detail.html",
        {"request": request, "user": user, "active": "rechnungen",
         "inv": inv, "fahrzeuge": fahrzeuge, "kategorien": kategorien},
    )


@router.post("/{invoice_id}/bestaetigen")
def bestaetigen(invoice_id: int, request: Request, user=Depends(require_rechnungen),
                db: Session = Depends(get_db),
                kategorie: CostCategory = Form(...), vehicle_id: str = Form(""),
                betrag: float = Form(...)):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    vid = int(vehicle_id) if vehicle_id.strip() else None
    inv.kategorie = kategorie
    inv.vehicle_id = vid
    inv.betrag = betrag
    inv.status = InvoiceStatus.geprueft

    # Kostenbuchung anlegen (integriert sich in Kosten-/Dashboard-Übersicht)
    cost = CostEntry(
        vehicle_id=vid, kategorie=kategorie, betrag=betrag,
        datum=inv.rechnungsdatum or date.today(),
        beschreibung=f"{inv.absender}: {inv.betreff}"[:250],
    )
    db.add(cost)
    db.flush()
    inv.cost_id = cost.id
    db.commit()
    return RedirectResponse("/rechnungen", status_code=303)


# --- Simulierter E-Mail-Eingang (Demo) --------------------------------------
_DEMO_MAILS = [
    ("rechnung@kfz-schneider.de", "Rechnung Reparatur B-TR 0788", "R-2026-4471", 512.40),
    ("buchhaltung@aral-tankkarte.de", "Tankabrechnung Juli 2026", "AR-778123", 1043.75),
    ("service@dekra.de", "Rechnung HU/AU Prüfung", "DK-99120", 128.00),
    ("info@reifen-mueller.de", "Rechnung Reifenwechsel B-TR 2233", "RM-5567", 684.20),
    ("kontakt@alphalease.de", "Leasingrate August B-TR 1450", "AL-0825-1450", 740.00),
    ("beleg@huk-versicherung.de", "Beitragsrechnung KFZ", "HUK-2026-0091", 98.00),
]


@router.post("/simulieren")
def simulieren(request: Request, user=Depends(require_rechnungen), db: Session = Depends(get_db)):
    absender, betreff, rnr, betrag = random.choice(_DEMO_MAILS)
    inv = Invoice(
        absender=absender, betreff=betreff, rechnungsnummer=rnr, betrag=betrag,
        rechnungsdatum=date.today() - timedelta(days=random.randint(0, 5)),
        eingegangen_am=datetime.now(), status=InvoiceStatus.eingegangen,
    )
    db.add(inv)
    db.flush()
    vorsortieren(inv, db)
    db.commit()
    return RedirectResponse("/rechnungen", status_code=303)


# --- Steuerberater-Export ---------------------------------------------------
export_router = APIRouter(prefix="/export")
require_export = require_area("export")


@export_router.get("", response_class=HTMLResponse)
def export_index(request: Request, user=Depends(require_export), db: Session = Depends(get_db)):
    monat_start = date.today().replace(day=1)
    geprueft = (
        db.query(Invoice)
        .filter(Invoice.status == InvoiceStatus.geprueft, Invoice.rechnungsdatum >= monat_start)
        .order_by(Invoice.rechnungsdatum.asc())
        .all()
    )
    ungeklaert = (
        db.query(Invoice).filter(Invoice.status != InvoiceStatus.geprueft).all()
    )
    summe = sum(float(i.betrag or 0) for i in geprueft)
    belege_offen = (
        db.query(Receipt).filter(Receipt.abgeholt.is_(False))
        .order_by(Receipt.created_at.desc()).all()
    )
    belege_abgeholt = (
        db.query(Receipt).filter(Receipt.abgeholt.is_(True))
        .order_by(Receipt.created_at.desc()).limit(20).all()
    )
    return templates.TemplateResponse(
        "export/index.html",
        {"request": request, "user": user, "active": "export",
         "geprueft": geprueft, "ungeklaert": ungeklaert, "summe": summe,
         "monat": date.today().strftime("%m/%Y"),
         "belege_offen": belege_offen, "belege_abgeholt": belege_abgeholt},
    )


@export_router.post("/beleg")
def beleg_hochladen(user=Depends(require_export), db: Session = Depends(get_db),
                    datei: UploadFile = File(...), notiz: str = Form("")):
    beleg = save_receipt(datei, hochgeladen_von_id=user.id, notiz=(notiz.strip() or None))
    if beleg:
        db.add(beleg)
        db.commit()
    return RedirectResponse("/export", status_code=303)


@export_router.post("/beleg/{beleg_id}/abgeholt")
def beleg_abgeholt(beleg_id: int, user=Depends(require_export), db: Session = Depends(get_db)):
    beleg = db.get(Receipt, beleg_id)
    if not beleg:
        raise HTTPException(status_code=404, detail="Beleg nicht gefunden")
    beleg.abgeholt = True
    db.commit()
    return RedirectResponse("/export", status_code=303)


@export_router.post("/beleg/{beleg_id}/loeschen")
def beleg_loeschen(beleg_id: int, user=Depends(require_export), db: Session = Depends(get_db)):
    beleg = db.get(Receipt, beleg_id)
    if not beleg:
        raise HTTPException(status_code=404, detail="Beleg nicht gefunden")
    db.delete(beleg)
    db.commit()
    return RedirectResponse("/export", status_code=303)


@export_router.get("/pdf")
def export_pdf(user=Depends(require_export), db: Session = Depends(get_db)):
    from app.services.pdf_report import build_monthly_pdf
    pdf_bytes = build_monthly_pdf(db)
    fname = f"monatsbericht_{date.today().strftime('%Y_%m')}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@export_router.get("/csv")
def export_csv(user=Depends(require_export), db: Session = Depends(get_db)):
    monat_start = date.today().replace(day=1)
    rows = (
        db.query(Invoice)
        .filter(Invoice.status == InvoiceStatus.geprueft, Invoice.rechnungsdatum >= monat_start)
        .order_by(Invoice.rechnungsdatum.asc())
        .all()
    )
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Datum", "Rechnungsnummer", "Absender", "Kategorie", "Fahrzeug", "Betrag_EUR"])
    for i in rows:
        w.writerow([
            i.rechnungsdatum.strftime("%d.%m.%Y") if i.rechnungsdatum else "",
            i.rechnungsnummer or "",
            i.absender,
            CATEGORY_LABELS.get(i.kategorie, "") if i.kategorie else "",
            i.vehicle.kennzeichen if i.vehicle else "Allgemein",
            f"{float(i.betrag or 0):.2f}".replace(".", ","),
        ])
    buf.seek(0)
    fname = f"steuerexport_{date.today().strftime('%Y_%m')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
