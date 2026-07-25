import enum
from datetime import date, datetime

from sqlalchemy import String, Enum as SAEnum, ForeignKey, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AppointmentSource(str, enum.Enum):
    schaden = "schaden"
    pruefung = "pruefung"
    wartung = "wartung"
    werkstatt = "werkstatt"
    leasing = "leasing"
    versicherung = "versicherung"
    allgemein = "allgemein"


class AppointmentStatus(str, enum.Enum):
    offen = "offen"
    erledigt = "erledigt"


SOURCE_LABELS = {
    AppointmentSource.schaden: "Schaden",
    AppointmentSource.pruefung: "Prüfung",
    AppointmentSource.wartung: "Wartung",
    AppointmentSource.werkstatt: "Werkstatt",
    AppointmentSource.leasing: "Leasing",
    AppointmentSource.versicherung: "Versicherung",
    AppointmentSource.allgemein: "Allgemein",
}


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    damage_id: Mapped[int | None] = mapped_column(ForeignKey("damage_reports.id"), nullable=True)

    titel: Mapped[str] = mapped_column(String(200))
    quelle: Mapped[AppointmentSource] = mapped_column(
        SAEnum(AppointmentSource), default=AppointmentSource.allgemein
    )
    faellig_am: Mapped[date] = mapped_column(Date)
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(AppointmentStatus), default=AppointmentStatus.offen
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vehicle: Mapped["Vehicle | None"] = relationship(back_populates="appointments")  # noqa: F821
    damage: Mapped["DamageReport | None"] = relationship(back_populates="appointments")  # noqa: F821

    @property
    def quelle_label(self) -> str:
        return SOURCE_LABELS.get(self.quelle, self.quelle.value)
