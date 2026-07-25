import enum
from datetime import date, datetime

from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, Date, DateTime, Numeric, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.cost import CostCategory


class InvoiceStatus(str, enum.Enum):
    eingegangen = "eingegangen"   # in der Prüf-Inbox, noch nicht bestätigt
    geprueft = "geprueft"         # von GF bestätigt und zugeordnet
    ungeklaert = "ungeklaert"     # unklar / fehlende Daten


INVOICE_STATUS_LABELS = {
    InvoiceStatus.eingegangen: "In Prüfung",
    InvoiceStatus.geprueft: "Geprüft",
    InvoiceStatus.ungeklaert: "Ungeklärt",
}

INVOICE_STATUS_TONE = {
    InvoiceStatus.eingegangen: "warn",
    InvoiceStatus.geprueft: "ok",
    InvoiceStatus.ungeklaert: "bad",
}


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Rohdaten aus der (simulierten) E-Mail
    absender: Mapped[str] = mapped_column(String(200))
    betreff: Mapped[str] = mapped_column(String(300))
    rechnungsnummer: Mapped[str | None] = mapped_column(String(80), nullable=True)
    betrag: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    rechnungsdatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    eingegangen_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    anhang_pfad: Mapped[str | None] = mapped_column(String(400), nullable=True)

    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus), default=InvoiceStatus.eingegangen
    )

    # Vorschläge aus der Regel-Vorsortierung
    vorschlag_kategorie: Mapped[CostCategory | None] = mapped_column(
        SAEnum(CostCategory), nullable=True
    )
    vorschlag_vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    ist_duplikat: Mapped[bool] = mapped_column(Boolean, default=False)
    hinweis: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Bestätigte Zuordnung
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    kategorie: Mapped[CostCategory | None] = mapped_column(SAEnum(CostCategory), nullable=True)
    cost_id: Mapped[int | None] = mapped_column(ForeignKey("cost_entries.id"), nullable=True)

    vehicle: Mapped["Vehicle | None"] = relationship(foreign_keys=[vehicle_id])  # noqa: F821
    vorschlag_vehicle: Mapped["Vehicle | None"] = relationship(  # noqa: F821
        foreign_keys=[vorschlag_vehicle_id]
    )

    @property
    def status_label(self) -> str:
        return INVOICE_STATUS_LABELS.get(self.status, self.status.value)

    @property
    def status_tone(self) -> str:
        return INVOICE_STATUS_TONE.get(self.status, "info")
