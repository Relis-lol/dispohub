"""Kulli-Modus (Draufsicht), Fahrzeugakte-Schnellübersicht, Druckbarkeit."""
from tests.conftest import login


def test_draufsicht_kulli_mode_present(client):
    login(client, "gf@dispohub.example", "gf123")
    page = client.get("/fahrzeuge/1/draufsicht").text
    assert 'id="beschreibung"' in page
    assert "kulli-details" in page  # weitere Felder eingeklappt
    assert "Weitere Details" in page


def test_draufsicht_submit_still_works_with_new_form(client):
    """Backend-Vertrag unverändert: schadensdatum wird weiter per Hidden-Feld gesendet."""
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/fahrzeuge/1/schaden-pin", data={
        "beschreibung": "Kulli-Test Delle", "position_x": "0.3", "position_y": "0.4",
        "schadensdatum": "2026-07-15",
    }, follow_redirects=False)
    assert r.status_code == 303


def test_vehicle_quickview_shows_tuev_km_maengel(client):
    login(client, "gf@dispohub.example", "gf123")
    page = client.get("/fahrzeuge/1").text
    assert "TÜV/AU" in page
    assert "Kilometerstand" in page
    assert "Offene Mängel" in page


def test_print_buttons_present_on_key_pages(client):
    login(client, "gf@dispohub.example", "gf123")
    pages = ["/fahrzeuge/1", "/schaeden", "/mitarbeiter", "/kosten", "/aufgaben", "/kalender"]
    for url in pages:
        page = client.get(url).text
        assert "window.print()" in page, url


def test_print_css_defines_a4_and_no_print_rules(client):
    css = client.get("/static/css/app.css").text
    assert "@page" in css
    assert "size: A4" in css
    assert ".no-print" in css
    assert "@media print" in css
