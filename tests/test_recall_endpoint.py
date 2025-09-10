from fastapi.testclient import TestClient

from app.main import app
from app.db import Base, engine, SessionLocal
from app import models
from app.llm import MockLLM


client = TestClient(app)


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module() -> None:
    Base.metadata.drop_all(bind=engine)


def test_recall_missing_topic() -> None:
    resp = client.post("/recall", json={"topic": "unknown", "recall_text": "test"})
    assert resp.status_code == 404


def test_recall_flow() -> None:
    # Upload initial study material
    up = client.post("/upload", json={"topic": "Alpha", "content": "content"})
    assert up.status_code == 200

    class CustomLLM(MockLLM):
        def score(self, prompt: str) -> dict:  # type: ignore[override]
            return {
                "score": 80,
                "feedback": "Nice",
                "flashcards": [
                    {"front": "Q1", "back": "A1"},
                ],
            }

    # Swap in our deterministic LLM
    import app.main as main

    main.llm = CustomLLM()

    resp = client.post(
        "/recall", json={"topic": "Alpha", "recall_text": "some recall"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 80
    assert data["feedback"] == "Nice"
    assert data["cards_added"] == 1
    assert "next_review" in data

    db = SessionLocal()
    try:
        # A history entry was added
        hist = db.query(models.RecallHistory).filter_by(topic="Alpha").all()
        assert len(hist) == 1

        # Schedule updated based on score
        sched = db.query(models.TopicSchedule).filter_by(topic="Alpha").first()
        assert sched is not None and sched.interval_days == 2

        # Flashcard persisted
        cards = db.query(models.Flashcard).filter_by(topic="Alpha").all()
        assert len(cards) == 1
    finally:
        db.close()

