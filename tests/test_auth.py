from tests.conftest import login


def test_login_required_redirects(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_login_wrong_password(client):
    r = login(client, "gf@dispohub.example", "falsch")
    assert r.status_code == 401


def test_gf_can_open_dashboard(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.get("/")
    assert r.status_code == 200
    assert "Dashboard" in r.text


def test_fahrer_redirected_to_chat_and_blocked_from_office(client):
    r = login(client, "fahrer1@dispohub.example", "fahrer123")
    assert r.headers["location"] == "/chat"
    # Fahrer darf die Büro-Bereiche nicht sehen
    assert client.get("/kosten").status_code == 403
    assert client.get("/schaeden").status_code == 403
    # aber Chat und Meldeansicht
    assert client.get("/chat").status_code == 200
    assert client.get("/melden").status_code == 200
