from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Receipt(Base):
    """Roher Beleg im Filedrop-Ordner — einfach reinkopiert, noch nicht als
    Rechnung/Kosten erfasst. Der Steuerberater kann sie direkt einsammeln,
    das Büro kann sie später in die normale Rechnungs-Inbox überführen."""

    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    pfad: Mapped[str] = mapped_column(String(400))
    dateiname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notiz: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hochgeladen_von_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    abgeholt: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    hochgeladen_von: Mapped["User"] = relationship()  # noqa: F821
