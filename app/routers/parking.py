from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user
from app.models import User, ParkingSpot
from app.services.uploads import save_upload

router = APIRouter(prefix="/parkplatz")


@router.post("")
def melden(user: User = Depends(require_user), db: Session = Depends(get_db),
          lat: float = Form(...), lng: float = Form(...),
          notiz: str = Form(""), foto: UploadFile | None = File(default=None)):
    if not user.vehicle_id:
        raise HTTPException(status_code=400, detail="Dir ist aktuell kein Fahrzeug zugeordnet")

    spot = ParkingSpot(
        vehicle_id=user.vehicle_id, reporter_id=user.id,
        lat=lat, lng=lng, notiz=(notiz.strip() or None),
    )
    doc = save_upload(foto) if foto else None
    if doc:
        db.add(doc)
        db.flush()
        spot.foto_id = doc.id
    db.add(spot)
    db.commit()
    return RedirectResponse("/melden?parkplatz=1", status_code=303)
