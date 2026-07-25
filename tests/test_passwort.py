"""Zufälliges Start-Passwort bei Mitarbeiter-Anlage + Passwort-Selbständerung."""
import re

from tests.conftest import login


def test_neuer_mitarbeiter_bekommt_zufallspasswort(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/verwaltung/mitarbeiter", data={
        "name": "Test Fahrer", "email": "testfahrer@dispohub.example", "rolle": "fahrer",
    })
    assert r.status_code == 200
    matches = re.findall(r'font-family:monospace[^>]*>([^<]+)</span>', r.text)
    assert matches, "kein generiertes Passwort im HTML gefunden"
    passwort = matches[0]
    assert len(passwort) == 8

    # Login mit dem generierten Passwort funktioniert und zwingt zur Änderung
    r2 = client.post("/login", data={"email": "testfahrer@dispohub.example", "password": passwort},
                     follow_redirects=False)
    assert r2.status_code == 303
    assert r2.headers["location"].startswith("/passwort")


def test_pflicht_passwort_aenderung_setzt_flag_zurueck(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/verwaltung/mitarbeiter", data={
        "name": "Zweiter Test", "email": "test2@dispohub.example", "rolle": "fahrer",
    })
    matches = re.findall(r'font-family:monospace[^>]*>([^<]+)</span>', r.text)
    passwort = matches[0]

    login(client, "test2@dispohub.example", passwort)
    r = client.post("/passwort", data={
        "altes_passwort": passwort, "neues_passwort": "neuesPW9",
        "neues_passwort_wiederholen": "neuesPW9",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    u = db.query(User).filter(User.email == "test2@dispohub.example").first()
    assert u.passwort_aendern_erforderlich is False
    db.close()

    # Neuer Login: kein Zwang mehr, direkt zum Chat (Fahrer-Startseite)
    r = client.post("/login", data={"email": "test2@dispohub.example", "password": "neuesPW9"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/chat"


def test_falsches_altes_passwort_wird_abgelehnt(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post("/passwort", data={
        "altes_passwort": "falsch", "neues_passwort": "neuNeu1", "neues_passwort_wiederholen": "neuNeu1",
    })
    assert r.status_code == 400
    assert "falsch" in r.text.lower()


def test_passwort_wiederholung_muss_uebereinstimmen(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post("/passwort", data={
        "altes_passwort": "fahrer123", "neues_passwort": "abcdefg1", "neues_passwort_wiederholen": "abweichend",
    })
    assert r.status_code == 400


def test_seite_ohne_login_nicht_erreichbar(client):
    r = client.get("/passwort", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
