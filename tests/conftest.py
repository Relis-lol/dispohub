import os
import tempfile

import pytest

# Test-DB und Secret vor App-Import setzen.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SEED_ON_STARTUP"] = "false"
# Tests senden Formulare direkt per POST, ohne vorher die Seite zu laden (und
# damit ein CSRF-Token zu bekommen) — für die Testsuite deaktiviert, im echten
# Betrieb bleibt der Schutz an (siehe tests/test_csrf.py für den echten Test).
os.environ["CSRF_PROTECTION_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed import (  # noqa: E402
    seed, seed_invoices, seed_chat, seed_fuelcards, seed_tasks, seed_safety_items,
    seed_parking, seed_personnel, seed_permissions,
)


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
        seed_invoices(db)
        seed_chat(db)
        seed_fuelcards(db)
        seed_tasks(db)
        seed_safety_items(db)
        seed_parking(db)
        seed_personnel(db)
        seed_permissions(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
