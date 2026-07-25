"""Urlaubsanträge: Fahrer beantragt mobil, GF/Büro genehmigt oder lehnt ab."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user, require_area
from app.models import LeaveRequest, LeaveStatus, PersonnelEntry, EntryArt
from app.models.user import Role

router = APIRouter(prefix="/urlaub")
require_mitarbeiter = require_area("mitarbeiter")


@router.post("")
def beantragen(user=Depends(require_user), db: Session = Depends(get_db),
               von: date = Form(...), bis: date = Form(...), notiz: str = Form("")):
    if bis < von:
        raise HTTPException(status_code=400, detail="'Bis' darf nicht vor 'Von' liegen")
    if von < date.today():
        raise HTTPException(status_code=400, detail="Urlaub kann nicht rückwirkend beantragt werden")
    db.add(LeaveRequest(user_id=user.id, von=von, bis=bis, notiz=(notiz.strip() or None)))
    db.commit()
    ziel = "/melden?urlaub=1" if user.role == Role.fahrer else f"/mitarbeiter/{user.id}"
    return RedirectResponse(ziel, status_code=303)


def _offener_antrag(db: Session, antrag_id: int) -> LeaveRequest:
    antrag = db.get(LeaveRequest, antrag_id)
    if not antrag:
        raise HTTPException(status_code=404, detail="Antrag nicht gefunden")
    if antrag.status != LeaveStatus.offen:
        raise HTTPException(status_code=400, detail="Antrag ist bereits entschieden")
    return antrag


@router.post("/{antrag_id}/genehmigen")
def genehmigen(antrag_id: int, user=Depends(require_mitarbeiter), db: Session = Depends(get_db)):
    antrag = _offener_antrag(db, antrag_id)
    antrag.status = LeaveStatus.genehmigt
    antrag.entschieden_von_id = user.id
    antrag.entschieden_am = datetime.now()
    # Genehmigter Urlaub landet direkt in der Personalakte (zählt auf das Urlaubskonto)
    db.add(PersonnelEntry(
        user_id=antrag.user_id, art=EntryArt.urlaub, datum=antrag.von,
        bis=(antrag.bis if antrag.bis > antrag.von else None),
        notiz=antrag.notiz or "Urlaubsantrag genehmigt",
    ))
    db.commit()
    return RedirectResponse("/mitarbeiter", status_code=303)


@router.post("/{antrag_id}/ablehnen")
def ablehnen(antrag_id: int, user=Depends(require_mitarbeiter), db: Session = Depends(get_db)):
    antrag = _offener_antrag(db, antrag_id)
    antrag.status = LeaveStatus.abgelehnt
    antrag.entschieden_von_id = user.id
    antrag.entschieden_am = datetime.now()
    db.commit()
    return RedirectResponse("/mitarbeiter", status_code=303)
