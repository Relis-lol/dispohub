"""Bearbeiten von Mitarbeiter-/Fahrzeug-Stammdaten und Passwort-Reset im UI."""
from tests.conftest import login


def _user_id(email):
    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first().id
    finally:
        db.close()


def test_mitarbeiter_stammdaten_bearbeiten(client):
    login(client, "buero@dispohub.example", "buero123")
    mid = _user_id("fahrer3@dispohub.example")
    r = client.post(f"/mitarbeiter/{mid}/stammdaten", data={
        "name": "Ahmed Hassan", "email": "fahrer3@dispohub.example",
        "telefon": "+49 151 9998877", "geburtstag": "1988-04-12", "status": "aktiv",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    m = db.get(User, mid)
    assert m.phone == "+49 151 9998877"
    assert m.geburtstag.isoformat() == "1988-04-12"
    db.close()


def test_email_kollision_wird_abgelehnt(client):
    login(client, "buero@dispohub.example", "buero123")
    mid = _user_id("fahrer3@dispohub.example")
    r = client.post(f"/mitarbeiter/{mid}/stammdaten", data={
        "name": "Ahmed Hassan", "email": "fahrer1@dispohub.example", "status": "aktiv",
    })
    assert r.status_code == 400


def test_rollenwechsel_nur_durch_gf(client):
    mid = _user_id("fahrer3@dispohub.example")
    # Büro darf Rolle NICHT ändern (Feld wird ignoriert)
    login(client, "buero@dispohub.example", "buero123")
    client.post(f"/mitarbeiter/{mid}/stammdaten", data={
        "name": "Ahmed Hassan", "email": "fahrer3@dispohub.example", "status": "aktiv",
        "rolle": "buero",
    })
    from app.db import SessionLocal
    from app.models import User, Role
    db = SessionLocal()
    assert db.get(User, mid).role == Role.fahrer
    db.close()

    # GF darf
    login(client, "gf@dispohub.example", "gf123")
    client.post(f"/mitarbeiter/{mid}/stammdaten", data={
        "name": "Ahmed Hassan", "email": "fahrer3@dispohub.example", "status": "aktiv",
        "rolle": "buero",
    })
    db = SessionLocal()
    assert db.get(User, mid).role == Role.buero
    # zurücksetzen
    db.get(User, mid).role = Role.fahrer
    db.commit()
    db.close()


def test_passwort_reset_nur_gf(client):
    mid = _user_id("fahrer3@dispohub.example")
    login(client, "buero@dispohub.example", "buero123")
    r = client.post(f"/mitarbeiter/{mid}/passwort", data={"neues_passwort": "geheim99"})
    assert r.status_code == 403

    login(client, "gf@dispohub.example", "gf123")
    r = client.post(f"/mitarbeiter/{mid}/passwort", data={"neues_passwort": "geheim99"},
                    follow_redirects=False)
    assert r.status_code == 303
    # Neues Passwort funktioniert
    assert login(client, "fahrer3@dispohub.example", "geheim99").status_code == 303
    # zurücksetzen für andere Tests
    login(client, "gf@dispohub.example", "gf123")
    client.post(f"/mitarbeiter/{mid}/passwort", data={"neues_passwort": "fahrer123"})


def test_fahrzeug_stammdaten_bearbeiten(client):
    from app.db import SessionLocal
    from app.models import Vehicle
    login(client, "buero@dispohub.example", "buero123")
    db = SessionLocal()
    v = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 9001").first()
    vid = v.id
    db.close()

    r = client.post(f"/fahrzeuge/{vid}/stammdaten", data={
        "kennzeichen": "b-tr 9001", "hersteller": "VW", "modell": "Passat Variant",
        "km_stand": "77000", "status": "werkstatt_geplant",
        "hu_faellig": "2027-03-01", "monatliche_fixkosten": "310,50",
    }, follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    v = db.get(Vehicle, vid)
    assert v.kennzeichen == "B-TR 9001"
    assert v.km_stand == 77000
    assert v.status.value == "werkstatt_geplant"
    assert v.hu_faellig.isoformat() == "2027-03-01"
    assert abs(float(v.monatliche_fixkosten) - 310.50) < 0.01
    db.close()
