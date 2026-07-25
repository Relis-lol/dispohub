from datetime import datetime

from sqlalchemy import Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Note(Base):
    """Kurze interne Notiz zwischen Geschäftsführung und Büro."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    ersteller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Optional: Notiz betrifft einen bestimmten Mitarbeiter (erscheint in dessen Personalakte)
    mitarbeiter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ersteller: Mapped["User"] = relationship(foreign_keys=[ersteller_id])  # noqa: F821
    mitarbeiter: Mapped["User | None"] = relationship(foreign_keys=[mitarbeiter_id])  # noqa: F821
