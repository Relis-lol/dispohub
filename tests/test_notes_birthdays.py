"""Notizen zwischen GF/Büro; Geburtstags-Erinnerung im Dashboard und in der Mitarbeiterliste."""
from tests.conftest import login


def test_create_and_list_note(client):
    login(client, "gf@dispohub.example", "gf123")
    r = client.post("/notizen", data={"text": "Bitte Werkstatttermine für KW30 abstimmen"},
                    follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/notizen").text
    assert "Bitte Werkstatttermine für KW30 abstimmen" in page
    assert "Sabine Groß" in page


def test_notes_blocked_for_driver_and_it(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    assert client.get("/notizen").status_code == 403

    login(client, "it@dispohub.example", "it123")
    assert client.get("/notizen").status_code == 403


def test_dashboard_shows_upcoming_birthday(client):
    login(client, "gf@dispohub.example", "gf123")
    # Marek Nowak (fahrer2) hat im Seed einen Geburtstag in 7 Tagen
    page = client.get("/").text
    assert "Geburtstage" in page
    assert "Marek Nowak" in page


def test_employee_list_shows_birthday(client):
    login(client, "gf@dispohub.example", "gf123")
    page = client.get("/mitarbeiter").text
    assert "Geburtstag" in page
