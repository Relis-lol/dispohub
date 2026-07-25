import enum
from datetime import date, datetime

from sqlalchemy import String, Integer, Enum as SAEnum, Date, DateTime, Numeric, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class VehicleTyp(str, enum.Enum):
    pkw = "pkw"
    sprinter = "sprinter"
    lkw = "lkw"
    haenger = "haenger"


VEHICLE_TYP_LABELS = {
    VehicleTyp.pkw: "PKW",
    VehicleTyp.sprinter: "Sprinter / Transporter",
    VehicleTyp.lkw: "LKW",
    VehicleTyp.haenger: "Hänger / Auflieger",
}


class VehicleStatus(str, enum.Enum):
    einsatzbereit = "einsatzbereit"
    unterwegs = "unterwegs"
    werkstatt_geplant = "werkstatt_geplant"
    in_reparatur = "in_reparatur"
    eingeschraenkt = "eingeschraenkt"
    ausgefallen = "ausgefallen"


VEHICLE_STATUS_LABELS = {
    VehicleStatus.einsatzbereit: "Einsatzbereit",
    VehicleStatus.unterwegs: "Unterwegs",
    VehicleStatus.werkstatt_geplant: "Werkstatt geplant",
    VehicleStatus.in_reparatur: "In Reparatur",
    VehicleStatus.eingeschraenkt: "Eingeschränkt nutzbar",
    VehicleStatus.ausgefallen: "Ausgefallen",
}

# Statusfarbe für die Oberfläche (Ampel-/Statuslogik)
VEHICLE_STATUS_TONE = {
    VehicleStatus.einsatzbereit: "ok",
    VehicleStatus.unterwegs: "info",
    VehicleStatus.werkstatt_geplant: "warn",
    VehicleStatus.in_reparatur: "warn",
    VehicleStatus.eingeschraenkt: "warn",
    VehicleStatus.ausgefallen: "bad",
}


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    kennzeichen: Mapped[str] = mapped_column(String(20), index=True)
    hersteller: Mapped[str] = mapped_column(String(60))
    modell: Mapped[str] = mapped_column(String(80))
    fin: Mapped[str | None] = mapped_column(String(40), nullable=True)
    erstzulassung: Mapped[date | None] = mapped_column(Date, nullable=True)
    km_stand: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[VehicleStatus] = mapped_column(
        SAEnum(VehicleStatus), default=VehicleStatus.einsatzbereit
    )
    typ: Mapped[VehicleTyp] = mapped_column(SAEnum(VehicleTyp), default=VehicleTyp.sprinter)
    untertyp: Mapped[str | None] = mapped_column(String(80), nullable=True)  # z.B. "Kofferauflieger 13,6m"
    # Verknüpfung für Hängerzüge: welches Zugfahrzeug zieht diesen Hänger normalerweise
    zugfahrzeug_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)

    # Vertrag / Fixkosten
    leasing_anbieter: Mapped[str | None] = mapped_column(String(120), nullable=True)
    leasing_ende: Mapped[date | None] = mapped_column(Date, nullable=True)
    monatliche_fixkosten: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Prüf-/Fristtermine als Datumsfelder (zusätzlich als Appointments abbildbar)
    hu_faellig: Mapped[date | None] = mapped_column(Date, nullable=True)
    sp_faellig: Mapped[date | None] = mapped_column(Date, nullable=True)
    uvv_faellig: Mapped[date | None] = mapped_column(Date, nullable=True)
    tacho_faellig: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Papierkorb: gesetzt = gelöscht, nach 30 Tagen endgültige Entfernung
    geloescht_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    driver: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="vehicle", uselist=False, foreign_keys="User.vehicle_id"
    )
    damages: Mapped[list["DamageReport"]] = relationship(  # noqa: F821
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(  # noqa: F821
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    costs: Mapped[list["CostEntry"]] = relationship(  # noqa: F821
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    zugfahrzeug: Mapped["Vehicle | None"] = relationship(remote_side=[id], foreign_keys=[zugfahrzeug_id])

    @property
    def name(self) -> str:
        return f"{self.kennzeichen} · {self.hersteller} {self.modell}"

    @property
    def status_label(self) -> str:
        return VEHICLE_STATUS_LABELS.get(self.status, self.status.value)

    @property
    def status_tone(self) -> str:
        return VEHICLE_STATUS_TONE.get(self.status, "info")

    @property
    def typ_label(self) -> str:
        return VEHICLE_TYP_LABELS.get(self.typ, self.typ.value)
