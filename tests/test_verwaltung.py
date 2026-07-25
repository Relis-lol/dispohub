"""Admin-Menü: Anlegen von Mitarbeitern/Fahrzeugen, 30-Tage-Papierkorb."""
from datetime import datetime, timedelta

from tests.conftest import login


def test_nur_gf_und_admin_haben_zugriff(client):
    login(client, "buero@dispohub.example", "buero123")
    assert client.get("/verwaltung").status_code == 403
    login(client, "gf@dispohub.example", "gf123")
    assert client.get("/verwaltung").status_code == 200


def test_mitarbeiter_anlegen_und_anmelden(client):
    # Zufalls-Passwort-Ausgabe + erzwungene Passwort-Änderung: siehe tests/test_passwort.py
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/verwaltung/mitarbeiter", data={
        "name": "Neuer Fahrer", "email": "neu@dispohub.example", "rolle": "fahrer",
        "telefon": "+49 151 0001122",
    })
    assert r.status_code == 200
    assert "neu@dispohub.example" in r.text

    # Doppelte E-Mail wird abgelehnt
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/verwaltung/mitarbeiter", data={
        "name": "Doppelt", "email": "neu@dispohub.example", "rolle": "fahrer",
    })
    assert r.status_code == 400


def test_fahrzeug_anlegen(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/verwaltung/fahrzeug", data={
        "kennzeichen": "b-neu 99", "hersteller": "MAN", "modell": "TGE",
        "typ": "sprinter", "km_stand": "1500",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import Vehicle
    db = SessionLocal()
    v = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-NEU 99").first()
    assert v is not None and v.km_stand == 1500
    db.close()


def test_papierkorb_loeschen_und_wiederherstellen(client):
    from app.db import SessionLocal
    from app.models import User
    login(client, "gf@dispohub.example", "gf123")

    db = SessionLocal()
    opfer = db.query(User).filter(User.email == "neu@dispohub.example").first()
    mid = opfer.id
    db.close()

    # Löschen -> Papierkorb, Login gesperrt, nicht mehr in Mitarbeiterliste
    r = client.post(f"/verwaltung/mitarbeiter/{mid}/loeschen", follow_redirects=False)
    assert r.status_code == 303
    db = SessionLocal()
    assert db.get(User, mid).geloescht_am is not None
    db.close()
    assert "Neuer Fahrer" not in client.get("/mitarbeiter").text

    fahrer_client_r = client.post("/login", data={"email": "neu@dispohub.example", "password": "start123"},
                                  follow_redirects=False)
    assert fahrer_client_r.status_code == 401

    # Papierkorb zeigt den Eintrag, Wiederherstellen macht alles rückgängig
    login(client, "gf@dispohub.example", "gf123")
    assert "Neuer Fahrer" in client.get("/verwaltung").text
    r = client.post(f"/verwaltung/mitarbeiter/{mid}/wiederherstellen", follow_redirects=False)
    assert r.status_code == 303
    db = SessionLocal()
    assert db.get(User, mid).geloescht_am is None
    db.close()


def test_eigenes_konto_nicht_loeschbar(client):
    from app.db import SessionLocal
    from app.models import User
    login(client, "gf@dispohub.example", "gf123")
    db = SessionLocal()
    gf_id = db.query(User).filter(User.email == "gf@dispohub.example").first().id
    db.close()
    r = client.post(f"/verwaltung/mitarbeiter/{gf_id}/loeschen")
    assert r.status_code == 400


def test_purge_nach_30_tagen(client):
    from app.db import SessionLocal
    from app.models import User, Role
    from app.security import hash_password
    from app.services.papierkorb import purge_abgelaufene

    db = SessionLocal()
    alt = User(name="Uralt Eintrag", email="uralt@dispohub.example", role=Role.fahrer,
               password_hash=hash_password("x" * 8),
               geloescht_am=datetime.now() - timedelta(days=31))
    db.add(alt)
    db.commit()
    uid = alt.id

    entfernt = purge_abgelaufene(db)
    assert entfernt >= 1
    assert db.get(User, uid) is None
    db.close()


def test_fahrzeug_loeschen_gibt_fahrer_frei(client):
    from app.db import SessionLocal
    from app.models import User, Vehicle
    login(client, "gf@dispohub.example", "gf123")

    # Zuordnung explizit herstellen (unabhängig von anderen Tests)
    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    vid = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 1201").first().id
    f1.vehicle_id = vid
    db.commit()
    db.close()

    r = client.post(f"/verwaltung/fahrzeug/{vid}/loeschen", follow_redirects=False)
    assert r.status_code == 303
    db = SessionLocal()
    assert db.query(User).filter(User.email == "fahrer1@dispohub.example").first().vehicle_id is None
    assert db.get(Vehicle, vid).geloescht_am is not None
    db.close()

    # Wiederherstellen (damit andere Tests das Fahrzeug weiter sehen)
    client.post(f"/verwaltung/fahrzeug/{vid}/wiederherstellen")
    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    f1.vehicle_id = vid
    db.commit()
    db.close()
