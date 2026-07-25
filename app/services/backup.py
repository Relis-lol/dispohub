"""Backup-Download der Datenbank (nur GF/Admin) — bewusst simpel: eine Datei,
die der GF manuell herunterlädt und selbst sichert (z.B. auf dem privaten PC).
Kein automatischer Cloud-Versand, kein Zeitplan — das ist Absicht.

Wiederherstellen: heruntergeladene .db-Datei einfach als dispohub.db an die
Stelle der aktuellen Datenbank kopieren (App vorher stoppen).
"""
import os
import sqlite3
import tempfile

from app.config import settings

SQLITE_PRAEFIX = "sqlite:///"


def ist_sqlite() -> bool:
    return settings.database_url.startswith("sqlite")


def sqlite_pfad() -> str:
    return settings.database_url.removeprefix(SQLITE_PRAEFIX)


def backup_erzeugen() -> bytes | None:
    """Erzeugt eine konsistente Kopie der SQLite-Datenbankdatei (nutzt SQLite's
    eigene Backup-API, damit auch bei parallelem Zugriff kein halbgeschriebener
    Zustand kopiert wird). None, falls keine SQLite-DB im Einsatz ist (z.B.
    Postgres in Docker — dort übernehmen pg_dump/Volume-Snapshots die Sicherung)."""
    if not ist_sqlite():
        return None
    quelle = sqlite3.connect(sqlite_pfad())
    tmp_fd, tmp_pfad = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        ziel = sqlite3.connect(tmp_pfad)
        try:
            quelle.backup(ziel)
        finally:
            ziel.close()
        with open(tmp_pfad, "rb") as fh:
            return fh.read()
    finally:
        quelle.close()
        os.remove(tmp_pfad)
