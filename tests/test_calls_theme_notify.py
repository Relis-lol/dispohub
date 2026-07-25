"""Ansprechpartner-Ampel, Theme/Notification-Assets, Fahrzeug-SVG ohne CSS-var()-Bug."""
from tests.conftest import login


def test_gf_can_toggle_erreichbarkeit(client):
    login(client, "gf@dispohub.example", "gf123")
    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    gf_id = db.query(User).filter(User.email == "gf@dispohub.example").first().id
    db.close()

    r = client.post("/einstellungen/erreichbarkeit",
                    data={"kontakt_id": gf_id, "status": "rot"}, follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    gf = db.get(User, gf_id)
    assert gf.erreichbarkeit.value == "rot"
    db.close()

    page = client.get("/einstellungen/rechte").text
    assert "Anrufbereitschaft" in page

    # zurücksetzen für andere Tests
    client.post("/einstellungen/erreichbarkeit", data={"kontakt_id": gf_id, "status": "gruen"})
    db = SessionLocal()
    assert db.get(User, gf_id).erreichbarkeit.value == "gruen"
    db.close()


def test_driver_mobile_pages_show_contacts_link(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    for url in ["/chat", "/melden", "/aufgaben"]:
        page = client.get(url).text
        assert "/kontakte" in page, url


def test_static_theme_and_notification_scripts_exist(client):
    for path in ["/static/js/theme.js", "/static/js/notifications.js", "/static/js/chat.js"]:
        r = client.get(path)
        assert r.status_code == 200, path


def test_vehicle_svg_has_no_css_var_bug(client):
    """Regression: SVG-Füllfarben dürfen keine var()-Presentation-Attribute mehr nutzen."""
    login(client, "gf@dispohub.example", "gf123")
    page = client.get("/fahrzeuge/1/draufsicht").text
    assert "var(--" not in page


def test_chat_photo_placeholder_is_not_app_logo(client):
    """Regression: Demo-Chatfoto darf nicht das DispoHub-Logo sein."""
    from app.db import SessionLocal
    from app.models import Document
    db = SessionLocal()
    docs = db.query(Document).filter(Document.pfad.like("%icon.svg")).count()
    assert docs == 0
    db.close()
