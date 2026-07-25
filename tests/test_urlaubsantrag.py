"""Urlaubsanträge: Fahrer beantragt, Büro/GF genehmigt oder lehnt ab."""
from datetime import date, timedelta

from tests.conftest import login


def _antrag_stellen(client, von_offset=30, tage=4, notiz="Testantrag"):
    von = date.today() + timedelta(days=von_offset)
    bis = von + timedelta(days=tage - 1)
    return client.post("/urlaub", data={
        "von": von.isoformat(), "bis": bis.isoformat(), "notiz": notiz,
    }, follow_redirects=False)


def test_fahrer_beantragt_urlaub(client):
    login(client, "fahrer2@dispohub.example", "fahrer123")
    r = _antrag_stellen(client, notiz="Familienfeier")
    assert r.status_code == 303
    assert "urlaub=1" in r.headers["location"]

    # Antrag erscheint auf der Melden-Seite mit Status Offen
    r = client.get("/melden")
    assert "Familienfeier" in r.text and "Offen" in r.text


def test_rueckwirkend_und_verdreht_abgelehnt(client):
    login(client, "fahrer2@dispohub.example", "fahrer123")
    gestern = (date.today() - timedelta(days=1)).isoformat()
    heute = date.today().isoformat()
    assert client.post("/urlaub", data={"von": gestern, "bis": heute}).status_code == 400
    morgen = (date.today() + timedelta(days=1)).isoformat()
    assert client.post("/urlaub", data={"von": morgen, "bis": heute}).status_code == 400


def test_genehmigen_erzeugt_personalakten_eintrag(client):
    login(client, "fahrer3@dispohub.example", "fahrer123")
    _antrag_stellen(client, von_offset=45, tage=3, notiz="Kurztrip")

    from app.db import SessionLocal
    from app.models import LeaveRequest, LeaveStatus, PersonnelEntry, EntryArt, User
    db = SessionLocal()
    f3 = db.query(User).filter(User.email == "fahrer3@dispohub.example").first()
    antrag = (db.query(LeaveRequest)
              .filter(LeaveRequest.user_id == f3.id, LeaveRequest.notiz == "Kurztrip").first())
    aid, uid = antrag.id, f3.id
    db.close()

    # Büro sieht den Antrag und genehmigt
    login(client, "buero@dispohub.example", "buero123")
    r = client.get("/mitarbeiter")
    assert "Kurztrip" in r.text and "Resturlaub" in r.text
    r = client.post(f"/urlaub/{aid}/genehmigen", follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    antrag = db.get(LeaveRequest, aid)
    assert antrag.status == LeaveStatus.genehmigt
    assert antrag.entschieden_von is not None
    eintrag = (db.query(PersonnelEntry)
               .filter(PersonnelEntry.user_id == uid, PersonnelEntry.art == EntryArt.urlaub,
                       PersonnelEntry.notiz == "Kurztrip").first())
    assert eintrag is not None and eintrag.tage == 3
    # Doppelt entscheiden geht nicht
    assert client.post(f"/urlaub/{aid}/genehmigen").status_code == 400
    # aufräumen
    db.delete(eintrag)
    db.commit()
    db.close()


def test_ablehnen_ohne_personalakten_eintrag(client):
    login(client, "fahrer2@dispohub.example", "fahrer123")
    _antrag_stellen(client, von_offset=60, tage=2, notiz="Abzulehnen")

    from app.db import SessionLocal
    from app.models import LeaveRequest, LeaveStatus, PersonnelEntry, User
    db = SessionLocal()
    f2 = db.query(User).filter(User.email == "fahrer2@dispohub.example").first()
    antrag = (db.query(LeaveRequest)
              .filter(LeaveRequest.user_id == f2.id, LeaveRequest.notiz == "Abzulehnen").first())
    aid, uid = antrag.id, f2.id
    vorher = db.query(PersonnelEntry).filter(PersonnelEntry.user_id == uid).count()
    db.close()

    login(client, "gf@dispohub.example", "gf123")
    r = client.post(f"/urlaub/{aid}/ablehnen", follow_redirects=False)
    assert r.status_code == 303

    db = SessionLocal()
    assert db.get(LeaveRequest, aid).status == LeaveStatus.abgelehnt
    assert db.query(PersonnelEntry).filter(PersonnelEntry.user_id == uid).count() == vorher
    db.close()


def test_fahrer_darf_nicht_entscheiden(client):
    login(client, "fahrer2@dispohub.example", "fahrer123")
    _antrag_stellen(client, von_offset=90, tage=1)
    from app.db import SessionLocal
    from app.models import LeaveRequest, User
    db = SessionLocal()
    f2 = db.query(User).filter(User.email == "fahrer2@dispohub.example").first()
    antrag = (db.query(LeaveRequest).filter(LeaveRequest.user_id == f2.id)
              .order_by(LeaveRequest.id.desc()).first())
    aid = antrag.id
    db.close()
    assert client.post(f"/urlaub/{aid}/genehmigen").status_code == 403
