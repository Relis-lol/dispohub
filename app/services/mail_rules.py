"""Regelbasierte Vorsortierung eingehender Rechnungen/E-Mails.

Bewusst ohne KI: bekannte Absender, Betreff-Schlüsselwörter, Kennzeichen-Erkennung
und Rechnungsnummer-Duplikate. Die Geschäftsführung bestätigt nur unklare Fälle.
"""
import re

from sqlalchemy.orm import Session

from app.models import Vehicle, CostCategory, Invoice

# Bekannte Absender-Domains/-Namen → Kostenkategorie
ABSENDER_KATEGORIE = {
    "werkstatt": CostCategory.werkstatt,
    "kfz": CostCategory.werkstatt,
    "autohaus": CostCategory.werkstatt,
    "reifen": CostCategory.reifen,
    "dekra": CostCategory.pruefung,
    "tuv": CostCategory.pruefung,
    "tüv": CostCategory.pruefung,
    "leasing": CostCategory.leasing,
    "alphalease": CostCategory.leasing,
    "versicher": CostCategory.versicherung,
    "allianz": CostCategory.versicherung,
    "huk": CostCategory.versicherung,
    "aral": CostCategory.tankkarte,
    "shell": CostCategory.tankkarte,
    "dkv": CostCategory.tankkarte,
    "uta": CostCategory.tankkarte,
    "tank": CostCategory.tankkarte,
    "maut": CostCategory.maut,
    "toll": CostCategory.maut,
}


def _kategorie_aus_absender(absender: str) -> CostCategory | None:
    a = absender.lower()
    for key, kat in ABSENDER_KATEGORIE.items():
        if key in a:
            return kat
    return None


def _kennzeichen_finden(text: str, db: Session) -> Vehicle | None:
    """Sucht bekannte Kennzeichen im Text (auch mit variabler Leerzeichen-Schreibweise)."""
    fahrzeuge = db.query(Vehicle).filter(Vehicle.geloescht_am.is_(None)).all()
    norm_text = re.sub(r"[\s\-]", "", text.upper())
    for v in fahrzeuge:
        norm_kz = re.sub(r"[\s\-]", "", v.kennzeichen.upper())
        if norm_kz and norm_kz in norm_text:
            return v
    return None


def vorsortieren(invoice: Invoice, db: Session) -> None:
    """Setzt vorschlag_kategorie, vorschlag_vehicle_id, ist_duplikat und hinweis."""
    hinweise: list[str] = []

    # 1. Kategorie aus Absender
    kat = _kategorie_aus_absender(invoice.absender or "")
    if kat:
        invoice.vorschlag_kategorie = kat
        hinweise.append(f"Absender erkannt → Kategorie {kat.value}")

    # 2. Betreff-Schlüsselwort "Rechnung"
    if "rechnung" in (invoice.betreff or "").lower():
        hinweise.append("Betreff enthält „Rechnung“")

    # 3. Kennzeichen im Betreff/Absender
    such_text = f"{invoice.betreff} {invoice.absender}"
    v = _kennzeichen_finden(such_text, db)
    if v:
        invoice.vorschlag_vehicle_id = v.id
        hinweise.append(f"Kennzeichen erkannt → {v.kennzeichen}")

    # 4. Duplikat: gleiche Rechnungsnummer schon vorhanden
    if invoice.rechnungsnummer:
        dup = (
            db.query(Invoice)
            .filter(Invoice.rechnungsnummer == invoice.rechnungsnummer, Invoice.id != invoice.id)
            .first()
        )
        if dup:
            invoice.ist_duplikat = True
            hinweise.append(f"⚠ Mögliches Duplikat von Rechnung #{dup.id}")

    invoice.hinweis = " · ".join(hinweise) if hinweise else "Keine Regel gegriffen – bitte prüfen."
