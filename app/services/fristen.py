from datetime import date


def ampel(faellig: date | None, gelb_tage: int = 30) -> str:
    """Ampellogik für Fristen.

    grün  = ausreichend Zeit
    gelb  = Termin nähert sich (innerhalb gelb_tage)
    rot   = überfällig
    grau  = Daten fehlen
    """
    if faellig is None:
        return "grau"
    rest = (faellig - date.today()).days
    if rest < 0:
        return "rot"
    if rest <= gelb_tage:
        return "gelb"
    return "gruen"


AMPEL_TONE = {"gruen": "ok", "gelb": "warn", "rot": "bad", "grau": "muted"}


def ampel_tone(faellig: date | None, gelb_tage: int = 30) -> str:
    return AMPEL_TONE[ampel(faellig, gelb_tage)]


def tage_bis(faellig: date | None) -> int | None:
    if faellig is None:
        return None
    return (faellig - date.today()).days


def tage_bis_geburtstag(geburtstag: date | None) -> int | None:
    """Tage bis zum nächsten Geburtstag, unabhängig vom Geburtsjahr."""
    if geburtstag is None:
        return None
    heute = date.today()
    try:
        naechster = geburtstag.replace(year=heute.year)
    except ValueError:  # 29. Februar in einem Nicht-Schaltjahr
        naechster = geburtstag.replace(year=heute.year, day=28)
    if naechster < heute:
        try:
            naechster = naechster.replace(year=heute.year + 1)
        except ValueError:
            naechster = naechster.replace(year=heute.year + 1, day=28)
    return (naechster - heute).days
