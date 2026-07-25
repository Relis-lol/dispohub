from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    damage_id: Mapped[int | None] = mapped_column(ForeignKey("damage_reports.id"), nullable=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    # Personalakte: Dokument gehört zu einem Mitarbeiter (z.B. Arbeitsvertrag)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Öffentlicher Pfad relativ zum Static-Mount, z.B. /static/uploads/xyz.jpg
    pfad: Mapped[str] = mapped_column(String(400))
    typ: Mapped[str] = mapped_column(String(60), default="foto")
    dateiname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    damage: Mapped["DamageReport | None"] = relationship(back_populates="documents")  # noqa: F821
