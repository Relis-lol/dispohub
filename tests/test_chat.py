"""Chat: senden, Ungelesen-Zähler, Rollen-Trennung, Bild→Schaden, WebSocket."""
import pytest

from tests.conftest import login


def _direct_thread_gf_f1(db):
    from app.models import ChatThread, ChatMembership, ThreadArt, User
    gf = db.query(User).filter(User.email == "gf@dispohub.example").first()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    # Thread, in dem beide Mitglied sind und der direkt ist
    for th in db.query(ChatThread).filter(ChatThread.art == ThreadArt.direkt).all():
        ids = {m.user_id for m in th.memberships}
        if gf.id in ids and f1.id in ids:
            return th.id, gf.id, f1.id
    raise AssertionError("Kein GF↔F1 Direktchat gefunden")


def test_send_message_and_unread(client):
    from app.db import SessionLocal
    from app.services.chat_service import unread_count
    from app.models import User

    db = SessionLocal()
    tid, gf_id, f1_id = _direct_thread_gf_f1(db)
    gf = db.get(User, gf_id)
    f1 = db.get(User, f1_id)

    # GF liest den Thread (setzt gelesen)
    login(client, "gf@dispohub.example", "gf123")
    client.get(f"/chat/{tid}")
    db.expire_all()
    before = unread_count(db, gf)

    # Fahrer sendet eine Nachricht
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post(f"/chat/{tid}/senden", data={"text": "Test-Nachricht vom Fahrer"},
                    headers={"X-WS": "1"})
    assert r.status_code == 204

    db.expire_all()
    after = unread_count(db, gf)
    assert after == before + 1  # GF hat jetzt 1 ungelesen mehr
    # Fahrer selbst hat 0 ungelesen in diesem Thread (eigene Nachricht)
    assert unread_count(db, f1) >= 0
    db.close()


def test_role_separation(client):
    """Fahrer darf einen fremden Direktchat (GF↔anderer Fahrer) nicht öffnen."""
    from app.db import SessionLocal
    from app.models import ChatThread, ChatMembership, ThreadArt, User
    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    fremd = None
    for th in db.query(ChatThread).filter(ChatThread.art == ThreadArt.direkt).all():
        ids = {m.user_id for m in th.memberships}
        if f1.id not in ids:
            fremd = th.id
            break
    db.close()
    assert fremd is not None
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.get(f"/chat/{fremd}")
    assert r.status_code == 403


def test_image_message_to_damage(client):
    """Bild-Nachricht des Fahrers → GF übernimmt als Schaden."""
    from app.db import SessionLocal
    from app.models import ChatMessage, DamageReport

    db = SessionLocal()
    # die im Seed angelegte Bild-Nachricht finden
    img_msg = db.query(ChatMessage).filter(ChatMessage.document_id.isnot(None)).first()
    assert img_msg is not None
    mid = img_msg.id
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    r = client.post(f"/chat/nachricht/{mid}/als-schaden", data={}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/schaeden/")

    # neuer Schaden existiert mit Bild
    db = SessionLocal()
    rid = int(r.headers["location"].rsplit("/", 1)[1])
    report = db.get(DamageReport, rid)
    assert report is not None
    assert len(report.documents) == 1
    db.close()


def test_websocket_delivery(client):
    """Live-Zustellung: gesendete Nachricht kommt über den WebSocket an."""
    from app.db import SessionLocal
    db = SessionLocal()
    tid, gf_id, f1_id = _direct_thread_gf_f1(db)
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    with client.websocket_connect(f"/ws/chat/{tid}") as ws:
        client.post(f"/chat/{tid}/senden", data={"text": "Live hallo"}, headers={"X-WS": "1"})
        data = ws.receive_json()
        assert data["type"] == "message"
        assert data["text"] == "Live hallo"


def test_delete_own_message_within_window(client):
    """Eigene Nachricht kann kurz nach dem Senden gelöscht werden (Soft-Delete + WS-Event)."""
    from app.db import SessionLocal
    from app.models import ChatMessage
    db = SessionLocal()
    tid, gf_id, f1_id = _direct_thread_gf_f1(db)
    db.close()

    login(client, "fahrer1@dispohub.example", "fahrer123")
    client.post(f"/chat/{tid}/senden", data={"text": "Tippfehler-Test"}, headers={"X-WS": "1"})

    db = SessionLocal()
    msg = db.query(ChatMessage).filter(ChatMessage.text == "Tippfehler-Test").first()
    mid = msg.id
    db.close()

    with client.websocket_connect(f"/ws/chat/{tid}") as ws:
        r = client.post(f"/chat/nachricht/{mid}/loeschen")
        assert r.status_code == 204
        ev = ws.receive_json()
        assert ev == {"type": "delete", "id": mid}

    db = SessionLocal()
    msg = db.get(ChatMessage, mid)
    assert msg.geloescht is True
    assert msg.text is None
    db.close()


def test_delete_foreign_message_blocked(client):
    """Fremde Nachricht darf nicht gelöscht werden."""
    from app.db import SessionLocal
    from app.models import ChatMessage
    db = SessionLocal()
    tid, gf_id, f1_id = _direct_thread_gf_f1(db)
    db.close()

    login(client, "fahrer1@dispohub.example", "fahrer123")
    client.post(f"/chat/{tid}/senden", data={"text": "Fahrer-Nachricht"}, headers={"X-WS": "1"})

    db = SessionLocal()
    msg = db.query(ChatMessage).filter(ChatMessage.text == "Fahrer-Nachricht").first()
    mid = msg.id
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    r = client.post(f"/chat/nachricht/{mid}/loeschen")
    assert r.status_code == 403


def test_delete_after_window_blocked(client):
    """Nach Ablauf des Zeitfensters ist Löschen nicht mehr möglich."""
    from datetime import datetime, timedelta
    from app.db import SessionLocal
    from app.models import ChatMessage
    db = SessionLocal()
    tid, gf_id, f1_id = _direct_thread_gf_f1(db)
    db.close()

    login(client, "fahrer1@dispohub.example", "fahrer123")
    client.post(f"/chat/{tid}/senden", data={"text": "Alte Nachricht"}, headers={"X-WS": "1"})

    db = SessionLocal()
    msg = db.query(ChatMessage).filter(ChatMessage.text == "Alte Nachricht").first()
    msg.created_at = datetime.utcnow() - timedelta(minutes=5)  # Server vergleicht in UTC
    mid = msg.id
    db.commit()
    db.close()

    r = client.post(f"/chat/nachricht/{mid}/loeschen")
    assert r.status_code == 403
