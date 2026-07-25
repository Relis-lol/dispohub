"""Parkplatz melden (GPS + Foto) und Anzeige in der Fahrzeugakte mit Karte."""
from tests.conftest import login


def test_driver_can_report_parking_spot(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.post("/parkplatz", data={
        "lat": "52.520000", "lng": "13.410000", "notiz": "Vor dem Kundengebäude",
    }, follow_redirects=False)
    assert r.status_code == 303
    assert "parkplatz=1" in r.headers["location"]

    from app.db import SessionLocal
    from app.models import ParkingSpot, User
    db = SessionLocal()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    spot = (db.query(ParkingSpot).filter(ParkingSpot.reporter_id == f1.id)
            .order_by(ParkingSpot.id.desc()).first())
    assert spot is not None
    assert abs(float(spot.lat) - 52.52) < 0.0001
    assert spot.vehicle_id == f1.vehicle_id
    db.close()


def test_driver_without_vehicle_cannot_report_parking(client):
    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    f3 = db.query(User).filter(User.email == "fahrer3@dispohub.example").first()
    original_vehicle = f3.vehicle_id
    f3.vehicle_id = None
    db.commit()
    db.close()

    login(client, "fahrer3@dispohub.example", "fahrer123")
    r = client.post("/parkplatz", data={"lat": "1.0", "lng": "1.0"})
    assert r.status_code == 400

    # zurücksetzen
    db = SessionLocal()
    f3 = db.query(User).filter(User.email == "fahrer3@dispohub.example").first()
    f3.vehicle_id = original_vehicle
    db.commit()
    db.close()


def test_vehicle_detail_shows_last_known_location(client):
    """Prüft gegen den tatsächlich aktuellsten Standort (andere Tests können
    zwischenzeitlich neuere ParkingSpots für Fahrzeug 1 angelegt haben)."""
    import re
    from app.db import SessionLocal
    from app.models import ParkingSpot
    db = SessionLocal()
    latest = (db.query(ParkingSpot).filter(ParkingSpot.vehicle_id == 1)
              .order_by(ParkingSpot.created_at.desc()).first())
    lat, lng = float(latest.lat), float(latest.lng)
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    page = client.get("/fahrzeuge/1").text
    assert "Zuletzt gesehen" in page
    assert "In Google Maps öffnen" in page
    assert "leaflet.js" in page

    m = re.search(r"google\.com/maps\?q=([\d.\-]+),([\d.\-]+)", page)
    assert m is not None
    assert abs(float(m.group(1)) - lat) < 0.001
    assert abs(float(m.group(2)) - lng) < 0.001


def test_parking_photo_upload_end_to_end(client):
    login(client, "fahrer2@dispohub.example", "fahrer123")
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de00000010494441545847636060606000000005000122a3e0a70000000049454e44ae426082"
    )
    r = client.post("/parkplatz", data={"lat": "52.5", "lng": "13.4"},
                    files={"foto": ("park.png", png, "image/png")}, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import ParkingSpot, User, Document
    db = SessionLocal()
    f2 = db.query(User).filter(User.email == "fahrer2@dispohub.example").first()
    spot = (db.query(ParkingSpot).filter(ParkingSpot.reporter_id == f2.id)
            .order_by(ParkingSpot.id.desc()).first())
    assert spot.foto_id is not None
    doc = db.get(Document, spot.foto_id)
    assert doc.pfad.startswith("/static/uploads/")
    db.close()


def test_melden_page_has_parkplatz_section_for_assigned_driver(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    page = client.get("/melden").text
    assert "Parkplatz melden" in page
    assert "Standort erfassen" in page
