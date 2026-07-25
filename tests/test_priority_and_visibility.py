"""Dringlichkeit auf 3 Stufen + fahrzeugübergreifende Schaden-Sichtbarkeit für Fahrer."""
from tests.conftest import login


def test_priority_has_three_levels():
    from app.models.damage import Priority
    values = {p.value for p in Priority}
    assert values == {"info", "normal", "kritisch"}


def test_priority_accepted_on_submit(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post("/melden", data={"vehicle_id": 1, "beschreibung": "Prio-Test",
                                     "prioritaet": "info"}, follow_redirects=False)
    assert r.status_code == 303


def test_driver_sees_open_damage_reported_by_colleague_on_same_vehicle(client):
    """Fahrer 1 meldet Schaden an seinem Fahrzeug -> Fahrer 3 (anderes Fahrzeug) sieht ihn nicht,
    aber ein Kollege am SELBEN Fahrzeug soll ihn in 'Bereits gemeldet' sehen."""
    from app.db import SessionLocal
    from app.models import User, Vehicle

    login(client, "fahrer1@dispohub.example", "fahrer123")
    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    vehicle_id = f1.vehicle_id
    db.close()
    assert vehicle_id is not None

    client.post("/melden", data={"vehicle_id": vehicle_id,
                                 "beschreibung": "Kollegen-Sichtbarkeitstest",
                                 "prioritaet": "normal"})

    # Schichtübergabe simulieren: f3 übernimmt dasselbe Fahrzeug von f1.
    # (Datenmodell aktuell 1 Fahrer : 1 Fahrzeug — echte Mehrfahrer-/Springer-Unterstützung
    # ist ein Backlog-Punkt, siehe BACKLOG.md.)
    db = SessionLocal()
    f1_again = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    f1_again.vehicle_id = None
    f3 = db.query(User).filter(User.email == "fahrer3@dispohub.example").first()
    f3.vehicle_id = vehicle_id
    db.commit()
    db.close()

    login(client, "fahrer3@dispohub.example", "fahrer123")
    page = client.get("/melden").text
    assert "Kollegen-Sichtbarkeitstest" in page
    assert "Bereits gemeldet an deinem Fahrzeug" in page
