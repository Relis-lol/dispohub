import enum
from datetime import date, datetime

from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TaskStatus(str, enum.Enum):
    offen = "offen"
    erledigt = "erledigt"


TASK_STATUS_LABELS = {TaskStatus.offen: "Offen", TaskStatus.erledigt: "Erledigt"}


class Task(Base):
    """Aufgabe vom Büro/GF an einen Fahrer (und/oder Fahrzeug), zum Abhaken."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    titel: Mapped[str] = mapped_column(String(200))
    beschreibung: Mapped[str | None] = mapped_column(Text, nullable=True)
    faellig_am: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.offen)

    zugewiesen_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    erstellt_von_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    erledigt_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    zugewiesen: Mapped["User | None"] = relationship(foreign_keys=[zugewiesen_user_id])  # noqa: F821
    erstellt_von: Mapped["User"] = relationship(foreign_keys=[erstellt_von_id])  # noqa: F821
    vehicle: Mapped["Vehicle | None"] = relationship()  # noqa: F821

    @property
    def status_label(self) -> str:
        return TASK_STATUS_LABELS.get(self.status, self.status.value)
