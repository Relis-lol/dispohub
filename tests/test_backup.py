"""Backup-Download: nur GF/Admin, liefert eine funktionierende SQLite-Datei."""
import sqlite3
import tempfile

from tests.conftest import login


def test_gf_kann_backup_herunterladen(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.get("/verwaltung/backup")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"
    assert "attachment" in r.headers["content-disposition"]
    assert len(r.content) > 0

    # Heruntergeladene Datei ist eine echte, lesbare SQLite-DB mit Nutzerdaten
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(r.content)
        tmp_pfad = tmp.name
    con = sqlite3.connect(tmp_pfad)
    anzahl = con.execute("select count(*) from users").fetchone()[0]
    con.close()
    assert anzahl > 0


def test_buero_hat_keinen_zugriff_auf_backup(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.get("/verwaltung/backup")
    assert r.status_code == 403


def test_fahrer_hat_keinen_zugriff_auf_backup(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    r = client.get("/verwaltung/backup")
    assert r.status_code == 403
