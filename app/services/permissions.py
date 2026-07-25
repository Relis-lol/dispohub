"""Von der GF konfigurierbare Sichtbarkeit einzelner Bereiche für die Rolle 'Büro'."""
from sqlalchemy.orm import Session

from app.models import AreaPermission, Role, User

BEREICHE = [
    "fahrzeuge", "mitarbeiter", "kalender", "schaeden",
    "kosten", "rechnungen", "export", "tankkarten", "aufgaben",
]


def is_erlaubt(db: Session, user: User, bereich: str) -> bool:
    """Admin/GF: immer erlaubt. Büro: abhängig von der Einstellung. Alle anderen: nie."""
    if user.role in (Role.admin, Role.geschaeftsfuehrung):
        return True
    if user.role != Role.buero:
        return False
    perm = db.query(AreaPermission).filter(AreaPermission.bereich == bereich).first()
    return perm.buero_erlaubt if perm else True


def alle_bereiche_mit_status(db: Session) -> list[tuple[str, bool]]:
    """Für die Einstellungsseite: (bereich, aktuell_erlaubt) je bekanntem Bereich."""
    vorhanden = {p.bereich: p.buero_erlaubt for p in db.query(AreaPermission).all()}
    return [(b, vorhanden.get(b, True)) for b in BEREICHE]
