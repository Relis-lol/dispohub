"""CSRF-Schutz: eigener Test mit AKTIVEM Schutz (Testsuite läuft sonst mit
CSRF_PROTECTION_ENABLED=false, siehe conftest.py, damit die ~120 anderen
Tests nicht jedes Formular erst per GET laden müssen)."""
import re

import pytest

from app.config import settings


@pytest.fixture
def csrf_client(client):
    """Selber TestClient, aber mit eingeschaltetem CSRF-Schutz."""
    settings.csrf_protection_enabled = True
    yield client
    settings.csrf_protection_enabled = False


def test_formular_ohne_token_wird_abgelehnt(csrf_client):
    r = csrf_client.post("/login", data={"email": "gf@dispohub.example", "password": "gf123"})
    assert r.status_code == 403


def test_login_seite_enthaelt_token_und_funktioniert_damit(csrf_client):
    seite = csrf_client.get("/login").text
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', seite)
    assert m, "kein csrf_token im Login-Formular gefunden"
    token = m.group(1)

    r = csrf_client.post("/login", data={
        "email": "gf@dispohub.example", "password": "gf123", "csrf_token": token,
    }, follow_redirects=False)
    assert r.status_code == 303


def test_falsches_token_wird_abgelehnt(csrf_client):
    csrf_client.get("/login")  # Session/Token anlegen
    r = csrf_client.post("/login", data={
        "email": "gf@dispohub.example", "password": "gf123", "csrf_token": "falsches-token",
    })
    assert r.status_code == 403


def test_eingeloggte_formulare_bekommen_ebenfalls_ein_token(csrf_client):
    seite = csrf_client.get("/login").text
    m = re.search(r'name="csrf_token" value="([a-f0-9]+)"', seite)
    token = m.group(1)
    csrf_client.post("/login", data={
        "email": "gf@dispohub.example", "password": "gf123", "csrf_token": token,
    })

    notizen_seite = csrf_client.get("/notizen").text
    assert 'name="csrf_token"' in notizen_seite


def test_token_aus_anderer_session_wird_abgelehnt(csrf_client):
    """Ein gültiges Token aus Session A darf in Session B nicht funktionieren."""
    from starlette.testclient import TestClient
    from app.main import app

    seite_a = csrf_client.get("/login").text
    token_a = re.search(r'name="csrf_token" value="([a-f0-9]+)"', seite_a).group(1)

    # Eigener Client = eigene Session/Cookies = eigenes (anderes) Token
    client_b = TestClient(app)
    r = client_b.post("/login", data={
        "email": "gf@dispohub.example", "password": "gf123", "csrf_token": token_a,
    })
    assert r.status_code == 403


def test_logout_post_mit_formulardaten_braucht_token(csrf_client):
    """/logout wird in der App nur als GET-Link ausgelöst (siehe Kommentar in
    app/routers/auth.py: same_site=lax macht ein CSRF-Token dafür unnötig -
    ein fremder Request kommt ohne Session-Cookie an). Enthält ein POST an
    /logout aber tatsächlich Formulardaten, greift die CSRFMiddleware genauso
    wie bei jedem anderen Formular."""
    seite = csrf_client.get("/login").text
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', seite).group(1)
    csrf_client.post("/login", data={"email": "gf@dispohub.example", "password": "gf123", "csrf_token": token})

    r = csrf_client.post("/logout", data={"irgendein_feld": "x"}, follow_redirects=False)
    assert r.status_code == 403  # Formulardaten vorhanden, aber kein Token


def test_datei_upload_multipart_ohne_token_abgelehnt(csrf_client):
    """Datei-Uploads laufen als multipart/form-data - müssen genauso geprüft werden."""
    import io

    seite = csrf_client.get("/login").text
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', seite).group(1)
    csrf_client.post("/login", data={"email": "gf@dispohub.example", "password": "gf123", "csrf_token": token})

    pdf = io.BytesIO(b"%PDF-1.4 test")
    r = csrf_client.post("/export/beleg", data={"notiz": "x"},
                         files={"datei": ("beleg.pdf", pdf, "application/pdf")})
    assert r.status_code == 403


def test_datei_upload_multipart_mit_token_funktioniert(csrf_client):
    import io

    seite = csrf_client.get("/login").text
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', seite).group(1)
    csrf_client.post("/login", data={"email": "gf@dispohub.example", "password": "gf123", "csrf_token": token})

    export_seite = csrf_client.get("/export").text
    upload_token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', export_seite).group(1)

    pdf = io.BytesIO(b"%PDF-1.4 test")
    r = csrf_client.post("/export/beleg", data={"notiz": "x", "csrf_token": upload_token},
                         files={"datei": ("beleg.pdf", pdf, "application/pdf")},
                         follow_redirects=False)
    assert r.status_code == 303


def test_javascript_fetch_stil_request_ohne_token_abgelehnt(csrf_client):
    """Simuliert einen fetch()-Request wie chat.js ihn schickt (FormData,
    Header X-WS statt normaler Formular-Navigation) - muss trotzdem geprüft werden."""
    seite = csrf_client.get("/login").text
    token = re.search(r'name="csrf_token" value="([a-f0-9]+)"', seite).group(1)
    csrf_client.post("/login", data={"email": "gf@dispohub.example", "password": "gf123", "csrf_token": token})

    from app.db import SessionLocal
    from app.models import ChatMembership, ThreadArt, User
    db = SessionLocal()
    gf = db.query(User).filter(User.email == "gf@dispohub.example").first()
    m = next((m for m in db.query(ChatMembership).filter(ChatMembership.user_id == gf.id).all()
              if m.thread.art == ThreadArt.direkt), None)
    db.close()
    if not m:
        pytest.skip("kein Einzelchat für GF im Seed vorhanden")

    r = csrf_client.post(f"/chat/{m.thread_id}/senden", data={"text": "Hallo"},
                         headers={"X-WS": "1"})
    assert r.status_code == 403


def test_fehlerseite_ist_lesbar_und_kein_rohes_json(csrf_client):
    r = csrf_client.post("/login", data={"email": "gf@dispohub.example", "password": "gf123"})
    assert r.status_code == 403
    assert "text/html" in r.headers["content-type"]
    assert "Sicherheitsprüfung" in r.text
    assert '{"detail"' not in r.text
