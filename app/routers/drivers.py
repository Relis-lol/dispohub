from datetime import date

from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_area
from app.models import (
    User, Role, UserStatus, Document, Note, PersonnelEntry, EntryArt,
    LeaveRequest, LeaveStatus,
)
from app.models.user import ROLE_LABELS
from app.security import hash_password
from app.services.uploads import save_upload
from app.templating import templates

router = APIRouter(prefix="/mitarbeiter")
require_mitarbeiter = require_area("mitarbeiter")


@router.get("", response_class=HTMLResponse)
def liste(request: Request, user=Depends(require_mitarbeiter), db: Session = Depends(get_db)):
    mitarbeiter = (db.query(User).filter(User.geloescht_am.is_(None))
                   .order_by(User.role, User.name).all())
    offene_antraege = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.status == LeaveStatus.offen)
        .order_by(LeaveRequest.von.asc())
        .all()
    )
    # Resturlaub je Antragsteller (für die Entscheidung direkt sichtbar)
    jahr = date.today().year
    resturlaub = {}
    for a in offene_antraege:
        if a.user_id in resturlaub:
            continue
        genommen = sum(
            e.tage for e in db.query(PersonnelEntry)
            .filter(PersonnelEntry.user_id == a.user_id, PersonnelEntry.art == EntryArt.urlaub)
            .all() if e.datum.year == jahr
        )
        resturlaub[a.user_id] = a.user.urlaubstage_kontingent - genommen
    return templates.TemplateResponse(
        "drivers/list.html",
        {"request": request, "user": user, "active": "mitarbeiter", "mitarbeiter": mitarbeiter,
         "offene_antraege": offene_antraege, "resturlaub": resturlaub},
    )


def _get_mitarbeiter(db: Session, mitarbeiter_id: int) -> User:
    m = db.get(User, mitarbeiter_id)
    if not m:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    return m


@router.get("/{mitarbeiter_id}", response_class=HTMLResponse)
def detail(mitarbeiter_id: int, request: Request, user=Depends(require_mitarbeiter),
           db: Session = Depends(get_db)):
    m = _get_mitarbeiter(db, mitarbeiter_id)

    eintraege = (
        db.query(PersonnelEntry)
        .filter(PersonnelEntry.user_id == m.id)
        .order_by(PersonnelEntry.datum.desc())
        .all()
    )
    jahr = date.today().year
    urlaub_genommen = sum(e.tage for e in eintraege
                          if e.art == EntryArt.urlaub and e.datum.year == jahr)
    krank_tage = sum(e.tage for e in eintraege
                     if e.art == EntryArt.krank and e.datum.year == jahr)
    monat_start = date.today().replace(day=1)
    stunden_monat = (
        db.query(func.coalesce(func.sum(PersonnelEntry.stunden), 0))
        .filter(PersonnelEntry.user_id == m.id, PersonnelEntry.art == EntryArt.stunden,
                PersonnelEntry.datum >= monat_start)
        .scalar()
    )
    dokumente = (
        db.query(Document)
        .filter(Document.user_id == m.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    notizen = (
        db.query(Note)
        .filter(Note.mitarbeiter_id == m.id)
        .order_by(Note.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "drivers/detail.html",
        {
            "request": request, "user": user, "active": "mitarbeiter",
            "m": m, "eintraege": eintraege,
            "urlaub_genommen": urlaub_genommen, "krank_tage": krank_tage,
            "stunden_monat": stunden_monat, "jahr": jahr,
            "dokumente": dokumente, "notizen": notizen,
            "rollen": [(r.value, label) for r, label in ROLE_LABELS.items()],
            "status_werte": [s.value for s in UserStatus],
        },
    )


@router.post("/{mitarbeiter_id}/stammdaten")
def stammdaten_speichern(mitarbeiter_id: int, user=Depends(require_mitarbeiter),
                         db: Session = Depends(get_db),
                         name: str = Form(...), email: str = Form(...),
                         telefon: str = Form(""), geburtstag: str = Form(""),
                         status: UserStatus = Form(UserStatus.aktiv),
                         rolle: str = Form("")):
    m = _get_mitarbeiter(db, mitarbeiter_id)
    email = email.strip().lower()
    if not name.strip() or not email:
        raise HTTPException(status_code=400, detail="Name und E-Mail angeben")
    doppelt = db.query(User).filter(User.email == email, User.id != m.id).first()
    if doppelt:
        raise HTTPException(status_code=400, detail="E-Mail-Adresse ist bereits vergeben")
    m.name = name.strip()
    m.email = email
    m.phone = telefon.strip() or None
    m.geburtstag = date.fromisoformat(geburtstag) if geburtstag else None
    m.status = status
    # Rollenwechsel nur durch GF/Admin, und nicht am eigenen Konto (Aussperr-Schutz)
    if rolle and user.role in (Role.admin, Role.geschaeftsfuehrung) and m.id != user.id:
        m.role = Role(rolle)
    db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)


@router.post("/{mitarbeiter_id}/passwort")
def passwort_zuruecksetzen(mitarbeiter_id: int, user=Depends(require_mitarbeiter),
                           db: Session = Depends(get_db),
                           neues_passwort: str = Form(...)):
    if user.role not in (Role.admin, Role.geschaeftsfuehrung):
        raise HTTPException(status_code=403, detail="Passwörter setzt nur GF/Admin zurück")
    m = _get_mitarbeiter(db, mitarbeiter_id)
    if len(neues_passwort) < 6:
        raise HTTPException(status_code=400, detail="Passwort braucht mindestens 6 Zeichen")
    m.password_hash = hash_password(neues_passwort)
    db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)


@router.post("/{mitarbeiter_id}/karten")
def karten_speichern(mitarbeiter_id: int, user=Depends(require_mitarbeiter),
                     db: Session = Depends(get_db),
                     fahrerkarte_ablauf: str = Form(""), adr_karte_ablauf: str = Form(""),
                     urlaubstage_kontingent: int = Form(24)):
    m = _get_mitarbeiter(db, mitarbeiter_id)
    m.fahrerkarte_ablauf = date.fromisoformat(fahrerkarte_ablauf) if fahrerkarte_ablauf else None
    m.adr_karte_ablauf = date.fromisoformat(adr_karte_ablauf) if adr_karte_ablauf else None
    m.urlaubstage_kontingent = max(0, urlaubstage_kontingent)
    db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)


@router.post("/{mitarbeiter_id}/eintrag")
def eintrag_hinzufuegen(mitarbeiter_id: int, user=Depends(require_mitarbeiter),
                        db: Session = Depends(get_db),
                        art: EntryArt = Form(...), datum: date = Form(...),
                        bis: str = Form(""), stunden: str = Form(""), notiz: str = Form("")):
    _get_mitarbeiter(db, mitarbeiter_id)
    entry = PersonnelEntry(
        user_id=mitarbeiter_id, art=art, datum=datum,
        bis=(date.fromisoformat(bis) if bis and art == EntryArt.urlaub else None),
        stunden=(float(stunden.replace(",", ".")) if stunden and art == EntryArt.stunden else None),
        notiz=(notiz.strip() or None),
    )
    if entry.art == EntryArt.stunden and entry.stunden is None:
        raise HTTPException(status_code=400, detail="Bitte Stundenzahl angeben")
    db.add(entry)
    db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)


@router.post("/{mitarbeiter_id}/eintrag/{entry_id}/loeschen")
def eintrag_loeschen(mitarbeiter_id: int, entry_id: int, user=Depends(require_mitarbeiter),
                     db: Session = Depends(get_db)):
    entry = db.get(PersonnelEntry, entry_id)
    if entry and entry.user_id == mitarbeiter_id:
        db.delete(entry)
        db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)


@router.post("/{mitarbeiter_id}/foto")
def foto_hochladen(mitarbeiter_id: int, user=Depends(require_mitarbeiter),
                   db: Session = Depends(get_db), foto: UploadFile = File(...)):
    m = _get_mitarbeiter(db, mitarbeiter_id)
    doc = save_upload(foto)
    if doc:
        m.foto_pfad = doc.pfad
        doc.user_id = m.id
        db.add(doc)
        db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)


@router.post("/{mitarbeiter_id}/dokument")
def dokument_hochladen(mitarbeiter_id: int, user=Depends(require_mitarbeiter),
                       db: Session = Depends(get_db),
                       datei: UploadFile = File(...), typ: str = Form("vertrag")):
    m = _get_mitarbeiter(db, mitarbeiter_id)
    doc = save_upload(datei, dokumente=True)
    if doc:
        doc.user_id = m.id
        if typ.strip():
            doc.typ = typ.strip()
        db.add(doc)
        db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)


@router.post("/{mitarbeiter_id}/notiz")
def notiz_erstellen(mitarbeiter_id: int, user=Depends(require_mitarbeiter),
                    db: Session = Depends(get_db), text: str = Form(...)):
    _get_mitarbeiter(db, mitarbeiter_id)
    if text.strip():
        db.add(Note(text=text.strip(), ersteller_id=user.id, mitarbeiter_id=mitarbeiter_id))
        db.commit()
    return RedirectResponse(f"/mitarbeiter/{mitarbeiter_id}", status_code=303)
