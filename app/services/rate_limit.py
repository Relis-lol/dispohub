"""Brute-Force-Schutz fürs Login: einfacher In-Memory-Zähler pro IP+E-Mail.

Bewusst ohne externen Speicher (Redis o.ä.) — passt zum Rest der App, die
ohnehin nur mit einem einzelnen uvicorn-Worker läuft (siehe Chat-Broadcast).
Bei Mehr-Worker-Betrieb müsste das auf einen gemeinsamen Speicher wandern.
"""
import time

MAX_VERSUCHE = 5
SPERRE_SEKUNDEN = 15 * 60

# key = (ip, email) -> Liste von Fehlversuch-Zeitstempeln
_fehlversuche: dict[tuple[str, str], list[float]] = {}


def _key(ip: str, email: str) -> tuple[str, str]:
    return (ip, email.strip().lower())


def gesperrt_fuer(ip: str, email: str) -> int:
    """Verbleibende Sperrzeit in Sekunden (0 = nicht gesperrt)."""
    versuche = _fehlversuche.get(_key(ip, email), [])
    jetzt = time.time()
    versuche = [t for t in versuche if jetzt - t < SPERRE_SEKUNDEN]
    if len(versuche) < MAX_VERSUCHE:
        return 0
    aeltester_relevanter = min(versuche)
    return max(0, int(SPERRE_SEKUNDEN - (jetzt - aeltester_relevanter)))


def fehlversuch_merken(ip: str, email: str) -> None:
    k = _key(ip, email)
    jetzt = time.time()
    versuche = [t for t in _fehlversuche.get(k, []) if jetzt - t < SPERRE_SEKUNDEN]
    versuche.append(jetzt)
    _fehlversuche[k] = versuche


def erfolg_zuruecksetzen(ip: str, email: str) -> None:
    _fehlversuche.pop(_key(ip, email), None)
