"""Tankkarten-Import: CSV → Kostenbuchung, Duplikate, unbekannte Karten."""
from tests.conftest import login

CSV = (
    "Datum;Kartennummer;Produkt;Menge;Betrag\n"
    "01.07.2026;DKV-1001;Diesel;62,40;98,15\n"
    "03.07.2026;DKV-1002;Diesel;71,10;112,04\n"
    "05.07.2026;UNBEKANNT-999;Diesel;50,00;80,00\n"
    "kaputte zeile ohne semikolons\n"
)


def _upload(client, content: str):
    return client.post(
        "/tankkarten/import",
        files={"datei": ("abrechnung.csv", content.encode("utf-8"), "text/csv")},
        follow_redirects=False,
    )


def test_import_creates_costs_and_skips_unknown(client):
    login(client, "gf@dispohub.example", "gf123")
    r = _upload(client, CSV)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import FuelTransaction, CostEntry, FuelCard
    db = SessionLocal()
    txs = db.query(FuelTransaction).all()
    assert len(txs) == 2  # unbekannte Karte + kaputte Zeile übersprungen

    # Kosten wurden dem richtigen Fahrzeug zugeordnet
    card1 = db.query(FuelCard).filter(FuelCard.kartennummer == "DKV-1001").first()
    tx1 = db.query(FuelTransaction).filter(FuelTransaction.card_id == card1.id).first()
    cost = db.get(CostEntry, tx1.cost_id)
    assert cost.vehicle_id == card1.vehicle_id
    assert float(cost.betrag) == 98.15
    assert cost.kategorie.value == "kraftstoff"
    db.close()


def test_reimport_detects_duplicates(client):
    login(client, "gf@dispohub.example", "gf123")
    r = _upload(client, CSV)  # gleiche Datei nochmal
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.models import FuelTransaction
    db = SessionLocal()
    # keine neuen Transaktionen dazugekommen
    assert db.query(FuelTransaction).count() == 2
    db.close()


def test_fahrer_blocked(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get("/tankkarten").status_code == 403
