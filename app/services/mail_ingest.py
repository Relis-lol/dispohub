"""E-Mail-Anbindung fürs Rechnungspostfach (IMAP-Polling) — VORBEREITET, aber
INAKTIV, solange keine echten Zugangsdaten in .env stehen.

So wird's aktiviert, sobald ihr ein Postfach habt (z.B. belege@eurefirma.de):
1. .env ergänzen:
     IMAP_HOST=imap.eurefirma.de
     IMAP_USER=belege@eurefirma.de
     IMAP_PASSWORD=... (App-Passwort, kein normales Postfach-Passwort verwenden)
     IMAP_ORDNER=INBOX
2. Diese Funktion regelmäßig aufrufen (z.B. per Scheduler/Cron alle 5-10 Minuten,
   oder manuell per Button analog zum bisherigen "Eingang simulieren").
3. Fertig — die bestehende Vorsortierung (app/services/mail_rules.py) läuft
   unverändert weiter, ganz gleich ob die Rechnung simuliert oder echt per Mail kam.

Sicherheitshinweis: Nutzt ein dediziertes Belege-Postfach mit eigenem Passwort,
NIE das normale Geschäftsführungs-Postfach — dieser Code braucht vollen Lesezugriff
auf den Posteingang.
"""
import email
import imaplib
import os
from datetime import date
from email.message import Message

from sqlalchemy.orm import Session

from app.models import Invoice, InvoiceStatus
from app.services.mail_rules import vorsortieren
from app.services.uploads import ALLOWED_DOC_EXT, UPLOAD_DIR

IMAP_HOST = os.environ.get("IMAP_HOST", "")
IMAP_USER = os.environ.get("IMAP_USER", "")
IMAP_PASSWORD = os.environ.get("IMAP_PASSWORD", "")
IMAP_ORDNER = os.environ.get("IMAP_ORDNER", "INBOX")


def ist_konfiguriert() -> bool:
    """True, sobald echte IMAP-Zugangsdaten hinterlegt sind."""
    return bool(IMAP_HOST and IMAP_USER and IMAP_PASSWORD)


def _anhang_speichern(msg: Message) -> str | None:
    """Speichert den ersten PDF-/Bild-Anhang wie ein normaler Upload."""
    import uuid
    for part in msg.walk():
        dateiname = part.get_filename()
        if not dateiname:
            continue
        ext = os.path.splitext(dateiname)[1].lower()
        if ext not in ALLOWED_DOC_EXT:
            continue
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        name = f"{uuid.uuid4().hex}{ext}"
        with open(os.path.join(UPLOAD_DIR, name), "wb") as fh:
            fh.write(part.get_payload(decode=True) or b"")
        return f"/static/uploads/{name}"
    return None


def _betrag_aus_betreff(betreff: str) -> float | None:
    """Simple Heuristik: erste Zahl mit Komma/Punkt im Betreff als Betrag."""
    import re
    m = re.search(r"(\d+[.,]\d{2})\s*(?:€|EUR)?", betreff)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def neue_rechnungen_abholen(db: Session) -> int:
    """Holt neue Mails aus dem Belege-Postfach und legt Invoice-Einträge an,
    genau wie der bisherige 'Eingang simulieren'-Button. Gibt die Anzahl neu
    angelegter Rechnungen zurück. Tut nichts, wenn nicht konfiguriert."""
    if not ist_konfiguriert():
        return 0

    angelegt = 0
    with imaplib.IMAP4_SSL(IMAP_HOST) as conn:
        conn.login(IMAP_USER, IMAP_PASSWORD)
        conn.select(IMAP_ORDNER)
        status, daten = conn.search(None, "UNSEEN")
        if status != "OK":
            return 0
        for num in daten[0].split():
            status, msg_daten = conn.fetch(num, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_daten[0][1])
            absender = email.utils.parseaddr(msg.get("From", ""))[1] or msg.get("From", "")
            betreff = msg.get("Subject", "")
            anhang_pfad = _anhang_speichern(msg)

            inv = Invoice(
                absender=absender, betreff=betreff,
                betrag=_betrag_aus_betreff(betreff),
                rechnungsdatum=date.today(),
                anhang_pfad=anhang_pfad,
                status=InvoiceStatus.eingegangen,
            )
            db.add(inv)
            db.flush()
            vorsortieren(inv, db)
            angelegt += 1
            conn.store(num, "+FLAGS", "\\Seen")
    db.commit()
    return angelegt
