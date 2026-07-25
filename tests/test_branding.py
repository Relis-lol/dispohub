"""Firmenlogo & Website: Upload in der Verwaltung, Anzeige in der Seitenleiste."""
import io

from tests.conftest import login

# 1x1 rotes PNG
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
       b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03"
       b"\x00\x01\x9f\xa9\xc8\xc5\x00\x00\x00\x00IEND\xaeB`\x82")


def test_logo_hochladen_und_entfernen(client):
    login(client, "gf@dispohub.example", "gf123")

    r = client.post("/verwaltung/branding",
                    data={"firmen_website": "www.meinefirma.de"},
                    files={"logo": ("logo.png", io.BytesIO(PNG), "image/png")},
                    follow_redirects=False)
    assert r.status_code == 303

    from app.db import SessionLocal
    from app.services.app_settings import get_setting, LOGO_PFAD, FIRMEN_WEBSITE
    db = SessionLocal()
    logo = get_setting(db, LOGO_PFAD)
    assert logo and logo.startswith("/static/uploads/")
    assert get_setting(db, FIRMEN_WEBSITE) == "https://www.meinefirma.de"
    db.close()

    # Logo erscheint in der Seitenleiste (jede eingeloggte Seite)
    r = client.get("/mitarbeiter")
    assert logo in r.text

    # Entfernen -> wieder DispoHub-Schriftzug
    r = client.post("/verwaltung/branding", data={"logo_entfernen": "1", "firmen_website": ""},
                    follow_redirects=False)
    assert r.status_code == 303
    db = SessionLocal()
    assert get_setting(db, LOGO_PFAD) is None
    db.close()


def test_branding_nur_gf_admin(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.post("/verwaltung/branding", data={"firmen_website": "x.de"})
    assert r.status_code == 403
