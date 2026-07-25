"""Vordrucke: druckfertige Formulare für Arbeitszeit, Tankliste, Urlaub."""
from tests.conftest import login


def test_uebersicht_und_formulare_laden(client):
    login(client, "buero@dispohub.example", "buero123")
    r = client.get("/vordrucke")
    assert r.status_code == 200
    assert "Arbeitszeitnachweis" in r.text and "Tankliste" in r.text

    r = client.get("/vordrucke/arbeitszeit?monat=2026-03")
    assert r.status_code == 200
    assert "März 2026" in r.text and "Unterschrift" in r.text

    r = client.get("/vordrucke/tankliste?monat=2026-03")
    assert r.status_code == 200
    assert "Diesel" in r.text and "AdBlue" in r.text

    r = client.get("/vordrucke/urlaubsantrag")
    assert r.status_code == 200
    assert "Erholungsurlaub" in r.text


def test_arbeitszeit_mit_mitarbeiter_zeigt_namen(client):
    login(client, "buero@dispohub.example", "buero123")
    from app.db import SessionLocal
    from app.models import User
    db = SessionLocal()
    mid = db.query(User).filter(User.email == "fahrer1@dispohub.example").first().id
    db.close()
    r = client.get(f"/vordrucke/arbeitszeit?mitarbeiter_id={mid}&monat=2026-07")
    assert "Kemal Yıldız" in r.text


def test_urlaubsbestaetigung_nur_fuer_genehmigte_antraege(client):
    from datetime import date, timedelta
    login(client, "fahrer2@dispohub.example", "fahrer123")
    von = date.today() + timedelta(days=15)
    bis = von + timedelta(days=1)
    client.post("/urlaub", data={"von": von.isoformat(), "bis": bis.isoformat(), "notiz": "Formulartest"})

    from app.db import SessionLocal
    from app.models import LeaveRequest
    db = SessionLocal()
    antrag = (db.query(LeaveRequest).filter(LeaveRequest.notiz == "Formulartest")
              .order_by(LeaveRequest.id.desc()).first())
    aid = antrag.id
    db.close()

    # Noch offen -> 404
    login(client, "buero@dispohub.example", "buero123")
    assert client.get(f"/vordrucke/urlaubsbestaetigung/{aid}").status_code == 404

    client.post(f"/urlaub/{aid}/genehmigen")
    r = client.get(f"/vordrucke/urlaubsbestaetigung/{aid}")
    assert r.status_code == 200
    assert "nicht im" in r.text and "Betrieb tätig" in r.text


def test_fahrer_hat_keinen_zugriff(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get("/vordrucke").status_code == 403
