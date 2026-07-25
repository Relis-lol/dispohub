"""Foto an der Fahrzeugakte hinterlegen."""
from tests.conftest import login


def test_upload_vehicle_photo(client):
    login(client, "gf@dispohub.example", "gf123")
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de00000010494441545847636060606000000005000122a3e0a70000000049454e44ae426082"
    )
    r = client.post("/fahrzeuge/1/foto", files={"foto": ("fahrzeug.png", png, "image/png")},
                    follow_redirects=False)
    assert r.status_code == 303

    page = client.get("/fahrzeuge/1").text
    assert "Fahrzeugfoto" in page

    from app.db import SessionLocal
    from app.models import Document
    db = SessionLocal()
    doc = db.query(Document).filter(Document.vehicle_id == 1).first()
    assert doc is not None
    db.close()
