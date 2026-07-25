"""'Alle'/'Alle Fahrer' sind Durchsagen (nur GF/Büro senden); Kollegen-Chat ist frei für Fahrer."""
from tests.conftest import login


def _thread_id_by_name(name: str) -> int:
    from app.db import SessionLocal
    from app.models import ChatThread
    db = SessionLocal()
    th = db.query(ChatThread).filter(ChatThread.name == name).first()
    tid = th.id
    db.close()
    return tid


def test_driver_cannot_post_in_alle(client):
    tid = _thread_id_by_name("Alle")
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post(f"/chat/{tid}/senden", data={"text": "Darf ich das?"}, headers={"X-WS": "1"})
    assert r.status_code == 403


def test_driver_cannot_post_in_alle_fahrer(client):
    tid = _thread_id_by_name("Alle Fahrer")
    login(client, "fahrer2@dispohub.example", "fahrer123")
    r = client.post(f"/chat/{tid}/senden", data={"text": "Test"}, headers={"X-WS": "1"})
    assert r.status_code == 403


def test_gf_can_post_in_alle(client):
    tid = _thread_id_by_name("Alle")
    login(client, "gf@dispohub.example", "gf123")
    r = client.post(f"/chat/{tid}/senden", data={"text": "Durchsage"}, headers={"X-WS": "1"})
    assert r.status_code == 204


def test_driver_can_post_freely_in_kollegen_chat(client):
    tid = _thread_id_by_name("Kollegen-Chat")
    login(client, "fahrer2@dispohub.example", "fahrer123")
    r = client.post(f"/chat/{tid}/senden", data={"text": "Komme heute 2h später"}, headers={"X-WS": "1"})
    assert r.status_code == 204


def test_kollegen_chat_shows_vehicle_per_member(client):
    tid = _thread_id_by_name("Kollegen-Chat")
    login(client, "fahrer1@dispohub.example", "fahrer123")
    page = client.get(f"/chat/{tid}").text
    assert "member-chip" in page
    # mindestens ein Mitglied zeigt sein zugeordnetes Fahrzeug
    assert "B-TR" in page


def test_readonly_note_shown_for_driver_in_alle_fahrer(client):
    tid = _thread_id_by_name("Alle Fahrer")
    login(client, "fahrer1@dispohub.example", "fahrer123")
    page = client.get(f"/chat/{tid}").text
    assert "Nur Lesezugriff" in page


def test_driver_is_not_member_of_alle(client):
    """'Alle' ist rein intern für GF/Büro - Fahrer sehen den Kanal gar nicht erst."""
    tid = _thread_id_by_name("Alle")
    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get(f"/chat/{tid}").status_code == 403

    chat_list = client.get("/chat").text
    assert f'/chat/{tid}"' not in chat_list  # kein Link zum "Alle"-Thread in der Liste
    assert "Alle Fahrer" in chat_list  # der Durchsage-Kanal für Fahrer bleibt sichtbar


def test_gf_still_sees_alle(client):
    tid = _thread_id_by_name("Alle")
    login(client, "gf@dispohub.example", "gf123")
    assert client.get(f"/chat/{tid}").status_code == 200
