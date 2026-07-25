"""PDF-Monatsbericht für die Steuerberatung (fpdf2, Core-Fonts/cp1252)."""
from datetime import date

from fpdf import FPDF
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CostEntry, Vehicle, Invoice, InvoiceStatus
from app.models.cost import CATEGORY_LABELS


def _eur(v) -> str:
    return f"{float(v or 0):,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")


class _Report(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.cell(0, 8, "DispoHub - Monatsbericht", new_x="LMARGIN", new_y="NEXT")
        self.set_font("helvetica", "", 9)
        self.set_text_color(110)
        self.cell(0, 5, f"Erstellt am {date.today().strftime('%d.%m.%Y')} - "
                        "Aufbereitung für die Steuerberatung (ersetzt keine Buchhaltung)",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0)
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "", 8)
        self.set_text_color(130)
        self.cell(0, 6, f"Seite {self.page_no()}/{{nb}}", align="C")

    def section(self, titel: str):
        self.ln(2)
        self.set_font("helvetica", "B", 11)
        self.set_fill_color(230, 240, 251)
        self.cell(0, 7, f" {titel}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def table_row(self, cols: list[tuple[str, float, str]], bold=False, header=False):
        """cols: Liste (text, breite, align)."""
        self.set_font("helvetica", "B" if (bold or header) else "", 9)
        if header:
            self.set_text_color(110)
        h = 6
        for text, w, align in cols:
            self.cell(w, h, text, align=align)
        self.ln(h)
        self.set_text_color(0)


def build_monthly_pdf(db: Session) -> bytes:
    heute = date.today()
    monat_start = heute.replace(day=1)
    monat_label = heute.strftime("%m/%Y")

    pdf = _Report()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Zusammenfassung ---
    gesamt = db.query(func.coalesce(func.sum(CostEntry.betrag), 0)).filter(
        CostEntry.datum >= monat_start).scalar()
    n_gep = db.query(Invoice).filter(Invoice.status == InvoiceStatus.geprueft,
                                     Invoice.rechnungsdatum >= monat_start).count()
    n_off = db.query(Invoice).filter(Invoice.status != InvoiceStatus.geprueft).count()

    pdf.section(f"Zusammenfassung {monat_label}")
    pdf.table_row([("Gesamtkosten des Monats", 90, "L"), (_eur(gesamt), 60, "R")], bold=True)
    pdf.table_row([("Geprüfte Rechnungen", 90, "L"), (str(n_gep), 60, "R")])
    pdf.table_row([("Ungeklärte / offene Belege", 90, "L"), (str(n_off), 60, "R")])

    # --- Kosten nach Kategorie ---
    pdf.section("Kosten nach Kategorie")
    je_kat = (db.query(CostEntry.kategorie, func.coalesce(func.sum(CostEntry.betrag), 0))
              .filter(CostEntry.datum >= monat_start)
              .group_by(CostEntry.kategorie).all())
    for kat, summe in sorted(je_kat, key=lambda x: -float(x[1])):
        pdf.table_row([(CATEGORY_LABELS.get(kat, kat.value), 90, "L"), (_eur(summe), 60, "R")])

    # --- Kosten nach Fahrzeug ---
    pdf.section("Kosten nach Fahrzeug")
    je_fzg = (db.query(Vehicle, func.coalesce(func.sum(CostEntry.betrag), 0))
              .outerjoin(CostEntry, (CostEntry.vehicle_id == Vehicle.id) &
                         (CostEntry.datum >= monat_start))
              .group_by(Vehicle.id).all())
    for v, summe in sorted(je_fzg, key=lambda x: -float(x[1])):
        pdf.table_row([(f"{v.kennzeichen}  ({v.hersteller} {v.modell})", 110, "L"),
                       (_eur(summe), 40, "R")])

    # --- Geprüfte Rechnungen (Belegliste) ---
    pdf.section(f"Belegliste - geprüfte Rechnungen {monat_label}")
    pdf.table_row([("Datum", 22, "L"), ("Nr.", 32, "L"), ("Absender", 60, "L"),
                   ("Fahrzeug", 26, "L"), ("Betrag", 30, "R")], header=True)
    rechnungen = (db.query(Invoice)
                  .filter(Invoice.status == InvoiceStatus.geprueft,
                          Invoice.rechnungsdatum >= monat_start)
                  .order_by(Invoice.rechnungsdatum.asc()).all())
    for i in rechnungen:
        pdf.table_row([
            (i.rechnungsdatum.strftime("%d.%m.%y") if i.rechnungsdatum else "-", 22, "L"),
            ((i.rechnungsnummer or "-")[:18], 32, "L"),
            (i.absender[:38], 60, "L"),
            (i.vehicle.kennzeichen if i.vehicle else "Allg.", 26, "L"),
            (_eur(i.betrag), 30, "R"),
        ])
    if not rechnungen:
        pdf.table_row([("Keine geprüften Rechnungen in diesem Monat.", 150, "L")])

    if n_off:
        pdf.ln(3)
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(160, 60, 40)
        pdf.multi_cell(0, 5, f"Hinweis: {n_off} Beleg(e) sind noch ungeklärt oder in Prüfung "
                             "und in diesem Bericht nicht enthalten.")
        pdf.set_text_color(0)

    return bytes(pdf.output())
