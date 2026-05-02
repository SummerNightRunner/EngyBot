from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    source_language: Mapped[str] = mapped_column(String(16), default="ru")
    target_language: Mapped[str] = mapped_column(String(16), default="en")
    level: Mapped[str] = mapped_column(String(32), default="A1")
    bilingual_ui: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    training_attempts: Mapped[list["TrainingAttempt"]] = relationship(back_populates="user")
    word_progress: Mapped[list["UserWordProgress"]] = relationship(back_populates="user")


class WordSet(Base):
    __tablename__ = "word_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[str] = mapped_column(String(32), default="A1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    words: Mapped[list["Word"]] = relationship(back_populates="word_set", cascade="all, delete-orphan")
    training_attempts: Mapped[list["TrainingAttempt"]] = relationship(back_populates="word_set")


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_set_id: Mapped[int] = mapped_column(ForeignKey("word_sets.id"))
    source_text: Mapped[str] = mapped_column(String(255))
    target_text: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(32), default="A1")
    example: Mapped[str | None] = mapped_column(Text, nullable=True)

    word_set: Mapped["WordSet"] = relationship(back_populates="words")
    progress_entries: Mapped[list["UserWordProgress"]] = relationship(back_populates="word")


class TrainingAttempt(Base):
    __tablename__ = "training_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    word_set_id: Mapped[int] = mapped_column(ForeignKey("word_sets.id"))
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="training_attempts")
    word_set: Mapped["WordSet"] = relationship(back_populates="training_attempts")


class UserWordProgress(Base):
    __tablename__ = "user_word_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"))
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    last_result: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="word_progress")
    word: Mapped["Word"] = relationship(back_populates="progress_entries")


class DailyPractice(Base):
    __tablename__ = "daily_practices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    practice_date: Mapped[date] = mapped_column(Date, index=True)
    word_ids_json: Mapped[str] = mapped_column(Text)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
