from fastapi.testclient import TestClient

from app.main import app
from app.db import Base, engine


client = TestClient(app)


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module() -> None:
    Base.metadata.drop_all(bind=engine)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_and_due() -> None:
    resp = client.post("/upload", json={"topic": "Alpha", "content": "Beta"})
    assert resp.status_code == 200
    assert resp.json()["topic"] == "Alpha"
    resp = client.get("/due")
    assert resp.status_code == 200
    assert resp.json() == []
