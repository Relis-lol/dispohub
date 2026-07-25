from datetime import date, datetime

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user, require_area
from app.models import Task, TaskStatus, User, Role, Vehicle
from app.services.permissions import is_erlaubt
from app.services.task_service import tasks_for_driver
from app.templating import templates

router = APIRouter(prefix="/aufgaben")
require_aufgaben = require_area("aufgaben")


@router.get("", response_class=HTMLResponse)
def uebersicht(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if user.role == Role.fahrer:
        offen = tasks_for_driver(db, user)
        erledigt = (
            db.query(Task)
            .filter(Task.status == TaskStatus.erledigt, Task.zugewiesen_user_id == user.id)
            .order_by(Task.erledigt_am.desc())
            .limit(10)
            .all()
        )
        # Offene Umfragen, die dieser Fahrer noch nicht beantwortet hat
        from app.models import Poll, PollAntwort
        beantwortet = {a.poll_id for a in
                       db.query(PollAntwort).filter(PollAntwort.user_id == user.id).all()}
        umfragen = [p for p in
                    db.query(Poll).filter(Poll.offen.is_(True)).order_by(Poll.created_at.desc()).all()
                    if p.id not in beantwortet]
        return templates.TemplateResponse(
            "tasks/mobile.html",
            {"request": request, "user": user, "active": "aufgaben", "offen": offen,
             "erledigt": erledigt, "umfragen": umfragen},
        )

    # Büro/GF/Admin: Bereichsrecht prüfen (IT/unbekannte Rollen sind hier nie erlaubt).
    if not is_erlaubt(db, user, "aufgaben"):
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Bereich")

    fahrer = (db.query(User).filter(User.role == Role.fahrer, User.geloescht_am.is_(None))
              .order_by(User.name).all())
    fahrzeuge = (db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None))
                 .order_by(Vehicle.kennzeichen).all())
    offene = db.query(Task).filter(Task.status == TaskStatus.offen).order_by(Task.faellig_am.asc().nullslast()).all()
    erledigte = db.query(Task).filter(Task.status == TaskStatus.erledigt).order_by(Task.erledigt_am.desc()).limit(20).all()
    return templates.TemplateResponse(
        "tasks/office.html",
        {"request": request, "user": user, "active": "aufgaben",
         "fahrer": fahrer, "fahrzeuge": fahrzeuge, "offene": offene, "erledigte": erledigte},
    )


@router.post("")
def erstellen(request: Request, user=Depends(require_aufgaben), db: Session = Depends(get_db),
             titel: str = Form(...), beschreibung: str = Form(""),
             faellig_am: str = Form(""), zugewiesen_user_id: str = Form(""),
             vehicle_id: str = Form("")):
    task = Task(
        titel=titel.strip(), beschreibung=(beschreibung.strip() or None),
        faellig_am=(date.fromisoformat(faellig_am) if faellig_am else None),
        zugewiesen_user_id=(int(zugewiesen_user_id) if zugewiesen_user_id.strip() else None),
        vehicle_id=(int(vehicle_id) if vehicle_id.strip() else None),
        erstellt_von_id=user.id,
    )
    db.add(task)
    db.commit()
    return RedirectResponse("/aufgaben", status_code=303)


@router.post("/{task_id}/erledigt")
def erledigt(task_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")
    # Fahrer dürfen nur eigene/für sie sichtbare Aufgaben abhaken, Büro/GF alles.
    if user.role == Role.fahrer:
        eigene = tasks_for_driver(db, user)
        if task.id not in {t.id for t in eigene}:
            raise HTTPException(status_code=403, detail="Kein Zugriff auf diese Aufgabe")
    task.status = TaskStatus.erledigt
    task.erledigt_am = datetime.utcnow()
    db.commit()
    return RedirectResponse("/aufgaben", status_code=303)
