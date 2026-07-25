from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Boolean, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Poll(Base):
    """Kleine Ja/Nein-Umfrage vom Büro/GF an die Fahrer (z.B. Samstag Sonderschicht?)."""

    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True)
    frage: Mapped[str] = mapped_column(String(255))
    erstellt_von_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    offen: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    erstellt_von: Mapped["User"] = relationship()  # noqa: F821
    antworten: Mapped[list["PollAntwort"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan"
    )

    @property
    def ja_stimmen(self) -> list["PollAntwort"]:
        return [a for a in self.antworten if a.antwort]

    @property
    def nein_stimmen(self) -> list["PollAntwort"]:
        return [a for a in self.antworten if not a.antwort]


class PollAntwort(Base):
    __tablename__ = "poll_antworten"
    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="uq_poll_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    antwort: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    poll: Mapped["Poll"] = relationship(back_populates="antworten")
    user: Mapped["User"] = relationship()  # noqa: F821
