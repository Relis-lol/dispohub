from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Task, TaskStatus, User


def tasks_for_driver(db: Session, user: User) -> list[Task]:
    """Eigene Aufgaben + Aufgaben am aktuellen Fahrzeug + allgemeine (an alle Fahrer)."""
    q = db.query(Task).filter(Task.status == TaskStatus.offen)
    bedingungen = [Task.zugewiesen_user_id == user.id]
    if user.vehicle_id:
        bedingungen.append(Task.vehicle_id == user.vehicle_id)
    bedingungen.append((Task.zugewiesen_user_id.is_(None)) & (Task.vehicle_id.is_(None)))
    return q.filter(or_(*bedingungen)).order_by(Task.faellig_am.asc().nullslast()).all()
