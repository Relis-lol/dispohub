"""Admin-Menü: Fahrzeuge & Mitarbeiter im UI anlegen/entfernen (30-Tage-Papierkorb)."""
from datetime import date, datetime

from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_gf_or_admin
from app.models import User, Role, UserStatus, Vehicle, VehicleTyp, VehicleStatus
from app.security import hash_password, generiere_passwort
from app.services import backup, papierkorb
from app.services.app_settings import get_setting, set_setting, LOGO_PFAD, FIRMEN_WEBSITE
from app.services.uploads import save_upload
from app.templating import templates

router = APIRouter(prefix="/verwaltung")


@router.get("", response_class=HTMLResponse)
def uebersicht(request: Request, user=Depends(require_gf_or_admin), db: Session = Depends(get_db)):
    papierkorb.purge_abgelaufene(db)
    mitarbeiter = (db.query(User).filter(User.geloescht_am.is_(None))
                   .order_by(User.role, User.name).all())
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    korb_users = (db.query(User).filter(User.geloescht_am.isnot(None))
                  .order_by(User.geloescht_am.desc()).all())
    korb_vehicles = (db.query(Vehicle).filter(Vehicle.geloescht_am.isnot(None))
                     .order_by(Vehicle.geloescht_am.desc()).all())
    return templates.TemplateResponse(
        "settings/verwaltung.html",
        {
            "request": request, "user": user, "active": "verwaltung",
            "mitarbeiter": mitarbeiter, "fahrzeuge": fahrzeuge,
            "korb_users": korb_users, "korb_vehicles": korb_vehicles,
            "rollen": [r.value for r in Role],
            "typen": [t.value for t in VehicleTyp],
            "tage_verbleibend": papierkorb.tage_verbleibend,
            "aufbewahrung": papierkorb.AUFBEWAHRUNG_TAGE,
            "logo_pfad": get_setting(db, LOGO_PFAD),
            "firmen_website": get_setting(db, FIRMEN_WEBSITE),
            "backup_verfuegbar": backup.ist_sqlite(),
        },
    )


@router.post("/branding")
def branding_speichern(user=Depends(require_gf_or_admin), db: Session = Depends(get_db),
                       logo: UploadFile = File(None), firmen_website: str = Form(""),
                       logo_entfernen: str = Form("")):
    if logo_entfernen:
        set_setting(db, LOGO_PFAD, None)
    else:
        doc = save_upload(logo)
        if doc:
            db.add(doc)
            set_setting(db, LOGO_PFAD, doc.pfad)
    website = firmen_website.strip()
    if website and not website.startswith(("http://", "https://")):
        website = "https://" + website
    set_setting(db, FIRMEN_WEBSITE, website or None)
    return RedirectResponse("/verwaltung", status_code=303)


@router.post("/mitarbeiter")
def mitarbeiter_anlegen(request: Request, user=Depends(require_gf_or_admin), db: Session = Depends(get_db),
                        name: str = Form(...), email: str = Form(...),
                        rolle: Role = Form(Role.fahrer), telefon: str = Form("")):
    email = email.strip().lower()
    if not name.strip() or not email:
        raise HTTPException(status_code=400, detail="Name und E-Mail angeben")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="E-Mail-Adresse ist bereits vergeben")
    # Zufälliges Start-Passwort statt manueller Eingabe: kein schwaches
    # "123456" möglich, wird dem Mitarbeiter einmalig hier angezeigt und muss
    # beim ersten Login geändert werden.
    passwort = generiere_passwort()
    neu = User(
        name=name.strip(), email=email, role=rolle,
        phone=(telefon.strip() or None), status=UserStatus.aktiv,
        password_hash=hash_password(passwort), passwort_aendern_erforderlich=True,
    )
    db.add(neu)
    db.commit()
    return templates.TemplateResponse(
        "settings/mitarbeiter_angelegt.html",
        {"request": request, "user": user, "active": "verwaltung",
         "neuer_mitarbeiter": neu, "passwort": passwort},
    )


@router.post("/fahrzeug")
def fahrzeug_anlegen(user=Depends(require_gf_or_admin), db: Session = Depends(get_db),
                     kennzeichen: str = Form(...), hersteller: str = Form(""),
                     modell: str = Form(""), typ: VehicleTyp = Form(VehicleTyp.sprinter),
                     km_stand: int = Form(0), hu_faellig: str = Form("")):
    if not kennzeichen.strip():
        raise HTTPException(status_code=400, detail="Kennzeichen angeben")
    db.add(Vehicle(
        kennzeichen=kennzeichen.strip().upper(), hersteller=hersteller.strip(),
        modell=modell.strip(), typ=typ, km_stand=max(0, km_stand),
        status=VehicleStatus.einsatzbereit,
        hu_faellig=(date.fromisoformat(hu_faellig) if hu_faellig else None),
    ))
    db.commit()
    return RedirectResponse("/verwaltung", status_code=303)


@router.post("/mitarbeiter/{mitarbeiter_id}/loeschen")
def mitarbeiter_loeschen(mitarbeiter_id: int, user=Depends(require_gf_or_admin),
                         db: Session = Depends(get_db)):
    m = db.get(User, mitarbeiter_id)
    if not m:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    if m.id == user.id:
        raise HTTPException(status_code=400, detail="Das eigene Konto kann nicht gelöscht werden")
    papierkorb.in_papierkorb(db, m)
    return RedirectResponse("/verwaltung", status_code=303)


@router.post("/fahrzeug/{vehicle_id}/loeschen")
def fahrzeug_loeschen(vehicle_id: int, user=Depends(require_gf_or_admin),
                      db: Session = Depends(get_db)):
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Fahrzeug nicht gefunden")
    papierkorb.in_papierkorb(db, v)
    return RedirectResponse("/verwaltung", status_code=303)


@router.post("/mitarbeiter/{mitarbeiter_id}/wiederherstellen")
def mitarbeiter_wiederherstellen(mitarbeiter_id: int, user=Depends(require_gf_or_admin),
                                 db: Session = Depends(get_db)):
    m = db.get(User, mitarbeiter_id)
    if m and m.geloescht_am:
        papierkorb.wiederherstellen(db, m)
    return RedirectResponse("/verwaltung", status_code=303)


@router.post("/fahrzeug/{vehicle_id}/wiederherstellen")
def fahrzeug_wiederherstellen(vehicle_id: int, user=Depends(require_gf_or_admin),
                              db: Session = Depends(get_db)):
    v = db.get(Vehicle, vehicle_id)
    if v and v.geloescht_am:
        papierkorb.wiederherstellen(db, v)
    return RedirectResponse("/verwaltung", status_code=303)


@router.get("/backup")
def backup_herunterladen(user=Depends(require_gf_or_admin)):
    daten = backup.backup_erzeugen()
    if daten is None:
        raise HTTPException(
            status_code=400,
            detail="Backup-Download ist nur für die lokale SQLite-Datenbank verfügbar "
                   "(im Docker/Postgres-Betrieb übernehmen pg_dump/Volume-Snapshots die Sicherung).",
        )
    fname = f"dispohub_backup_{datetime.now().strftime('%Y-%m-%d_%H%M')}.db"
    return StreamingResponse(
        iter([daten]), media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
