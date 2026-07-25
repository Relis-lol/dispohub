import enum
from datetime import date, datetime

from sqlalchemy import String, Enum as SAEnum, ForeignKey, Date, DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class EntryArt(str, enum.Enum):
    urlaub = "urlaub"
    krank = "krank"
    stunden = "stunden"


ENTRY_LABELS = {
    EntryArt.urlaub: "Urlaub",
    EntryArt.krank: "Krankheit",
    EntryArt.stunden: "Arbeitsstunden",
}


class PersonnelEntry(Base):
    """Personalakten-Eintrag: Urlaub (von-bis), Krankheitstag oder Arbeitsstunden."""

    __tablename__ = "personnel_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    art: Mapped[EntryArt] = mapped_column(SAEnum(EntryArt))
    datum: Mapped[date] = mapped_column(Date)
    # Nur für Urlaub: letzter Urlaubstag (einschließlich). Leer = eintägig.
    bis: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Nur für Arbeitsstunden.
    stunden: Mapped[float | None] = mapped_column(Float, nullable=True)
    notiz: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship()  # noqa: F821

    @property
    def tage(self) -> int:
        """Anzahl Kalendertage des Eintrags (für Urlaubs-/Krankheitszähler)."""
        if self.bis and self.bis > self.datum:
            return (self.bis - self.datum).days + 1
        return 1

    @property
    def art_label(self) -> str:
        return ENTRY_LABELS.get(self.art, self.art.value)
