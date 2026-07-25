"""Aufgabenliste: Büro erstellt, Fahrer sieht eigene/Fahrzeug-/allgemeine Aufgaben und hakt ab."""
from tests.conftest import login


def test_office_creates_task_assigned_to_driver(client):
    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    f2 = db.query(User).filter(User.email == "fahrer2@dispohub.example").first()
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/aufgaben", data={
        "titel": "Ölstand prüfen", "zugewiesen_user_id": str(f2.id), "faellig_am": "2026-07-20",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.models import Task
    db = SessionLocal()
    t = db.query(Task).filter(Task.titel == "Ölstand prüfen").first()
    assert t is not None
    assert t.zugewiesen_user_id == f2.id
    db.close()

    # Fahrer2 sieht sie, Fahrer3 (nicht zugewiesen, anderes Fahrzeug) nicht
    login(client, "fahrer2@dispohub.example", "fahrer123")
    assert "Ölstand prüfen" in client.get("/aufgaben").text

    login(client, "fahrer3@dispohub.example", "fahrer123")
    assert "Ölstand prüfen" not in client.get("/aufgaben").text


def test_general_task_visible_to_all_drivers(client):
    login(client, "gf@dispohub.example", "gf123")
    client.post("/aufgaben", data={"titel": "Verbandskasten kontrollieren"})

    for email in ["fahrer1@dispohub.example", "fahrer2@dispohub.example", "fahrer3@dispohub.example"]:
        login(client, email, "fahrer123")
        assert "Verbandskasten kontrollieren" in client.get("/aufgaben").text


def test_driver_can_complete_own_task_but_not_foreign(client):
    from app.db import SessionLocal
    from app.models import User, Task
    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    client.post("/aufgaben", data={"titel": "Reifendruck-Test", "zugewiesen_user_id": str(f1.id)})

    db = SessionLocal()
    task = db.query(Task).filter(Task.titel == "Reifendruck-Test").first()
    tid = task.id
    db.close()

    # Fahrer2 darf fremde Aufgabe nicht abhaken
    login(client, "fahrer2@dispohub.example", "fahrer123")
    r = client.post(f"/aufgaben/{tid}/erledigt")
    assert r.status_code == 403

    # Fahrer1 (zugewiesen) darf
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post(f"/aufgaben/{tid}/erledigt", follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    task = db.get(Task, tid)
    assert task.status.value == "erledigt"
    assert task.erledigt_am is not None
    db.close()


def test_it_role_blocked_from_tasks(client):
    login(client, "it@dispohub.example", "it123")
    assert client.get("/aufgaben").status_code == 403


def test_dashboard_shows_open_task_count(client):
    login(client, "gf@dispohub.example", "gf123")
    assert "Offene Aufgaben" in client.get("/").text
