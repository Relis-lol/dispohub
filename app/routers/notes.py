from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_office
from app.models import Note
from app.templating import templates

router = APIRouter(prefix="/notizen")


@router.get("", response_class=HTMLResponse)
def liste(request: Request, user=Depends(require_office), db: Session = Depends(get_db)):
    notizen = db.query(Note).order_by(Note.created_at.desc()).limit(50).all()
    return templates.TemplateResponse(
        "notes/list.html",
        {"request": request, "user": user, "active": "notizen", "notizen": notizen},
    )


@router.post("")
def erstellen(user=Depends(require_office), db: Session = Depends(get_db), text: str = Form(...)):
    if text.strip():
        db.add(Note(text=text.strip(), ersteller_id=user.id))
        db.commit()
    return RedirectResponse("/notizen", status_code=303)
