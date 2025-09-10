from __future__ import annotations

from datetime import datetime, timedelta
import json

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from collections.abc import Iterator
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from . import models, scheduler, utils
from .llm import build_llm
from .config import settings

init_db()

app = FastAPI(title="Free Recall Study App")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UploadRequest(BaseModel):
    topic: str
    content: str


class RecallRequest(BaseModel):
    topic: str
    recall_text: str


class FlashcardItem(BaseModel):
    front: str
    back: str


class LLMResponse(BaseModel):
    score: int
    feedback: str
    flashcards: list[FlashcardItem]


llm = build_llm(settings)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload(req: UploadRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    now = datetime.utcnow().isoformat()
    material = models.StudyMaterial(
        topic=req.topic,
        content=req.content,
        created_at=now,
        updated_at=now,
    )
    db.add(material)
    schedule = models.TopicSchedule(
        topic=req.topic,
        interval_days=1,
        next_review=(datetime.utcnow() + timedelta(days=1)).isoformat(),
    )
    db.merge(schedule)
    db.commit()
    return {"topic": req.topic}


@app.get("/due")
async def due_topics(db: Session = Depends(get_db)) -> list[str]:
    now = datetime.utcnow().isoformat()
    rows = db.query(models.TopicSchedule).filter(models.TopicSchedule.next_review <= now).all()
    return [r.topic for r in rows]


@app.post("/recall")
async def recall(req: RecallRequest, db: Session = Depends(get_db)) -> dict[str, str | int]:
    material = db.query(models.StudyMaterial).filter_by(topic=req.topic).first()
    if material is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    prompt = f"{material.content}\n---\n{req.recall_text}"
    raw_resp = llm.score(prompt)
    try:
        parsed = LLMResponse(**raw_resp)
    except ValidationError as e:  # pragma: no cover - schema errors are unlikely
        raise HTTPException(status_code=500, detail="Invalid LLM response") from e

    now = datetime.utcnow()
    now_iso = now.isoformat()
    history = models.RecallHistory(
        topic=req.topic,
        recall_text=req.recall_text,
        feedback_json=json.dumps(raw_resp),
        score=parsed.score,
        created_at=now_iso,
    )
    db.add(history)

    schedule = db.query(models.TopicSchedule).filter_by(topic=req.topic).first()
    if schedule is None:
        schedule = models.TopicSchedule(
            topic=req.topic,
            interval_days=1,
            next_review=now_iso,
        )
        db.add(schedule)
    next_int = scheduler.next_interval(schedule.interval_days, parsed.score)
    schedule.interval_days = next_int
    schedule.last_review = now_iso
    schedule.next_review = (now + timedelta(days=next_int)).isoformat()

    cards_added = 0
    for card in parsed.flashcards:
        h = utils.card_hash(card.front, card.back)
        exists = db.query(models.Flashcard).filter_by(front_back_sha256=h).first()
        if exists:
            continue
        db.add(
            models.Flashcard(
                topic=req.topic,
                front=card.front,
                back=card.back,
                front_back_sha256=h,
                created_at=now_iso,
            )
        )
        cards_added += 1

    db.commit()
    return {
        "feedback": parsed.feedback,
        "score": parsed.score,
        "cards_added": cards_added,
        "next_review": schedule.next_review,
    }
