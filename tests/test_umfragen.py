"""Umfragen: Büro fragt, Fahrer antworten Ja/Nein im Aufgaben-Tab."""
from tests.conftest import login


def test_buero_erstellt_umfrage(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.post("/umfragen", data={"frage": "Samstag Sonderschicht — wer kann?"},
                    follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/umfragen")
    assert "Samstag Sonderschicht" in r.text and "läuft" in r.text


def test_fahrer_sieht_und_beantwortet(client):
    from app.db import SessionLocal
    from app.models import Poll, PollAntwort, User

    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.get("/aufgaben")
    assert "Samstag Sonderschicht" in r.text

    db = SessionLocal()
    poll = db.query(Poll).filter(Poll.frage.like("Samstag%")).first()
    pid = poll.id
    db.close()

    r = client.post(f"/umfragen/{pid}/antwort", data={"antwort": "ja"}, follow_redirects=False)
    assert r.status_code == 303

    # Nach Antwort verschwindet die Frage aus dem Aufgaben-Tab
    assert "Samstag Sonderschicht" not in client.get("/aufgaben").text
    # Doppelt antworten geht nicht
    assert client.post(f"/umfragen/{pid}/antwort", data={"antwort": "nein"}).status_code == 400

    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    a = (db.query(PollAntwort)
         .filter(PollAntwort.poll_id == pid, PollAntwort.user_id == f1.id).first())
    assert a is not None and a.antwort is True
    db.close()


def test_ergebnis_und_schliessen(client):
    from app.db import SessionLocal
    from app.models import Poll
    db = SessionLocal()
    pid = db.query(Poll).filter(Poll.frage.like("Samstag%")).first().id
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    r = client.get("/umfragen")
    assert "Kemal Yıldız" in r.text  # Ja-Stimme namentlich sichtbar

    r = client.post(f"/umfragen/{pid}/schliessen", follow_redirects=False)
    assert r.status_code == 303
    assert "geschlossen" in client.get("/umfragen").text

    # Geschlossene Umfrage nimmt keine Antworten mehr an
    login(client, "fahrer2@dispohub.example", "fahrer123")
    assert client.post(f"/umfragen/{pid}/antwort", data={"antwort": "ja"}).status_code == 404


def test_fahrer_hat_keinen_zugriff_auf_verwaltungsseite(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get("/umfragen").status_code == 403
