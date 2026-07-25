"""Schaden-Draufsicht: Sticky-Note-Pins auf der Fahrzeugsilhouette, Fahrer-Zuordnung."""
from tests.conftest import login


def test_draufsicht_page_loads_with_existing_pin(client):
    login(client, "gf@dispohub.example", "gf123")
    # v6 (LKW) hat im Seed einen Demo-Pin
    r = client.get("/fahrzeuge/6/draufsicht")
    assert r.status_code == 200
    assert "vehicle-shape" in r.text
    assert 'class="pin' in r.text


def test_create_pin_creates_damage_with_position(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/fahrzeuge/6/schaden-pin", data={
        "beschreibung": "Lackkratzer Seitenwand", "position_x": "0.42", "position_y": "0.6",
        "schadensdatum": "2026-07-10", "ort": "Autohof", "prioritaet": "normal",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import DamageReport
    db = SessionLocal()
    d = db.query(DamageReport).filter(DamageReport.beschreibung == "Lackkratzer Seitenwand").first()
    assert d is not None
    assert abs(float(d.position_x) - 0.42) < 0.001
    assert abs(float(d.position_y) - 0.6) < 0.001
    assert str(d.schadensdatum) == "2026-07-10"
    assert d.ort == "Autohof"
    db.close()


def test_pin_out_of_range_gets_clamped(client):
    login(client, "gf@dispohub.example", "gf123")
    client.post("/fahrzeuge/6/schaden-pin", data={
        "beschreibung": "Grenzwert-Test", "position_x": "1.5", "position_y": "-0.3",
        "schadensdatum": "2026-07-10",
    })
    from app.db import SessionLocal
    from app.models import DamageReport
    db = SessionLocal()
    d = db.query(DamageReport).filter(DamageReport.beschreibung == "Grenzwert-Test").first()
    assert float(d.position_x) == 1.0
    assert float(d.position_y) == 0.0
    db.close()


def test_fahrer_cannot_access_draufsicht(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get("/fahrzeuge/6/draufsicht").status_code == 403


def test_driver_reassignment_frees_previous_vehicle(client):
    from app.db import SessionLocal
    from app.models import User

    login(client, "gf@dispohub.example", "gf123")
    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    old_vehicle_id = f1.vehicle_id
    f3 = db.query(User).filter(User.email == "fahrer3@dispohub.example").first()
    db.close()
    assert old_vehicle_id is not None

    # fahrer3 übernimmt fahrer1's Fahrzeug
    r = client.post(f"/fahrzeuge/{old_vehicle_id}/fahrer", data={"fahrer_id": str(f3.id)},
                    follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    f1_after = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    f3_after = db.query(User).filter(User.email == "fahrer3@dispohub.example").first()
    assert f1_after.vehicle_id is None
    assert f3_after.vehicle_id == old_vehicle_id
    db.close()

    # Zustand zurücksetzen, damit spätere Tests (geteilte DB, session-scope) unbeeinflusst bleiben.
    r = client.post(f"/fahrzeuge/{old_vehicle_id}/fahrer", data={"fahrer_id": str(f1.id)})
    db = SessionLocal()
    f1_reset = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    assert f1_reset.vehicle_id == old_vehicle_id
    db.close()
