"""Sprachumschaltung: Cookie-basiert, betrifft Login + Fahrer-Ansichten."""
from tests.conftest import login


def test_standardsprache_ist_deutsch(client):
    r = client.get("/login")
    assert "Anmelden" in r.text
    assert 'lang="de"' in r.text


def test_login_seite_auf_englisch(client):
    client.cookies.set("fh_lang", "en")
    r = client.get("/login")
    assert "Sign in" in r.text
    assert 'lang="en"' in r.text
    assert "Anmelden" not in r.text


def test_alle_sechs_sprachen_liefern_valide_seite(client):
    for code, erwartet in [
        ("de", "Anmelden"), ("cs", "Přihlášení"), ("en", "Sign in"),
        ("ru", "Вход"), ("pl", "Logowanie"), ("tr", "Giriş yap"),
    ]:
        client.cookies.set("fh_lang", code)
        r = client.get("/login")
        assert r.status_code == 200
        assert erwartet in r.text, f"Sprache {code}: '{erwartet}' fehlt"


def test_unbekannte_sprache_faellt_auf_deutsch_zurueck(client):
    client.cookies.set("fh_lang", "xx")
    r = client.get("/login")
    assert "Anmelden" in r.text


def test_sprachumschalter_vorhanden_auf_login(client):
    r = client.get("/login")
    assert "lang-switch" in r.text
    assert "🇩🇪" in r.text and "🇨🇿" in r.text and "🇬🇧" in r.text
    assert "🇷🇺" in r.text and "🇵🇱" in r.text and "🇹🇷" in r.text


def test_fahrer_ansicht_uebersetzt_und_nicht_kaputt(client):
    login(client, "fahrer1@dispohub.example", "fahrer123")
    for pfad in ["/chat", "/melden", "/aufgaben", "/kontakte", "/passwort"]:
        r = client.cookies.set("fh_lang", "ru") or client.get(pfad)
        assert r.status_code == 200
    # stichprobenartig: /melden zeigt russischen Text
    r = client.get("/melden")
    assert "Сообщить" in r.text or "повреждении" in r.text


def test_office_seiten_bleiben_deutsch(client):
    """Büro/GF-Seiten sind (noch) nicht übersetzt — Standardverhalten bleibt Deutsch."""
    login(client, "buero@dispohub.example", "buero123")
    client.cookies.set("fh_lang", "en")
    r = client.get("/mitarbeiter")
    assert "Mitarbeiter" in r.text
