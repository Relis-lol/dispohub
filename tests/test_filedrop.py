"""Filedrop für den Steuerberater: rohe Belege hochladen, abholen, löschen."""
import io

from tests.conftest import login


def test_beleg_hochladen_und_anzeigen(client):
    login(client, "buero@dispohub.example", "buero123")
    pdf = io.BytesIO(b"%PDF-1.4 test")
    r = client.post("/export/beleg", data={"notiz": "Tankquittung Mai"},
                    files={"datei": ("quittung.pdf", pdf, "application/pdf")},
                    follow_redirects=False)
    assert r.status_code == 303

    r = client.get("/export")
    assert "quittung.pdf" in r.text and "Tankquittung Mai" in r.text


def test_beleg_abholen_verschiebt_in_abgeholt(client):
    login(client, "buero@dispohub.example", "buero123")
    pdf = io.BytesIO(b"%PDF-1.4 test2")
    client.post("/export/beleg", data={"notiz": "Abzuholender Beleg"},
               files={"datei": ("beleg2.pdf", pdf, "application/pdf")})

    from app.db import SessionLocal
    from app.models import Receipt
    db = SessionLocal()
    beleg = (db.query(Receipt).filter(Receipt.notiz == "Abzuholender Beleg")
             .order_by(Receipt.id.desc()).first())
    bid = beleg.id
    db.close()

    r = client.post(f"/export/beleg/{bid}/abgeholt", follow_redirects=False)
    assert r.status_code == 303

    from app.models import Receipt as R
    db = SessionLocal()
    assert db.get(R, bid).abgeholt is True
    db.close()

    page = client.get("/export").text
    # Nicht mehr in der offenen Liste, aber im "Bereits abgeholt"-Abschnitt
    assert "Bereits abgeholte Belege" in page


def test_beleg_loeschen(client):
    login(client, "buero@dispohub.example", "buero123")
    pdf = io.BytesIO(b"%PDF-1.4 test3")
    client.post("/export/beleg", data={"notiz": "Zu loeschen"},
               files={"datei": ("weg.pdf", pdf, "application/pdf")})

    from app.db import SessionLocal
    from app.models import Receipt
    db = SessionLocal()
    beleg = (db.query(Receipt).filter(Receipt.notiz == "Zu loeschen")
             .order_by(Receipt.id.desc()).first())
    bid = beleg.id
    db.close()

    r = client.post(f"/export/beleg/{bid}/loeschen", follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    assert db.get(Receipt, bid) is None
    db.close()


def test_fahrer_hat_keinen_zugriff(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get("/export").status_code == 403
