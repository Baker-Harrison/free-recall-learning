from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class StudyMaterial(Base):
    __tablename__ = "study_material"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class RecallHistory(Base):
    __tablename__ = "recall_history"
    __table_args__ = (
        Index("idx_history_topic_created", "topic", "created_at"),
        CheckConstraint("score BETWEEN 0 AND 100"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String, ForeignKey("study_material.topic"), nullable=False)
    recall_text: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_json: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Flashcard(Base):
    __tablename__ = "flashcard"
    __table_args__ = (
        Index("idx_flash_topic", "topic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    front_back_sha256: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    added_to_anki: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anki_note_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class TopicSchedule(Base):
    __tablename__ = "topic_schedule"

    topic: Mapped[str] = mapped_column(String, primary_key=True)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    next_review: Mapped[str] = mapped_column(String, nullable=False)
    last_review: Mapped[str | None] = mapped_column(String)
    easiness: Mapped[float] = mapped_column(default=2.3)
