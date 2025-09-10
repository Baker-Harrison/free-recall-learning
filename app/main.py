from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from collections.abc import Iterator
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from . import models

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
