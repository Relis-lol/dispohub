"""Ansprechpartner-Seite für Fahrer: Nummern mit Anruf-Ampel (grün/rot)."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user
from app.models import User, Role
from app.templating import templates

router = APIRouter()


@router.get("/kontakte", response_class=HTMLResponse)
def kontakte(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    ansprechpartner = (
        db.query(User)
        .filter(User.role.in_([Role.geschaeftsfuehrung, Role.buero]),
                User.geloescht_am.is_(None), User.phone.isnot(None))
        .order_by(User.role, User.name)
        .all()
    )
    return templates.TemplateResponse(
        "contacts/list.html",
        {"request": request, "user": user, "active": "kontakte",
         "ansprechpartner": ansprechpartner},
    )
