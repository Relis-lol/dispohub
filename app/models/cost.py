import enum
from datetime import date, datetime

from sqlalchemy import String, Enum as SAEnum, ForeignKey, Date, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CostCategory(str, enum.Enum):
    leasing = "leasing"
    finanzierung = "finanzierung"
    reparatur = "reparatur"
    wartung = "wartung"
    reifen = "reifen"
    versicherung = "versicherung"
    steuer = "steuer"
    kraftstoff = "kraftstoff"
    adblue = "adblue"
    tankkarte = "tankkarte"
    maut = "maut"
    pruefung = "pruefung"
    werkstatt = "werkstatt"
    ausruestung = "ausruestung"
    sonderzahlung = "sonderzahlung"
    sonstiges = "sonstiges"


CATEGORY_LABELS = {
    CostCategory.leasing: "Leasing",
    CostCategory.finanzierung: "Finanzierung",
    CostCategory.reparatur: "Reparatur",
    CostCategory.wartung: "Wartung",
    CostCategory.reifen: "Reifen",
    CostCategory.versicherung: "Versicherung",
    CostCategory.steuer: "Steuer",
    CostCategory.kraftstoff: "Kraftstoff",
    CostCategory.adblue: "AdBlue",
    CostCategory.tankkarte: "Tankkarte",
    CostCategory.maut: "Maut",
    CostCategory.pruefung: "Prüfung",
    CostCategory.werkstatt: "Werkstatt",
    CostCategory.ausruestung: "Ausrüstung Fahrer",
    CostCategory.sonderzahlung: "Sonderzahlung",
    CostCategory.sonstiges: "Sonstiges",
}


class CostEntry(Base):
    __tablename__ = "cost_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    damage_id: Mapped[int | None] = mapped_column(ForeignKey("damage_reports.id"), nullable=True)
    mitarbeiter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    kategorie: Mapped[CostCategory] = mapped_column(SAEnum(CostCategory), default=CostCategory.sonstiges)
    betrag: Mapped[float] = mapped_column(Numeric(10, 2))
    datum: Mapped[date] = mapped_column(Date)
    beschreibung: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vehicle: Mapped["Vehicle | None"] = relationship(back_populates="costs")  # noqa: F821
    damage: Mapped["DamageReport | None"] = relationship(back_populates="costs")  # noqa: F821
    mitarbeiter: Mapped["User | None"] = relationship()  # noqa: F821

    @property
    def kategorie_label(self) -> str:
        return CATEGORY_LABELS.get(self.kategorie, self.kategorie.value)
