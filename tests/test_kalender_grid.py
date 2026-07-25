"""Kalender-Grid: Monat x Fahrzeug/Fahrer mit Terminen und Urlaub/Krank."""
from datetime import date

from tests.conftest import login


def test_grid_zeigt_fahrzeuge_und_fahrer(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.get("/kalender")
    assert r.status_code == 200
    assert "calgrid" in r.text
    assert "B-TR 1201" in r.text          # Fahrzeug-Zeile
    assert "Kemal Yıldız" in r.text        # Fahrer-Zeile
    assert "Alle offenen Termine" in r.text


def test_monatsblaettern(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.get("/kalender?monat=2026-01")
    assert r.status_code == 200
    assert "Januar 2026" in r.text
    # Ungültiger Parameter fällt auf den aktuellen Monat zurück
    r = client.get("/kalender?monat=quatsch")
    assert r.status_code == 200


def test_urlaub_erscheint_im_grid(client):
    """Seed: fahrer2 hat Urlaub in ~20 Tagen -> im passenden Monat steht ein U."""
    from datetime import timedelta
    login(client, "buero@dispohub.example", "buero123")
    urlaubstag = date.today() + timedelta(days=20)
    r = client.get(f"/kalender?monat={urlaubstag.strftime('%Y-%m')}")
    assert r.status_code == 200
    assert "cal-urlaub" in r.text
