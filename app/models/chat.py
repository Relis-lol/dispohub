import enum
from datetime import datetime

from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, DateTime, Boolean, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ThreadArt(str, enum.Enum):
    direkt = "direkt"
    gruppe = "gruppe"


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(primary_key=True)
    art: Mapped[ThreadArt] = mapped_column(SAEnum(ThreadArt), default=ThreadArt.direkt)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # nur Gruppen
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    memberships: Mapped[list["ChatMembership"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )

    def anzeige_name(self, viewer) -> str:
        """Gruppen: eigener Name. Direktchat: Name des jeweils anderen Teilnehmers."""
        if self.art == ThreadArt.gruppe:
            return self.name or "Gruppe"
        other = [m.user for m in self.memberships if m.user_id != viewer.id]
        return other[0].name if other else "Direktnachricht"


class ChatMembership(Base):
    __tablename__ = "chat_memberships"
    __table_args__ = (UniqueConstraint("thread_id", "user_id", name="uq_thread_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("chat_threads.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    last_read_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_messages.id"), nullable=True
    )

    thread: Mapped["ChatThread"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship()  # noqa: F821


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("chat_threads.id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    geloescht: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    thread: Mapped["ChatThread"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship()  # noqa: F821
    document: Mapped["Document | None"] = relationship()  # noqa: F821
