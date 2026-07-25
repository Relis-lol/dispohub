"""Umfragen: kleine Ja/Nein-Fragen vom Büro/GF an die Fahrer."""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user, require_area
from app.models import Poll, PollAntwort, User, Role
from app.templating import templates

router = APIRouter(prefix="/umfragen")
require_aufgaben = require_area("aufgaben")


@router.get("", response_class=HTMLResponse)
def uebersicht(request: Request, user=Depends(require_aufgaben), db: Session = Depends(get_db)):
    umfragen = db.query(Poll).order_by(Poll.offen.desc(), Poll.created_at.desc()).limit(30).all()
    anzahl_fahrer = (db.query(User)
                     .filter(User.role == Role.fahrer, User.geloescht_am.is_(None)).count())
    return templates.TemplateResponse(
        "polls/office.html",
        {"request": request, "user": user, "active": "umfragen",
         "umfragen": umfragen, "anzahl_fahrer": anzahl_fahrer},
    )


@router.post("")
def erstellen(user=Depends(require_aufgaben), db: Session = Depends(get_db),
              frage: str = Form(...)):
    if frage.strip():
        db.add(Poll(frage=frage.strip(), erstellt_von_id=user.id))
        db.commit()
    return RedirectResponse("/umfragen", status_code=303)


@router.post("/{poll_id}/schliessen")
def schliessen(poll_id: int, user=Depends(require_aufgaben), db: Session = Depends(get_db)):
    poll = db.get(Poll, poll_id)
    if poll:
        poll.offen = False
        db.commit()
    return RedirectResponse("/umfragen", status_code=303)


@router.post("/{poll_id}/antwort")
def antworten(poll_id: int, user: User = Depends(require_user), db: Session = Depends(get_db),
              antwort: str = Form(...)):
    poll = db.get(Poll, poll_id)
    if not poll or not poll.offen:
        raise HTTPException(status_code=404, detail="Umfrage nicht gefunden oder geschlossen")
    schon = (db.query(PollAntwort)
             .filter(PollAntwort.poll_id == poll_id, PollAntwort.user_id == user.id).first())
    if schon:
        raise HTTPException(status_code=400, detail="Bereits beantwortet")
    db.add(PollAntwort(poll_id=poll_id, user_id=user.id, antwort=(antwort == "ja")))
    db.commit()
    ziel = "/aufgaben" if user.role == Role.fahrer else "/umfragen"
    return RedirectResponse(ziel, status_code=303)
