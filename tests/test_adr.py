"""ADR-/Sicherheitsmittel: Ablaufdatum, Dashboard-Hinweis, Checkliste an Fahrer."""
from tests.conftest import login


def test_add_adr_item(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/fahrzeuge/1/adr", data={"bezeichnung": "Warnweste", "ablauf_am": "2027-01-01"},
                    follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/fahrzeuge/1").text
    assert "Warnweste" in page


def test_dashboard_shows_adr_reminder(client):
    login(client, "gf@dispohub.example", "gf123")
    assert "ADR-Mittel fällig" in client.get("/").text


def test_checklist_creates_task_for_driver(client):
    from app.db import SessionLocal
    from app.models import User, Vehicle, Task

    login(client, "gf@dispohub.example", "gf123")
    db = SessionLocal()
    v1 = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 1201").first()
    vid = v1.id
    db.close()

    r = client.post(f"/fahrzeuge/{vid}/adr-checkliste", follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    task = db.query(Task).filter(Task.vehicle_id == vid,
                                 Task.titel.like("ADR-Ausrüstung prüfen%")).first()
    assert task is not None
    assert "Feuerlöscher" in task.beschreibung
    db.close()
