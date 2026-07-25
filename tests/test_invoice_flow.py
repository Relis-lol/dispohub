"""End-to-End: Rechnung eingegangen → vorsortiert → geprüft → Kosten → Steuer-Export."""
from tests.conftest import login


def test_invoice_presort_and_confirm(client):
    login(client, "gf@dispohub.example", "gf123")

    # Simulierten Eingang erzeugen
    r = client.post("/rechnungen/simulieren", follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import Invoice, InvoiceStatus, CostEntry
    db = SessionLocal()
    inv = db.query(Invoice).filter(Invoice.status == InvoiceStatus.eingegangen).order_by(Invoice.id.desc()).first()
    iid = inv.id
    # Vorsortierung hat einen Hinweis gesetzt
    assert inv.hinweis
    db.close()

    # Prüf-Inbox zeigt die Rechnung
    inbox = client.get("/rechnungen")
    assert inbox.status_code == 200

    # Bestätigen → Kostenbuchung entsteht
    r = client.post(f"/rechnungen/{iid}/bestaetigen",
                    data={"kategorie": "werkstatt", "vehicle_id": "1", "betrag": "199.90"},
                    follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    inv = db.get(Invoice, iid)
    assert inv.status == InvoiceStatus.geprueft
    assert inv.cost_id is not None
    cost = db.get(CostEntry, inv.cost_id)
    assert float(cost.betrag) == 199.90
    assert cost.vehicle_id == 1
    db.close()


def test_duplicate_detection(client):
    """Zwei Rechnungen mit gleicher Nummer → zweite als Duplikat markiert."""
    from app.db import SessionLocal
    from app.models import Invoice, InvoiceStatus
    from app.services.mail_rules import vorsortieren
    from datetime import date

    db = SessionLocal()
    a = Invoice(absender="rechnung@werkstatt-x.de", betreff="Rechnung", rechnungsnummer="DUP-1",
                betrag=50, rechnungsdatum=date.today(), status=InvoiceStatus.eingegangen)
    db.add(a); db.flush(); vorsortieren(a, db)
    b = Invoice(absender="rechnung@werkstatt-x.de", betreff="Rechnung Kopie", rechnungsnummer="DUP-1",
                betrag=50, rechnungsdatum=date.today(), status=InvoiceStatus.eingegangen)
    db.add(b); db.flush(); vorsortieren(b, db)
    db.commit()
    assert b.ist_duplikat is True
    # Werkstatt-Absender → Kategorie werkstatt vorgeschlagen
    assert a.vorschlag_kategorie is not None
    db.close()


def test_tax_export_csv(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.get("/export/csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    # Kopfzeile vorhanden
    assert "Rechnungsnummer" in r.text
