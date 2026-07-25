import enum
from datetime import date, datetime

from sqlalchemy import String, Enum as SAEnum, ForeignKey, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LeaveStatus(str, enum.Enum):
    offen = "offen"
    genehmigt = "genehmigt"
    abgelehnt = "abgelehnt"


LEAVE_STATUS_LABELS = {
    LeaveStatus.offen: "Offen",
    LeaveStatus.genehmigt: "Genehmigt",
    LeaveStatus.abgelehnt: "Abgelehnt",
}

LEAVE_STATUS_TONE = {
    LeaveStatus.offen: "warn",
    LeaveStatus.genehmigt: "ok",
    LeaveStatus.abgelehnt: "bad",
}


class LeaveRequest(Base):
    """Urlaubsantrag eines Mitarbeiters; genehmigt -> wird zum Personalakten-Eintrag."""

    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    von: Mapped[date] = mapped_column(Date)
    bis: Mapped[date] = mapped_column(Date)
    notiz: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LeaveStatus] = mapped_column(SAEnum(LeaveStatus), default=LeaveStatus.offen)
    entschieden_von_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    entschieden_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
    entschieden_von: Mapped["User | None"] = relationship(foreign_keys=[entschieden_von_id])  # noqa: F821

    @property
    def tage(self) -> int:
        return (self.bis - self.von).days + 1

    @property
    def status_label(self) -> str:
        return LEAVE_STATUS_LABELS.get(self.status, self.status.value)

    @property
    def status_tone(self) -> str:
        return LEAVE_STATUS_TONE.get(self.status, "muted")
