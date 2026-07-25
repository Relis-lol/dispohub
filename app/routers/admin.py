from datetime import time

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_gf_or_admin, require_it_or_admin
from app.models import AreaPermission, User, Role, Vehicle, Erreichbarkeit
from app.services.permissions import BEREICHE, alle_bereiche_mit_status
from app.templating import templates

router = APIRouter()


def _ansprechpartner(db: Session) -> list[User]:
    """GF und Büro mit Telefonnummer — die sehen Fahrer als Anruf-Kontakte."""
    return (
        db.query(User)
        .filter(User.role.in_([Role.geschaeftsfuehrung, Role.buero]),
                User.geloescht_am.is_(None), User.phone.isnot(None))
        .order_by(User.role, User.name)
        .all()
    )


@router.get("/einstellungen/rechte", response_class=HTMLResponse)
def rechte_form(request: Request, user=Depends(require_gf_or_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "settings/rechte.html",
        {"request": request, "user": user, "active": "einstellungen",
         "bereiche": alle_bereiche_mit_status(db),
         "ansprechpartner": _ansprechpartner(db)},
    )


@router.post("/einstellungen/erreichbarkeit")
def erreichbarkeit_speichern(user=Depends(require_gf_or_admin), db: Session = Depends(get_db),
                             kontakt_id: int = Form(...), status: Erreichbarkeit = Form(...),
                             von: str = Form(""), bis: str = Form("")):
    kontakt = db.get(User, kontakt_id)
    if not kontakt or kontakt.role not in (Role.geschaeftsfuehrung, Role.buero):
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden")
    kontakt.erreichbarkeit = status
    kontakt.erreichbar_von = time.fromisoformat(von) if von else None
    kontakt.erreichbar_bis = time.fromisoformat(bis) if bis else None
    db.commit()
    return RedirectResponse("/einstellungen/rechte", status_code=303)


@router.post("/einstellungen/rechte")
async def rechte_speichern(request: Request, user=Depends(require_gf_or_admin),
                           db: Session = Depends(get_db)):
    form = await request.form()
    for bereich in BEREICHE:
        perm = db.query(AreaPermission).filter(AreaPermission.bereich == bereich).first()
        if not perm:
            perm = AreaPermission(bereich=bereich)
            db.add(perm)
        perm.buero_erlaubt = f"bereich_{bereich}" in form
    db.commit()
    return RedirectResponse("/einstellungen/rechte", status_code=303)


# --- IT-Bereich: technischer Zugriff, keine Finanzdaten --------------------
@router.get("/it", response_class=HTMLResponse)
def it_uebersicht(request: Request, user=Depends(require_it_or_admin), db: Session = Depends(get_db)):
    # Bewusst eingeschränkte Sicht: nur Namen/Rollen, keine Kontaktdaten, keine Kosten.
    mitarbeiter = (db.query(User).filter(User.geloescht_am.is_(None))
                   .order_by(User.role, User.name).all())
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    return templates.TemplateResponse(
        "settings/it.html",
        {"request": request, "user": user, "active": "it",
         "mitarbeiter": mitarbeiter, "fahrzeuge": fahrzeuge},
    )
