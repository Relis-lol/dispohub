"""Sprachauswahl für den Fahrer-Bereich: Cookie-basiert, kein Server-Roundtrip
zum Speichern (JS setzt das Cookie direkt, Seite lädt mit der neuen Sprache
neu). Kein Login/Konto nötig, funktioniert schon auf der Login-Seite.
"""
from starlette.requests import Request

from app.i18n.translations import TRANSLATIONS

COOKIE_NAME = "fh_lang"
STANDARD_SPRACHE = "de"

SPRACHEN = {
    "de": "Deutsch",
    "cs": "Čeština",
    "en": "English",
    "ru": "Русский",
    "pl": "Polski",
    "tr": "Türkçe",
}

FLAGGEN = {
    "de": "🇩🇪",
    "cs": "🇨🇿",
    "en": "🇬🇧",
    "ru": "🇷🇺",
    "pl": "🇵🇱",
    "tr": "🇹🇷",
}


def sprache_ermitteln(request: Request) -> str:
    wert = request.cookies.get(COOKIE_NAME, STANDARD_SPRACHE)
    return wert if wert in SPRACHEN else STANDARD_SPRACHE


def uebersetzen(schluessel: str, sprache: str, **platzhalter) -> str:
    katalog = TRANSLATIONS.get(sprache, TRANSLATIONS[STANDARD_SPRACHE])
    text = katalog.get(schluessel) or TRANSLATIONS[STANDARD_SPRACHE].get(schluessel, schluessel)
    if platzhalter:
        try:
            return text.format(**platzhalter)
        except (KeyError, IndexError):
            return text
    return text


def i18n_context(request: Request) -> dict:
    """Context-Processor für Jinja2Templates: macht tr()/lang/sprachen/flaggen
    in jedem Template automatisch verfügbar, ohne jede Route anzufassen.
    Heißt bewusst "tr" statt "t" — "t" ist in den Chat-Templates schon der
    Variablenname für das ChatThread-Objekt."""
    sprache = sprache_ermitteln(request)
    return {
        "lang": sprache,
        "tr": lambda schluessel, **kw: uebersetzen(schluessel, sprache, **kw),
        "sprachen": SPRACHEN,
        "flaggen": FLAGGEN,
    }
