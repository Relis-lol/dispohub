"""Zugriff auf App-weite Einstellungen (Key-Value, z.B. Firmenlogo/Website)."""
from sqlalchemy.orm import Session

from app.models import AppSetting

LOGO_PFAD = "logo_pfad"
FIRMEN_WEBSITE = "firmen_website"


def get_setting(db: Session, key: str) -> str | None:
    eintrag = db.get(AppSetting, key)
    return eintrag.value if eintrag else None


def set_setting(db: Session, key: str, value: str | None) -> None:
    eintrag = db.get(AppSetting, key)
    if not eintrag:
        eintrag = AppSetting(key=key)
        db.add(eintrag)
    eintrag.value = value
    db.commit()
