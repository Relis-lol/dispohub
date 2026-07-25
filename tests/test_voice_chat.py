"""Sprachnachrichten im Chat: Audio-Upload wird als Player-Nachricht gespeichert."""
import io

from tests.conftest import login


def _thread_id(client):
    """Erster Chat-Thread des eingeloggten Fahrers."""
    from app.db import SessionLocal
    from app.models import ChatMembership, ThreadArt, User
    db = SessionLocal()
    try:
        f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
        # Einzelchat wählen — in Durchsage-Gruppen dürfen Fahrer nicht schreiben
        for m in db.query(ChatMembership).filter(ChatMembership.user_id == f1.id).all():
            if m.thread.art == ThreadArt.direkt:
                return m.thread_id
        raise AssertionError("Kein Einzelchat für fahrer1 im Seed")
    finally:
        db.close()


def test_sprachnachricht_senden(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    tid = _thread_id(client)
    fake_audio = io.BytesIO(b"\x1aE\xdf\xa3" + b"\x00" * 500)  # WebM-Magic + Füllung
    r = client.post(f"/chat/{tid}/senden",
                    data={"text": ""},
                    files={"audio": ("sprachnachricht.webm", fake_audio, "audio/webm")},
                    headers={"X-WS": "1"})
    assert r.status_code == 204

    from app.db import SessionLocal
    from app.models import ChatMessage, Document
    db = SessionLocal()
    msg = (db.query(ChatMessage).filter(ChatMessage.thread_id == tid)
           .order_by(ChatMessage.id.desc()).first())
    assert msg.document_id is not None
    doc = db.get(Document, msg.document_id)
    assert doc.typ == "audio"
    assert doc.pfad.endswith(".webm")
    db.close()

    # Im Thread erscheint ein Audio-Player statt eines Bildes
    r = client.get(f"/chat/{tid}")
    assert "<audio" in r.text and doc.pfad in r.text


def test_unerlaubte_audio_endung_wird_ignoriert(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    tid = _thread_id(client)
    r = client.post(f"/chat/{tid}/senden",
                    data={"text": ""},
                    files={"audio": ("boese.exe", io.BytesIO(b"MZ..."), "application/octet-stream")},
                    headers={"X-WS": "1"})
    # Kein Text, kein gültiger Anhang -> nichts gesendet
    assert r.status_code == 204

    from app.db import SessionLocal
    from app.models import ChatMessage
    db = SessionLocal()
    msg = (db.query(ChatMessage).filter(ChatMessage.thread_id == tid)
           .order_by(ChatMessage.id.desc()).first())
    # Letzte Nachricht ist weiterhin die gültige Sprachnachricht aus dem Test davor
    assert msg is None or (msg.document and msg.document.typ == "audio") or msg.text
    db.close()
