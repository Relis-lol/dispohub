from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ParkingSpot(Base):
    """Von einem Fahrer gemeldeter Standort (wo das Fahrzeug gerade steht/geparkt ist)."""

    __tablename__ = "parking_spots"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    lat: Mapped[float] = mapped_column(Numeric(9, 6))
    lng: Mapped[float] = mapped_column(Numeric(9, 6))
    notiz: Mapped[str | None] = mapped_column(Text, nullable=True)
    foto_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vehicle: Mapped["Vehicle"] = relationship()  # noqa: F821
    reporter: Mapped["User"] = relationship()  # noqa: F821
    foto: Mapped["Document | None"] = relationship()  # noqa: F821

    @property
    def google_maps_url(self) -> str:
        return f"https://www.google.com/maps?q={self.lat},{self.lng}"
