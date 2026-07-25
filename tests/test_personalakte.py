"""Personalakte: Detailseite, Urlaubs-/Krank-/Stunden-Einträge, Dokumente, Notizen."""
import io

from tests.conftest import login


def _fahrer1_id():
    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == "fahrer1@dispohub.example").first().id
    finally:
        db.close()


def test_detail_zeigt_personalakte(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.get(f"/mitarbeiter/{_fahrer1_id()}")
    assert r.status_code == 200
    assert "Kemal Yıldız" in r.text
    assert "Resturlaub" in r.text
    assert "Fahrerkarte" in r.text
    assert "Sommerurlaub" in r.text  # Seed-Eintrag sichtbar


def test_fahrer_hat_keinen_zugriff(client):
    login(client, "fahrer2@dispohub.example", "fahrer123")
    r = client.get(f"/mitarbeiter/{_fahrer1_id()}")
    assert r.status_code == 403


def test_urlaub_eintragen_und_zaehlen(client):
    login(client, "buero@dispohub.example", "buero123")
    mid = _fahrer1_id()
    from datetime import date, timedelta
    von = date.today() + timedelta(days=60)
    bis = von + timedelta(days=2)
    r = client.post(f"/mitarbeiter/{mid}/eintrag", data={
        "art": "urlaub", "datum": von.isoformat(), "bis": bis.isoformat(), "notiz": "Brückentage",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import PersonnelEntry, EntryArt
    db = SessionLocal()
    entry = (db.query(PersonnelEntry)
             .filter(PersonnelEntry.user_id == mid, PersonnelEntry.notiz == "Brückentage").first())
    assert entry is not None and entry.art == EntryArt.urlaub and entry.tage == 3
    db.delete(entry)
    db.commit()
    db.close()


def test_stunden_eintragen(client):
    login(client, "buero@dispohub.example", "buero123")
    mid = _fahrer1_id()
    from datetime import date
    r = client.post(f"/mitarbeiter/{mid}/eintrag", data={
        "art": "stunden", "datum": date.today().isoformat(), "stunden": "7,5",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import PersonnelEntry, EntryArt
    db = SessionLocal()
    entry = (db.query(PersonnelEntry)
             .filter(PersonnelEntry.user_id == mid, PersonnelEntry.art == EntryArt.stunden)
             .order_by(PersonnelEntry.id.desc()).first())
    assert entry is not None and abs(entry.stunden - 7.5) < 0.01
    db.delete(entry)
    db.commit()
    db.close()


def test_karten_und_kontingent_speichern(client):
    login(client, "gf@dispohub.example", "gf123")
    mid = _fahrer1_id()
    r = client.post(f"/mitarbeiter/{mid}/karten", data={
        "fahrerkarte_ablauf": "2028-05-01", "adr_karte_ablauf": "", "urlaubstage_kontingent": "28",
    }, follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    m = db.get(User, mid)
    assert m.urlaubstage_kontingent == 28
    assert m.fahrerkarte_ablauf.isoformat() == "2028-05-01"
    assert m.adr_karte_ablauf is None
    db.close()


def test_vertrag_pdf_hochladen(client):
    login(client, "buero@dispohub.example", "buero123")
    mid = _fahrer1_id()
    pdf = io.BytesIO(b"%PDF-1.4 test")
    r = client.post(f"/mitarbeiter/{mid}/dokument",
                    data={"typ": "vertrag"},
                    files={"datei": ("arbeitsvertrag.pdf", pdf, "application/pdf")},
                    follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import Document
    db = SessionLocal()
    doc = (db.query(Document).filter(Document.user_id == mid, Document.typ == "vertrag")
           .order_by(Document.id.desc()).first())
    assert doc is not None and doc.dateiname == "arbeitsvertrag.pdf"
    db.close()


def test_notiz_am_mitarbeiter(client):
    login(client, "gf@dispohub.example", "gf123")
    mid = _fahrer1_id()
    r = client.post(f"/mitarbeiter/{mid}/notiz", data={"text": "Wunsch: keine Nachtfahrten"},
                    follow_redirects=False)
    assert r.status_code == 303
    r = client.get(f"/mitarbeiter/{mid}")
    assert "Wunsch: keine Nachtfahrten" in r.text
