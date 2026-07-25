"""CSV-Import für Tankkarten-Abrechnungen.

Erwartetes Format (Semikolon-getrennt, wie von Tankkarten-Anbietern üblich):

    Datum;Kartennummer;Produkt;Menge;Betrag
    01.07.2026;DKV-1001;Diesel;62,40;98,15

- Datum: TT.MM.JJJJ
- Menge/Betrag: deutsches Dezimalkomma
- Unbekannte Kartennummern werden übersprungen (mit Hinweis).
- Duplikate (gleiche Karte + Datum + Betrag + Produkt) werden nicht erneut gebucht.
"""
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, date

from sqlalchemy.orm import Session

from app.models import FuelCard, FuelTransaction, CostEntry, CostCategory


@dataclass
class ImportResult:
    importiert: int = 0
    duplikate: int = 0
    unbekannte_karten: int = 0
    fehlerhafte_zeilen: int = 0
    summe: float = 0.0
    hinweise: list[str] = field(default_factory=list)


def _parse_de_float(s: str) -> float:
    return float(s.strip().replace(".", "").replace(",", "."))


def _parse_de_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%d.%m.%Y").date()


def import_csv(content: bytes | str, db: Session) -> ImportResult:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")

    res = ImportResult()
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    if not reader.fieldnames:
        res.hinweise.append("Datei ist leer oder kein CSV.")
        return res
    # Spaltennamen tolerant behandeln (Groß/Klein, Leerzeichen)
    feld = {f.strip().lower(): f for f in reader.fieldnames}
    noetig = {"datum", "kartennummer", "betrag"}
    if not noetig.issubset(feld.keys()):
        res.hinweise.append(
            "Spalten fehlen. Erwartet: Datum;Kartennummer;Produkt;Menge;Betrag"
        )
        return res

    karten = {c.kartennummer.strip().upper(): c for c in db.query(FuelCard).all()}

    for i, row in enumerate(reader, start=2):
        try:
            nummer = (row[feld["kartennummer"]] or "").strip().upper()
            datum = _parse_de_date(row[feld["datum"]])
            betrag = _parse_de_float(row[feld["betrag"]])
            produkt = (row.get(feld.get("produkt", ""), "") or "Diesel").strip() or "Diesel"
            menge = None
            if "menge" in feld and row.get(feld["menge"]):
                menge = _parse_de_float(row[feld["menge"]])
        except (ValueError, KeyError, TypeError):
            res.fehlerhafte_zeilen += 1
            res.hinweise.append(f"Zeile {i}: konnte nicht gelesen werden.")
            continue

        card = karten.get(nummer)
        if not card:
            res.unbekannte_karten += 1
            res.hinweise.append(f"Zeile {i}: unbekannte Karte „{nummer}“ – übersprungen.")
            continue

        # Duplikat?
        exists = (
            db.query(FuelTransaction)
            .filter(
                FuelTransaction.card_id == card.id,
                FuelTransaction.datum == datum,
                FuelTransaction.betrag == betrag,
                FuelTransaction.produkt == produkt,
            )
            .first()
        )
        if exists:
            res.duplikate += 1
            continue

        kategorie = CostCategory.adblue if "adblue" in produkt.lower() else CostCategory.kraftstoff
        cost = CostEntry(
            vehicle_id=card.vehicle_id, kategorie=kategorie, betrag=betrag, datum=datum,
            beschreibung=f"Tankkarte {card.kartennummer}: {produkt}"
                         + (f" {menge:.2f} l".replace(".", ",") if menge else ""),
        )
        db.add(cost)
        db.flush()
        db.add(FuelTransaction(
            card_id=card.id, datum=datum, produkt=produkt,
            menge_liter=menge, betrag=betrag, cost_id=cost.id,
        ))
        res.importiert += 1
        res.summe += betrag

    db.commit()
    return res
