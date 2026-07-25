import enum
from datetime import date, datetime

from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, DateTime, Date, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Priority(str, enum.Enum):
    info = "info"
    normal = "normal"
    kritisch = "kritisch"


class DamageStatus(str, enum.Enum):
    gemeldet = "gemeldet"
    uebernommen = "uebernommen"
    in_reparatur = "in_reparatur"
    erledigt = "erledigt"


PRIORITY_TONE = {
    Priority.info: "info",
    Priority.normal: "muted",
    Priority.kritisch: "bad",
}

PRIORITY_LABELS = {
    Priority.info: "Info",
    Priority.normal: "Normal",
    Priority.kritisch: "Kritisch",
}

DAMAGE_STATUS_LABELS = {
    DamageStatus.gemeldet: "Neu gemeldet",
    DamageStatus.uebernommen: "Übernommen",
    DamageStatus.in_reparatur: "In Reparatur",
    DamageStatus.erledigt: "Erledigt",
}


class DamageReport(Base):
    __tablename__ = "damage_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    beschreibung: Mapped[str] = mapped_column(Text)
    prioritaet: Mapped[Priority] = mapped_column(SAEnum(Priority), default=Priority.normal)
    status: Mapped[DamageStatus] = mapped_column(SAEnum(DamageStatus), default=DamageStatus.gemeldet)
    nachricht_an_gf: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Wann/wo der Schaden entstanden ist (nicht zu verwechseln mit created_at = Meldezeitpunkt)
    schadensdatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    ort: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Position auf der Fahrzeug-Draufsicht (0..1, relativ), falls per Sticky-Note erfasst
    position_x: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    position_y: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vehicle: Mapped["Vehicle"] = relationship(back_populates="damages")  # noqa: F821
    reporter: Mapped["User | None"] = relationship()  # noqa: F821
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        back_populates="damage", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="damage")  # noqa: F821
    costs: Mapped[list["CostEntry"]] = relationship(back_populates="damage")  # noqa: F821

    @property
    def priority_tone(self) -> str:
        return PRIORITY_TONE.get(self.prioritaet, "info")

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.prioritaet, self.prioritaet.value)

    @property
    def status_label(self) -> str:
        return DAMAGE_STATUS_LABELS.get(self.status, self.status.value)
