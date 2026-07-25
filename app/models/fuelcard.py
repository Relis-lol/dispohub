from datetime import date, datetime

from sqlalchemy import String, ForeignKey, Date, DateTime, Numeric, Boolean, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class FuelCard(Base):
    __tablename__ = "fuel_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    kartennummer: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    anbieter: Mapped[str] = mapped_column(String(80), default="")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    vehicle: Mapped["Vehicle | None"] = relationship()  # noqa: F821
    transactions: Mapped[list["FuelTransaction"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )


class FuelTransaction(Base):
    __tablename__ = "fuel_transactions"
    # Duplikaterkennung: identische Buchung derselben Karte wird nicht erneut importiert
    __table_args__ = (
        UniqueConstraint("card_id", "datum", "betrag", "produkt", name="uq_fuel_tx"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("fuel_cards.id"))
    datum: Mapped[date] = mapped_column(Date)
    produkt: Mapped[str] = mapped_column(String(60), default="Diesel")
    menge_liter: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    betrag: Mapped[float] = mapped_column(Numeric(10, 2))
    cost_id: Mapped[int | None] = mapped_column(ForeignKey("cost_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    card: Mapped["FuelCard"] = relationship(back_populates="transactions")
