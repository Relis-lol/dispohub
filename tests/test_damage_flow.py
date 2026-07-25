"""End-to-End: Fahrer meldet Schaden → GF übernimmt → Termin → Kosten → Dashboard."""
from tests.conftest import login


def _sum_month_costs(client):
    r = client.get("/kosten")
    assert r.status_code == 200
    return r.text


def test_full_damage_flow(client):
    # 1. Fahrer meldet Schaden (mit Datei)
    login(client, "fahrer2@dispohub.example", "fahrer123")
    r = client.post(
        "/melden",
        data={"vehicle_id": 2, "beschreibung": "Testschaden Bremse", "prioritaet": "kritisch",
              "nachricht": "bitte prüfen"},
        files={"fotos": ("bild.jpg", b"\xff\xd8\xff\xe0testjpeg", "image/jpeg")},
        follow_redirects=False,
    )
    assert r.status_code == 303

    # 2. GF sieht die neue Meldung im Posteingang
    login(client, "gf@dispohub.example", "gf123")
    inbox = client.get("/schaeden")
    assert "Testschaden Bremse" in inbox.text

    # Die neu erstellte Meldung finden (höchste ID)
    from app.db import SessionLocal
    from app.models import DamageReport, DamageStatus
    db = SessionLocal()
    report = db.query(DamageReport).filter(DamageReport.beschreibung == "Testschaden Bremse").first()
    rid = report.id
    assert report.documents  # Foto wurde gespeichert
    db.close()

    # 3. GF übernimmt
    r = client.post(f"/schaeden/{rid}/uebernehmen")
    assert r.status_code == 200

    # 4. Werkstatttermin anlegen
    r = client.post(f"/schaeden/{rid}/termin",
                    data={"titel": "Werkstatt Bremse", "faellig_am": "2026-08-01"})
    assert r.status_code == 200

    # 5. Kosten ergänzen
    r = client.post(f"/schaeden/{rid}/kosten",
                    data={"betrag": "333.33", "kategorie": "reparatur", "beschreibung": "Bremsen neu"})
    assert r.status_code == 200

    # 6. Prüfen: Status, Termin, Kosten in DB, Fahrzeug in Reparatur
    db = SessionLocal()
    report = db.get(DamageReport, rid)
    assert report.status == DamageStatus.in_reparatur
    assert len(report.appointments) == 1
    assert len(report.costs) == 1
    assert report.vehicle.status.value == "in_reparatur"
    db.close()

    # Kostenübersicht enthält den Betrag
    assert "333,33" in _sum_month_costs(client)
