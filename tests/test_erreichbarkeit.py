"""Anrufbereitschaft: Ampel je Ansprechpartner, Fahrer-Ansicht /kontakte."""
from datetime import time, datetime

from tests.conftest import login


def test_fahrer_sieht_kontakte_mit_ampel(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.get("/kontakte")
    assert r.status_code == 200
    assert "Sabine Groß" in r.text  # GF
    assert "Petra Klein" in r.text  # Büro


def test_gf_setzt_rot_und_fahrer_bekommt_warnung_im_link(client):
    from app.db import SessionLocal
    from app.models import User

    login(client, "gf@dispohub.example", "gf123")
    db = SessionLocal()
    buero_id = db.query(User).filter(User.email == "buero@dispohub.example").first().id
    db.close()

    r = client.post("/einstellungen/erreichbarkeit", data={
        "kontakt_id": buero_id, "status": "rot",
    }, follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    buero = db.get(User, buero_id)
    assert buero.erreichbarkeit.value == "rot"
    assert buero.ist_erreichbar is False
    db.close()

    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.get("/kontakte")
    assert "confirm(" in r.text  # Rückfrage vor dem Anruf eingebaut

    # zurücksetzen
    login(client, "gf@dispohub.example", "gf123")
    client.post("/einstellungen/erreichbarkeit", data={"kontakt_id": buero_id, "status": "gruen"})


def test_zeitplan_ampel_je_uhrzeit(client):
    from app.db import SessionLocal
    from app.models import User

    login(client, "gf@dispohub.example", "gf123")
    db = SessionLocal()
    it_id = db.query(User).filter(User.email == "it@dispohub.example").first().id
    db.close()
    # IT hat keine Telefonnummer im Seed -> stattdessen buero testen wäre doppelt;
    # wir testen die Modell-Logik direkt statt über die Ansprechpartner-Liste.

    db = SessionLocal()
    buero = db.query(User).filter(User.email == "buero@dispohub.example").first()
    buero.erreichbarkeit = __import__("app.models", fromlist=["Erreichbarkeit"]).Erreichbarkeit.zeitplan
    jetzt = datetime.now().time()
    # Fenster genau um "jetzt" herum setzen -> muss erreichbar sein
    buero.erreichbar_von = time((jetzt.hour - 1) % 24, 0)
    buero.erreichbar_bis = time((jetzt.hour + 1) % 24, 59)
    db.commit()
    assert buero.ist_erreichbar is True

    # Fenster weit weg von "jetzt" -> nicht erreichbar (außer Grenzfall Mitternacht-Wrap, daher großzügig)
    buero.erreichbar_von = time((jetzt.hour + 2) % 24, 0)
    buero.erreichbar_bis = time((jetzt.hour + 2) % 24, 1)
    db.commit()
    assert buero.ist_erreichbar is False

    # aufräumen
    from app.models import Erreichbarkeit
    buero.erreichbarkeit = Erreichbarkeit.gruen
    buero.erreichbar_von = None
    buero.erreichbar_bis = None
    db.commit()
    db.close()


def test_nur_gf_admin_koennen_erreichbarkeit_aendern(client):
    login(client, "buero@dispohub.example", "buero123")
    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    buero_id = db.query(User).filter(User.email == "buero@dispohub.example").first().id
    db.close()
    r = client.post("/einstellungen/erreichbarkeit", data={"kontakt_id": buero_id, "status": "rot"})
    assert r.status_code == 403
