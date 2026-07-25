"""Unauthenticated health endpoint for container orchestration."""


def test_health_ok_without_login(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
