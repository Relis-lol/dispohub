"""Ungelesen-Zähler für den Chat (von Router, Dashboard und Navigation genutzt)."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ChatMembership, ChatMessage


def unread_for_thread(db: Session, m: ChatMembership, user) -> int:
    q = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.thread_id == m.thread_id, ChatMessage.sender_id != user.id
    )
    if m.last_read_message_id:
        q = q.filter(ChatMessage.id > m.last_read_message_id)
    return q.scalar() or 0


def unread_count(db: Session, user) -> int:
    total = 0
    for m in db.query(ChatMembership).filter(ChatMembership.user_id == user.id).all():
        total += unread_for_thread(db, m, user)
    return total
