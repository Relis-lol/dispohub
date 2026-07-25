"""Smoke: alle Hauptseiten antworten je Rolle korrekt; PDF-Export liefert echtes PDF."""
import pytest

from tests.conftest import login

OFFICE_PAGES = [
    "/", "/schaeden", "/fahrzeuge", "/fahrzeuge/1", "/fahrzeuge/1/draufsicht", "/kalender",
    "/kosten", "/mitarbeiter", "/rechnungen", "/export", "/tankkarten", "/chat", "/melden",
    "/aufgaben", "/einstellungen/rechte", "/notizen",
]

DRIVER_ALLOWED = ["/melden", "/chat", "/aufgaben"]
DRIVER_BLOCKED = ["/", "/schaeden", "/kosten", "/rechnungen", "/export", "/tankkarten",
                  "/fahrzeuge", "/mitarbeiter", "/kalender", "/einstellungen/rechte", "/it", "/notizen"]


def test_office_pages_ok(client):
    login(client, "gf@dispohub.example", "gf123")
    for url in OFFICE_PAGES:
        r = client.get(url)
        assert r.status_code == 200, f"{url} -> {r.status_code}"


def test_driver_access_matrix(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    for url in DRIVER_ALLOWED:
        assert client.get(url).status_code == 200, f"{url} sollte erlaubt sein"
    for url in DRIVER_BLOCKED:
        assert client.get(url).status_code == 403, f"{url} sollte blockiert sein"


def test_pdf_report(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.get("/export/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 1500  # kein leeres Dokument


def test_pwa_endpoints(client):
    assert client.get("/manifest.webmanifest").status_code == 200
    assert client.get("/sw.js").status_code == 200