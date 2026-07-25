"""Demodaten für einen glaubwürdigen Betriebsablauf.

Wird beim Start einmalig eingespielt, wenn die Datenbank noch leer ist.
Alle Daten sind frei erfunden.
"""
from datetime import date, timedelta, datetime

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.security import hash_password
from app.models import (
    User, Role, UserStatus,
    Vehicle, VehicleStatus, VehicleTyp,
    DamageReport, DamageStatus, Priority,
    Appointment, AppointmentSource, AppointmentStatus,
    CostEntry, CostCategory,
    Invoice, InvoiceStatus,
    ChatThread, ChatMembership, ChatMessage, ThreadArt, Document,
    FuelCard, AreaPermission, Task, SafetyItem, ParkingSpot,
)
from app.services.mail_rules import vorsortieren


def _today(offset: int = 0) -> date:
    return date.today() + timedelta(days=offset)


def seed(db: Session) -> None:
    if db.query(User).count() > 0:
        return  # bereits befüllt

    # --- Fahrzeuge ---------------------------------------------------------
    v1 = Vehicle(
        kennzeichen="B-TR 1201", hersteller="Mercedes-Benz", modell="Sprinter 317",
        typ=VehicleTyp.sprinter,
        fin="WDB9066331S123456", erstzulassung=date(2021, 3, 14), km_stand=142300,
        status=VehicleStatus.einsatzbereit, leasing_anbieter="AlphaLease",
        leasing_ende=_today(240), monatliche_fixkosten=612.00,
        hu_faellig=_today(58), sp_faellig=_today(58), uvv_faellig=_today(12),
        tacho_faellig=_today(400),
    )
    v2 = Vehicle(
        kennzeichen="B-TR 1450", hersteller="MAN", modell="TGE 3.180",
        typ=VehicleTyp.sprinter,
        fin="WMA06XZZ7NM654321", erstzulassung=date(2022, 7, 1), km_stand=88750,
        status=VehicleStatus.unterwegs, leasing_anbieter="AlphaLease",
        leasing_ende=_today(25), monatliche_fixkosten=740.00,
        hu_faellig=_today(-4), sp_faellig=_today(120), uvv_faellig=_today(90),
        tacho_faellig=_today(300),
    )
    v3 = Vehicle(
        kennzeichen="B-TR 0788", hersteller="Ford", modell="Transit 350",
        typ=VehicleTyp.sprinter,
        fin="WF0XXXTTGXKY000111", erstzulassung=date(2020, 11, 20), km_stand=205400,
        status=VehicleStatus.werkstatt_geplant, leasing_anbieter="Volksbank Finanz",
        leasing_ende=_today(500), monatliche_fixkosten=510.00,
        hu_faellig=_today(200), sp_faellig=_today(200), uvv_faellig=_today(-2),
        tacho_faellig=_today(210),
    )
    v4 = Vehicle(
        kennzeichen="B-TR 2233", hersteller="VW", modell="Crafter 35",
        typ=VehicleTyp.sprinter,
        fin="WV1ZZZSYZL9000222", erstzulassung=date(2023, 1, 9), km_stand=41200,
        status=VehicleStatus.einsatzbereit, leasing_anbieter="AlphaLease",
        leasing_ende=_today(600), monatliche_fixkosten=690.00,
        hu_faellig=_today(150), sp_faellig=_today(150), uvv_faellig=_today(45),
        tacho_faellig=_today(500),
    )
    v5 = Vehicle(
        kennzeichen="B-TR 3011", hersteller="Iveco", modell="Daily 35S",
        typ=VehicleTyp.sprinter,
        fin="ZCFC135A005000333", erstzulassung=date(2019, 5, 2), km_stand=268900,
        status=VehicleStatus.ausgefallen, leasing_anbieter=None,
        leasing_ende=None, monatliche_fixkosten=0.00,
        hu_faellig=_today(-20), sp_faellig=_today(-20), uvv_faellig=_today(-40),
        tacho_faellig=_today(60),
    )
    v6 = Vehicle(
        kennzeichen="B-TR 4477", hersteller="Mercedes-Benz", modell="Actros 1845",
        typ=VehicleTyp.lkw,
        fin="WDB9634001L777888", erstzulassung=date(2022, 2, 10), km_stand=178000,
        status=VehicleStatus.einsatzbereit, leasing_anbieter="AlphaLease",
        leasing_ende=_today(400), monatliche_fixkosten=980.00,
        hu_faellig=_today(80), sp_faellig=_today(80), uvv_faellig=_today(30),
        tacho_faellig=_today(350),
    )
    v7 = Vehicle(
        kennzeichen="B-TR 4478", hersteller="Schmitz Cargobull", modell="Kofferauflieger",
        typ=VehicleTyp.haenger, untertyp="Sattelauflieger 13,6m Koffer",
        fin="WSC13600A000999", erstzulassung=date(2021, 6, 1), km_stand=0,
        status=VehicleStatus.einsatzbereit, leasing_anbieter=None,
        leasing_ende=None, monatliche_fixkosten=0.00,
        hu_faellig=_today(80), sp_faellig=_today(80), uvv_faellig=None,
        tacho_faellig=None,
    )
    v8 = Vehicle(
        kennzeichen="B-TR 9001", hersteller="VW", modell="Passat Variant",
        typ=VehicleTyp.pkw,
        fin="WVWZZZ3CZME000123", erstzulassung=date(2023, 5, 20), km_stand=32500,
        status=VehicleStatus.einsatzbereit, leasing_anbieter="AlphaLease",
        leasing_ende=_today(500), monatliche_fixkosten=340.00,
        hu_faellig=_today(300), sp_faellig=None, uvv_faellig=None,
        tacho_faellig=None,
    )
    vehicles = [v1, v2, v3, v4, v5, v6, v7, v8]
    db.add_all(vehicles)
    db.flush()

    v7.zugfahrzeug_id = v6.id  # Hänger wird normalerweise von der Zugmaschine gezogen

    # --- Nutzer ------------------------------------------------------------
    admin = User(name="Admin", email="admin@dispohub.example", role=Role.admin,
                 password_hash=hash_password("admin123"))
    gf = User(name="Sabine Groß", email="gf@dispohub.example", role=Role.geschaeftsfuehrung,
              phone="+49 170 1112233", password_hash=hash_password("gf123"),
              geburtstag=_today(200).replace(year=1985))
    buero = User(name="Petra Klein", email="buero@dispohub.example", role=Role.buero,
                 phone="+49 170 4445566", password_hash=hash_password("buero123"),
                 geburtstag=_today(10).replace(year=1990))
    it = User(name="Jonas Weber", email="it@dispohub.example", role=Role.it,
              phone="+49 170 7778899", password_hash=hash_password("it123"))

    f1 = User(name="Kemal Yıldız", email="fahrer1@dispohub.example", role=Role.fahrer,
              phone="+49 151 2223344", password_hash=hash_password("fahrer123"),
              status=UserStatus.aktiv, vehicle_id=v1.id)
    f2 = User(name="Marek Nowak", email="fahrer2@dispohub.example", role=Role.fahrer,
              phone="+49 151 5556677", password_hash=hash_password("fahrer123"),
              status=UserStatus.aktiv, vehicle_id=v2.id,
              geburtstag=_today(7).replace(year=1992))
    f3 = User(name="Ahmed Hassan", email="fahrer3@dispohub.example", role=Role.fahrer,
              phone="+49 151 8889900", password_hash=hash_password("fahrer123"),
              status=UserStatus.aktiv, vehicle_id=v4.id)
    db.add_all([admin, gf, buero, it, f1, f2, f3])
    db.flush()

    # --- Schäden -----------------------------------------------------------
    d1 = DamageReport(
        vehicle_id=v3.id, reporter_id=f1.id,
        beschreibung="Seitenspiegel rechts abgefahren, Glas gesprungen.",
        prioritaet=Priority.kritisch, status=DamageStatus.uebernommen,
        nachricht_an_gf="Bitte zeitnah, Sichtbehinderung.",
        created_at=datetime.now() - timedelta(days=3),
    )
    d2 = DamageReport(
        vehicle_id=v2.id, reporter_id=f2.id,
        beschreibung="Warnleuchte Motor leuchtet dauerhaft, Leistungsverlust.",
        prioritaet=Priority.kritisch, status=DamageStatus.gemeldet,
        created_at=datetime.now() - timedelta(hours=5),
    )
    d3 = DamageReport(
        vehicle_id=v1.id, reporter_id=f1.id,
        beschreibung="Kratzer an Heckklappe, kein Funktionsproblem.",
        prioritaet=Priority.info, status=DamageStatus.gemeldet,
        created_at=datetime.now() - timedelta(hours=20),
    )
    # Demo-Sticky-Note auf der Fahrzeug-Draufsicht (LKW-Zugmaschine)
    d4 = DamageReport(
        vehicle_id=v6.id, reporter_id=gf.id,
        beschreibung="Delle vorne rechts am Kotflügel, vermutlich beim Rangieren.",
        prioritaet=Priority.normal, status=DamageStatus.gemeldet,
        schadensdatum=_today(-2), ort="Betriebshof",
        position_x=0.78, position_y=0.18,
        created_at=datetime.now() - timedelta(days=2),
    )
    db.add_all([d1, d2, d3, d4])
    db.flush()

    # --- Termine / Kalender ------------------------------------------------
    appts = [
        Appointment(vehicle_id=v3.id, damage_id=d1.id, titel="Werkstatt: Spiegel Ersatz",
                    quelle=AppointmentSource.schaden, faellig_am=_today(2)),
        Appointment(vehicle_id=v2.id, titel="HU/AU überfällig",
                    quelle=AppointmentSource.pruefung, faellig_am=_today(-4)),
        Appointment(vehicle_id=v1.id, titel="UVV-Prüfung fällig",
                    quelle=AppointmentSource.pruefung, faellig_am=_today(12)),
        Appointment(vehicle_id=v2.id, titel="Leasing läuft aus",
                    quelle=AppointmentSource.leasing, faellig_am=_today(25)),
        Appointment(vehicle_id=v4.id, titel="Ölwechsel / Wartung",
                    quelle=AppointmentSource.wartung, faellig_am=_today(6)),
        Appointment(titel="Team-Besprechung Disposition",
                    quelle=AppointmentSource.allgemein, faellig_am=_today(0)),
    ]
    db.add_all(appts)

    # --- Kosten ------------------------------------------------------------
    heute = date.today()
    monat_start = heute.replace(day=1)
    costs = [
        CostEntry(vehicle_id=v1.id, kategorie=CostCategory.leasing, betrag=612.00,
                  datum=monat_start, beschreibung="Leasingrate"),
        CostEntry(vehicle_id=v2.id, kategorie=CostCategory.leasing, betrag=740.00,
                  datum=monat_start, beschreibung="Leasingrate"),
        CostEntry(vehicle_id=v3.id, kategorie=CostCategory.reparatur, betrag=284.50,
                  datum=heute, damage_id=d1.id, beschreibung="Spiegel + Montage"),
        CostEntry(vehicle_id=v1.id, kategorie=CostCategory.kraftstoff, betrag=196.30,
                  datum=heute - timedelta(days=2), beschreibung="Tankkarte Diesel"),
        CostEntry(vehicle_id=v2.id, kategorie=CostCategory.kraftstoff, betrag=221.90,
                  datum=heute - timedelta(days=1), beschreibung="Tankkarte Diesel"),
        CostEntry(vehicle_id=v5.id, kategorie=CostCategory.werkstatt, betrag=1450.00,
                  datum=heute - timedelta(days=4), beschreibung="Getriebeschaden Diagnose"),
        CostEntry(vehicle_id=v4.id, kategorie=CostCategory.versicherung, betrag=98.00,
                  datum=monat_start, beschreibung="KFZ-Versicherung"),
    ]
    db.add_all(costs)

    db.commit()


def seed_invoices(db: Session) -> None:
    """Rechnungen separat seeden (auch wenn Nutzer/Fahrzeuge schon existieren)."""
    if db.query(Invoice).count() > 0:
        return
    heute = date.today()
    demo = [
        # (absender, betreff, rnr, betrag, tage_alt, status)
        ("rechnung@kfz-schneider.de", "Rechnung Reparatur B-TR 0788", "R-2026-4471", 512.40, 1, "eingegangen"),
        ("buchhaltung@aral-tankkarte.de", "Tankabrechnung Juli 2026", "AR-778123", 1043.75, 2, "eingegangen"),
        ("service@dekra.de", "Rechnung HU/AU Prüfung", "DK-99120", 128.00, 3, "eingegangen"),
        ("kontakt@alphalease.de", "Leasingrate Juli B-TR 1201", "AL-0725-1201", 612.00, 6, "geprueft"),
        ("info@unbekannt-absender.com", "Ihre Bestellung", None, None, 4, "ungeklaert"),
        # Duplikat der ersten Rechnungsnummer → Duplikatwarnung
        ("rechnung@kfz-schneider.de", "Rechnung Reparatur (Kopie)", "R-2026-4471", 512.40, 0, "eingegangen"),
    ]
    for absender, betreff, rnr, betrag, alt, status in demo:
        inv = Invoice(
            absender=absender, betreff=betreff, rechnungsnummer=rnr, betrag=betrag,
            rechnungsdatum=heute - timedelta(days=alt),
            status=InvoiceStatus(status),
        )
        db.add(inv)
        db.flush()
        vorsortieren(inv, db)
        # Für bereits geprüfte: Zuordnung + Kostenbuchung setzen
        if status == "geprueft":
            inv.kategorie = inv.vorschlag_kategorie or CostCategory.leasing
            inv.vehicle_id = inv.vorschlag_vehicle_id
            cost = CostEntry(vehicle_id=inv.vehicle_id, kategorie=inv.kategorie,
                             betrag=betrag, datum=inv.rechnungsdatum,
                             beschreibung=f"{absender}: {betreff}"[:250])
            db.add(cost)
            db.flush()
            inv.cost_id = cost.id
    db.commit()


def seed_chat(db: Session) -> None:
    """Chat-Threads + Demo-Nachrichten (läuft, wenn noch keine Threads existieren)."""
    if db.query(ChatThread).count() > 0:
        return
    gf = db.query(User).filter(User.email == "gf@dispohub.example").first()
    fahrer = db.query(User).filter(User.role == Role.fahrer).all()
    buero = db.query(User).filter(User.email == "buero@dispohub.example").first()
    if not gf or not fahrer:
        return

    def add_thread(art, name, mitglieder):
        th = ChatThread(art=art, name=name)
        db.add(th)
        db.flush()
        for u in mitglieder:
            db.add(ChatMembership(thread_id=th.id, user_id=u.id))
        return th

    def add_msg(th, sender, text=None, doc=None):
        m = ChatMessage(thread_id=th.id, sender_id=sender.id, text=text)
        if doc is not None:
            db.add(doc)
            db.flush()
            m.document_id = doc.id
        db.add(m)
        db.flush()
        return m

    # Gruppen
    # "Alle" ist ein rein internes GF/Büro-Broadcast — Fahrer sind hier bewusst KEIN
    # Mitglied (sonst taucht ein für sie irrelevanter Kanal in ihrer Chat-Liste auf).
    add_thread(ThreadArt.gruppe, "Alle", [gf] + ([buero] if buero else []))
    # "Alle Fahrer" ist der Durchsage-Kanal von GF an die Fahrer (nur lesen für Fahrer).
    alle_fahrer = add_thread(ThreadArt.gruppe, "Alle Fahrer", [gf] + fahrer)
    add_msg(alle_fahrer, gf, "Willkommen im DispoHub-Chat! Bitte Schäden künftig hier oder über „Melden“ senden.")

    # Kollegen-Chat: Fahrer dürfen hier (im Gegensatz zu "Alle"/"Alle Fahrer") frei
    # untereinander schreiben, z.B. "komme 2h später".
    kollegen = add_thread(ThreadArt.gruppe, "Kollegen-Chat", [gf] + fahrer)
    add_msg(kollegen, fahrer[0], "Bin heute mit dem Sprinter unterwegs, falls jemand tauschen will Bescheid sagen.")

    # Direktchats GF ↔ Fahrer
    f1 = fahrer[0]
    d1 = add_thread(ThreadArt.direkt, None, [gf, f1])
    add_msg(d1, f1, "Moin! Kann ich heute etwas früher Schluss machen?")
    add_msg(d1, gf, "Klar, kein Problem. 👍")
    # Bild-Nachricht vom Fahrer (Demo-Platzhalter, kein echtes Foto)
    add_msg(d1, f1, "Hier noch das Foto vom Kratzer am Fahrzeug:",
            doc=Document(pfad="/static/icons/demo_kratzer.svg", typ="foto", dateiname="kratzer.jpg"))

    for f in fahrer[1:]:
        add_thread(ThreadArt.direkt, None, [gf, f])

    db.commit()


def seed_fuelcards(db: Session) -> None:
    """Tankkarten den Fahrzeugen zuordnen (läuft, wenn noch keine Karten existieren)."""
    if db.query(FuelCard).count() > 0:
        return
    fahrzeuge = db.query(Vehicle).order_by(Vehicle.id).all()
    for i, v in enumerate(fahrzeuge, start=1):
        db.add(FuelCard(kartennummer=f"DKV-10{i:02d}", anbieter="DKV", vehicle_id=v.id))
    db.commit()


def seed_tasks(db: Session) -> None:
    """Demo-Aufgaben vom Büro an Fahrer/Fahrzeuge (läuft, wenn noch keine existieren)."""
    if db.query(Task).count() > 0:
        return
    gf = db.query(User).filter(User.email == "gf@dispohub.example").first()
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    v1 = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 1201").first()
    v6 = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 4477").first()
    if not gf:
        return
    db.add_all([
        Task(titel="TÜV diese Woche", vehicle_id=v6.id if v6 else None,
             beschreibung="Termin bei DEKRA vereinbaren und Fahrzeug vorstellen.",
             faellig_am=_today(4), erstellt_von_id=gf.id),
        Task(titel="Fahrzeug waschen", zugewiesen_user_id=f1.id if f1 else None,
             vehicle_id=v1.id if v1 else None,
             faellig_am=_today(1), erstellt_von_id=gf.id),
        Task(titel="Reifenprofil prüfen", beschreibung="Bei allen Fahrzeugen Profiltiefe checken.",
             faellig_am=_today(7), erstellt_von_id=gf.id),
    ])
    db.commit()


def seed_safety_items(db: Session) -> None:
    """Demo-ADR-Mittel an ein paar Fahrzeugen (läuft, wenn noch keine existieren)."""
    if db.query(SafetyItem).count() > 0:
        return
    v1 = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 1201").first()
    v6 = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 4477").first()
    if not v1:
        return
    db.add_all([
        SafetyItem(vehicle_id=v1.id, bezeichnung="Feuerlöscher", ablauf_am=_today(20)),
        SafetyItem(vehicle_id=v1.id, bezeichnung="Augenspülflasche", ablauf_am=_today(-5)),
        SafetyItem(vehicle_id=v6.id if v6 else v1.id, bezeichnung="Feuerlöscher", ablauf_am=_today(180)),
        SafetyItem(vehicle_id=v6.id if v6 else v1.id, bezeichnung="Filtermaske", ablauf_am=_today(10)),
    ])
    db.commit()


def seed_parking(db: Session) -> None:
    """Demo-Standortmeldung (läuft, wenn noch keine existiert)."""
    if db.query(ParkingSpot).count() > 0:
        return
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    v1 = db.query(Vehicle).filter(Vehicle.kennzeichen == "B-TR 1201").first()
    if not f1 or not v1:
        return
    # Berlin, Alexanderplatz-Gegend (frei erfunden)
    db.add(ParkingSpot(
        vehicle_id=v1.id, reporter_id=f1.id,
        lat=52.521918, lng=13.413215,
        notiz="Kundenparkplatz, Zufahrt über Hinterhof",
        created_at=datetime.now() - timedelta(hours=2),
    ))
    db.commit()


def seed_personnel(db: Session) -> None:
    """Demo-Personalakten: Kartendaten + ein paar Urlaubs-/Krank-/Stunden-Einträge."""
    from app.models import PersonnelEntry, EntryArt
    if db.query(PersonnelEntry).count() > 0:
        return
    f1 = db.query(User).filter(User.email == "fahrer1@dispohub.example").first()
    f2 = db.query(User).filter(User.email == "fahrer2@dispohub.example").first()
    if not f1 or not f2:
        return
    f1.fahrerkarte_ablauf = _today(400)
    f1.adr_karte_ablauf = _today(25)  # bald fällig -> Ampel gelb/rot sichtbar
    f2.fahrerkarte_ablauf = _today(90)
    db.add_all([
        PersonnelEntry(user_id=f1.id, art=EntryArt.urlaub,
                       datum=_today(-40), bis=_today(-34), notiz="Sommerurlaub"),
        PersonnelEntry(user_id=f1.id, art=EntryArt.krank, datum=_today(-12)),
        PersonnelEntry(user_id=f1.id, art=EntryArt.stunden, datum=_today(-1), stunden=8.5),
        PersonnelEntry(user_id=f2.id, art=EntryArt.urlaub,
                       datum=_today(20), bis=_today(24), notiz="Genehmigt durch GF"),
    ])
    db.commit()


def seed_permissions(db: Session) -> None:
    """Standard-Zugriffsrechte: Büro sieht anfangs alles (bestehendes Verhalten)."""
    from app.services.permissions import BEREICHE
    if db.query(AreaPermission).count() > 0:
        return
    for bereich in BEREICHE:
        db.add(AreaPermission(bereich=bereich, buero_erlaubt=True))
    db.commit()


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        seed(db)
        seed_invoices(db)
        seed_chat(db)
        seed_fuelcards(db)
        seed_tasks(db)
        seed_safety_items(db)
        seed_parking(db)
        seed_personnel(db)
        seed_permissions(db)
    finally:
        db.close()
