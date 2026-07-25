from datetime import date, datetime

from sqlalchemy import String, ForeignKey, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SafetyItem(Base):
    """ADR-/Sicherheitsmittel am Fahrzeug mit Ablaufdatum (Feuerlöscher, Augenspülung, ...)."""

    __tablename__ = "safety_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    bezeichnung: Mapped[str] = mapped_column(String(120))
    ablauf_am: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vehicle: Mapped["Vehicle"] = relationship()  # noqa: F821
