"""GF-konfigurierbare Büro-Rechte + IT-Rolle."""
from tests.conftest import login


def test_default_permissions_preserve_existing_behavior(client):
    """Ohne Änderung durch die GF darf Büro weiterhin alles sehen (Standard: erlaubt)."""
    login(client, "buero@dispohub.example", "buero123")
    for url in ["/fahrzeuge", "/mitarbeiter", "/kalender", "/schaeden", "/kosten",
                "/rechnungen", "/export", "/tankkarten"]:
        assert client.get(url).status_code == 200, url


def test_gf_can_toggle_off_area_for_buero(client):
    login(client, "gf@dispohub.example", "gf123")
    # GF kann selbst weiterhin alles, auch nach dem Deaktivieren für Büro
    r = client.get("/kosten")
    assert r.status_code == 200

    # Kosten für Büro sperren: nur "kosten" ankreuzen fehlt -> aus
    from app.services.permissions import BEREICHE
    form = {f"bereich_{b}": "on" for b in BEREICHE if b != "kosten"}
    r = client.post("/einstellungen/rechte", data=form, follow_redirects=False)
    assert r.status_code == 303

    login(client, "buero@dispohub.example", "buero123")
    assert client.get("/kosten").status_code == 403
    # andere Bereiche bleiben erlaubt
    assert client.get("/fahrzeuge").status_code == 200

    # GF ist von der Einschränkung nicht betroffen
    login(client, "gf@dispohub.example", "gf123")
    assert client.get("/kosten").status_code == 200

    # zurücksetzen für andere Tests
    from app.services.permissions import BEREICHE as B2
    form_reset = {f"bereich_{b}": "on" for b in B2}
    client.post("/einstellungen/rechte", data=form_reset)


def test_only_gf_admin_can_change_rights(client):
    login(client, "buero@dispohub.example", "buero123")
    assert client.get("/einstellungen/rechte").status_code == 403

    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get("/einstellungen/rechte").status_code == 403

    login(client, "it@dispohub.example", "it123")
    assert client.get("/einstellungen/rechte").status_code == 403

    login(client, "gf@dispohub.example", "gf123")
    assert client.get("/einstellungen/rechte").status_code == 200


def test_it_role_minimal_access(client):
    r = login(client, "it@dispohub.example", "it123")
    assert r.headers["location"] == "/it"

    login_ok = login(client, "it@dispohub.example", "it123")
    assert client.get("/it").status_code == 200

    # IT sieht keine Büro-/Finanzbereiche
    for url in ["/", "/kosten", "/rechnungen", "/export", "/tankkarten",
                "/fahrzeuge", "/mitarbeiter", "/kalender", "/schaeden"]:
        assert client.get(url).status_code == 403, url


def test_it_page_shows_only_names_no_financials(client):
    login(client, "it@dispohub.example", "it123")
    page = client.get("/it").text
    # Keine Kosten-/Vertragsdaten auf der IT-Seite
    assert "Leasing" not in page
    assert "monatliche_fixkosten" not in page
