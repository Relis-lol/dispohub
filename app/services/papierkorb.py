"""Papierkorb-Logik: Soft-Delete mit 30 Tagen Aufbewahrung, danach endgültig.

Schutz vor Fehlklicks: "Löschen" im Admin-Menü verschiebt nur in den Papierkorb
(geloescht_am wird gesetzt). Wiederherstellen ist jederzeit innerhalb der Frist
möglich. Beim App-Start und beim Öffnen der Verwaltung werden abgelaufene
Einträge endgültig entfernt.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import User, Vehicle

AUFBEWAHRUNG_TAGE = 30


def tage_verbleibend(geloescht_am: datetime) -> int:
    """Wie viele Tage bis zur endgültigen Löschung bleiben (min. 0)."""
    frist = geloescht_am + timedelta(days=AUFBEWAHRUNG_TAGE)
    return max(0, (frist - datetime.now()).days)


def purge_abgelaufene(db: Session) -> int:
    """Entfernt Einträge endgültig, deren Papierkorb-Frist abgelaufen ist."""
    grenze = datetime.now() - timedelta(days=AUFBEWAHRUNG_TAGE)
    entfernt = 0
    for model in (User, Vehicle):
        alte = db.query(model).filter(model.geloescht_am.isnot(None),
                                      model.geloescht_am < grenze).all()
        for eintrag in alte:
            db.delete(eintrag)
            entfernt += 1
    if entfernt:
        db.commit()
    return entfernt


def in_papierkorb(db: Session, eintrag: User | Vehicle) -> None:
    """Verschiebt Mitarbeiter/Fahrzeug in den Papierkorb und löst Zuordnungen."""
    eintrag.geloescht_am = datetime.now()
    if isinstance(eintrag, User):
        eintrag.vehicle_id = None
    else:
        # Fahrer freigeben, die diesem Fahrzeug zugeordnet sind
        for fahrer in db.query(User).filter(User.vehicle_id == eintrag.id).all():
            fahrer.vehicle_id = None
    db.commit()


def wiederherstellen(db: Session, eintrag: User | Vehicle) -> None:
    eintrag.geloescht_am = None
    db.commit()
