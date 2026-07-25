from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_area
from app.models import FuelCard, FuelTransaction, Vehicle
from app.services.fuel_import import import_csv, ImportResult
from app.templating import templates

router = APIRouter(prefix="/tankkarten")
require_tankkarten = require_area("tankkarten")

# Ergebnis des letzten Imports (pro Prozess, nur zur Anzeige nach Redirect)
_last_result: dict[int, ImportResult] = {}


@router.get("", response_class=HTMLResponse)
def index(request: Request, user=Depends(require_tankkarten), db: Session = Depends(get_db)):
    karten = db.query(FuelCard).order_by(FuelCard.kartennummer).all()
    letzte = (
        db.query(FuelTransaction)
        .order_by(FuelTransaction.datum.desc(), FuelTransaction.id.desc())
        .limit(20)
        .all()
    )
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    result = _last_result.pop(user.id, None)
    return templates.TemplateResponse(
        "fuelcards/index.html",
        {"request": request, "user": user, "active": "tankkarten",
         "karten": karten, "letzte": letzte, "fahrzeuge": fahrzeuge, "result": result},
    )


@router.post("/import")
async def import_datei(request: Request, user=Depends(require_tankkarten),
                       db: Session = Depends(get_db), datei: UploadFile = File(...)):
    if not datei.filename or not datei.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Bitte eine CSV-Datei hochladen.")
    content = await datei.read()
    _last_result[user.id] = import_csv(content, db)
    return RedirectResponse("/tankkarten", status_code=303)


@router.post("/karte")
def karte_anlegen(request: Request, user=Depends(require_tankkarten), db: Session = Depends(get_db),
                  kartennummer: str = Form(...), anbieter: str = Form(""),
                  vehicle_id: str = Form("")):
    nummer = kartennummer.strip().upper()
    if not nummer:
        raise HTTPException(status_code=400, detail="Kartennummer fehlt")
    if db.query(FuelCard).filter(FuelCard.kartennummer == nummer).first():
        raise HTTPException(status_code=400, detail="Karte existiert bereits")
    db.add(FuelCard(
        kartennummer=nummer, anbieter=anbieter.strip(),
        vehicle_id=int(vehicle_id) if vehicle_id.strip() else None,
    ))
    db.commit()
    return RedirectResponse("/tankkarten", status_code=303)


@router.get("/beispiel.csv", response_class=PlainTextResponse)
def beispiel_csv(user=Depends(require_tankkarten), db: Session = Depends(get_db)):
    """Beispieldatei mit den tatsächlich angelegten Kartennummern."""
    karten = db.query(FuelCard).limit(3).all()
    nummern = [k.kartennummer for k in karten] or ["DKV-1001", "DKV-1002", "DKV-1003"]
    zeilen = ["Datum;Kartennummer;Produkt;Menge;Betrag"]
    beispiele = [("01.07.2026", "Diesel", "62,40", "98,15"),
                 ("03.07.2026", "Diesel", "71,10", "112,04"),
                 ("05.07.2026", "AdBlue", "10,00", "9,90")]
    for i, (d, p, m, b) in enumerate(beispiele):
        zeilen.append(f"{d};{nummern[i % len(nummern)]};{p};{m};{b}")
    return PlainTextResponse(
        "\n".join(zeilen),
        headers={"Content-Disposition": 'attachment; filename="tankdaten_beispiel.csv"'},
    )
