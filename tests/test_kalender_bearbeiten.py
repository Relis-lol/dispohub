"""Kalender: Termine direkt eintragen und als erledigt abhaken."""
from datetime import date, timedelta

from tests.conftest import login


def test_termin_anlegen_und_im_grid_sichtbar(client):
    login(client, "buero@dispohub.example", "buero123")
    from app.db import SessionLocal
    from app.models import Vehicle
    db = SessionLocal()
    vid = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 1201").first().id
    db.close()

    ziel = date.today() + timedelta(days=5)
    r = client.post("/kalender/termin", data={
        "titel": "TÜV-Vorbereitung", "faellig_am": ziel.isoformat(),
        "vehicle_id": str(vid), "quelle": "pruefung",
    }, follow_redirects=False)
    assert r.status_code == 303

    r = client.get(f"/kalender?monat={ziel.strftime('%Y-%m')}")
    assert "TÜV-Vorbereitung" in r.text


def test_termin_ohne_titel_abgelehnt(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.post("/kalender/termin", data={"titel": "  ", "faellig_am": date.today().isoformat()})
    assert r.status_code == 400


def test_termin_erledigt_abhaken(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.post("/kalender/termin", data={
        "titel": "Abzuhakender Termin", "faellig_am": date.today().isoformat(),
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import Appointment, AppointmentStatus
    db = SessionLocal()
    termin = (db.query(Appointment).filter(Appointment.titel == "Abzuhakender Termin")
              .order_by(Appointment.id.desc()).first())
    tid = termin.id
    db.close()

    assert "Abzuhakender Termin" in client.get("/kalender").text
    r = client.post(f"/kalender/termin/{tid}/erledigt", follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    assert db.get(Appointment, tid).status == AppointmentStatus.erledigt
    db.close()
    assert "Abzuhakender Termin" not in client.get("/kalender").text


def test_fahrer_kein_zugriff_auf_kalender_bearbeiten(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post("/kalender/termin", data={"titel": "x", "faellig_am": date.today().isoformat()})
    assert r.status_code == 403
